"""Deterministic structural checks for tasks.md (no LLM).

Encodes the quality self-check list from tasks-template.md as hard gates.
Used after single-shot tasks.md generation in /opsx-continue.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

CHANGES_DIR = Path("openspec/changes")

PROVISIONAL_AGENTS = frozenset({
    "API_Agent",
    "OperatorController_Agent",
    "ManifestsBindata_Agent",
    "WebhookTLS_Agent",
    "RBACSecurity_Agent",
    "OLMRelease_Agent",
    "Testing_Agent",
    "Docs_Agent",
})

FIBONACCI_COMPLEXITY = frozenset({1, 2, 3, 5, 8})

FORBIDDEN_AGENTS = frozenset({"Testing_Agent"})

SECTION_0_RE = re.compile(r"^##\s+0\.\s+Input Coverage Checklist", re.I | re.M)
SECTION_1_RE = re.compile(r"^##\s+1\.\s+Task Dependency Graph", re.I | re.M)
SECTION_2_RE = re.compile(r"^##\s+2\.\s+Linear Execution Order", re.I | re.M)
SECTION_3_RE = re.compile(r"^##\s+3\.\s+Task Execution Manifest", re.I | re.M)
SECTION_4_RE = re.compile(r"^##\s+4\.\s+Task Specifications", re.I | re.M)
SECTION_5_RE = re.compile(r"^##\s+5\.\s+Orchestration", re.I | re.M)

TASK_ID_RE = re.compile(r"\bT\d+_\d+\b")
US_ID_RE = re.compile(r"\bUS-\d{3}\b", re.I)
FR_ID_RE = re.compile(r"\bFR-\d+\b", re.I)
AGENT_ROUTING_RE = re.compile(
    r"\*\*AgentRoutingMode:\*\*\s*(PROVIDED|PROVISIONAL)",
    re.I,
)
PAYLOAD_HEADER_RE = re.compile(r"^###\s+Task\s+(T\d+_\d+)\s*:", re.I | re.M)
MERMAID_EDGE_RE = re.compile(r"\b(T\d+_\d+)\s*-->\s*(T\d+_\d+)\b")
LINEAR_ORDER_RE = re.compile(r"^\s*\d+\.\s+(T\d+_\d+)\b", re.I | re.M)
AGENT_ID_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*_Agent\b")


def _section_slice(text: str, start_re: re.Pattern[str], end_res: list[re.Pattern[str]]) -> str:
    m = start_re.search(text)
    if not m:
        return ""
    start = m.start()
    end = len(text)
    for end_re in end_res:
        em = end_re.search(text, m.end())
        if em:
            end = min(end, em.start())
    return text[start:end]


def _parse_manifest_rows(section_3: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    in_table = False
    for line in section_3.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table and rows:
                break
            continue
        if re.match(r"^\|\s*Task ID\s*\|", stripped, re.I):
            in_table = True
            continue
        if in_table and re.match(r"^\|[-:\s|]+\|$", stripped):
            continue
        if not in_table:
            continue
        cols = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cols) < 8:
            continue
        task_id = cols[0]
        if not TASK_ID_RE.fullmatch(task_id):
            continue
        rows.append({
            "task_id": task_id,
            "title": cols[1],
            "agent": cols[2],
            "phase": cols[3],
            "depends_on": cols[4],
            "parallel_ok": cols[5],
            "complexity": cols[6],
            "risk": cols[7],
            "user_story": cols[8] if len(cols) > 8 else "",
        })
    return rows


def _parse_agents_from_agents_md(agents_md: str) -> set[str]:
    found = set(AGENT_ID_RE.findall(agents_md))
    return {a for a in found if a not in FORBIDDEN_AGENTS}


def _extract_dag_edges(section_1: str) -> list[tuple[str, str]]:
    return list(MERMAID_EDGE_RE.findall(section_1))


def _extract_linear_order(section_2: str) -> list[str]:
    return LINEAR_ORDER_RE.findall(section_2)


def _is_valid_topological_order(
    task_ids: set[str],
    edges: list[tuple[str, str]],
    linear_order: list[str],
) -> tuple[bool, str]:
    if not linear_order:
        return False, "§2 linear order is empty"

    linear_set = set(linear_order)
    if linear_set != task_ids:
        missing = task_ids - linear_set
        extra = linear_set - task_ids
        parts = []
        if missing:
            parts.append(f"missing in §2: {sorted(missing)}")
        if extra:
            parts.append(f"extra in §2: {sorted(extra)}")
        return False, "§2 task IDs do not match §3 manifest (" + "; ".join(parts) + ")"

    indegree: dict[str, int] = {tid: 0 for tid in task_ids}
    adj: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        if src not in task_ids or dst not in task_ids:
            continue
        adj[src].append(dst)
        indegree[dst] += 1

    position = {tid: i for i, tid in enumerate(linear_order)}
    for src, dst in edges:
        if src in position and dst in position and position[src] >= position[dst]:
            return False, f"§2 violates DAG edge {src} --> {dst} (dependency must appear earlier)"

    # Kahn's algorithm — also verify DAG has no cycles among known nodes
    q = deque([n for n, d in indegree.items() if d == 0])
    visited = 0
    while q:
        n = q.popleft()
        visited += 1
        for nb in adj[n]:
            indegree[nb] -= 1
            if indegree[nb] == 0:
                q.append(nb)
    if visited != len(task_ids) and edges:
        return False, "§1 DAG contains a cycle or unresolved dependencies among §3 task IDs"

    return True, ""


def validate_tasks_structural(
    change_dir: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Run all structural checks on tasks.md for a change."""
    repo_root = repo_root or Path(".")
    failures: list[str] = []
    checks_run = 0

    tasks_path = change_dir / "tasks.md"
    specs_path = change_dir / "specs.md"
    plan_path = change_dir / "plan.md"
    agents_path = repo_root / "agents.md"
    constitution_path = repo_root / "harness-evals" / "constitution.md"

    if not tasks_path.exists():
        return {"ok": False, "failures": [f"tasks.md not found at {tasks_path}"], "checks_passed": 0, "checks_total": 1}

    tasks_text = tasks_path.read_text(encoding="utf-8", errors="replace")
    specs_text = specs_path.read_text(encoding="utf-8", errors="replace") if specs_path.exists() else ""
    agents_text = agents_path.read_text(encoding="utf-8", errors="replace") if agents_path.exists() else ""
    constitution_text = (
        constitution_path.read_text(encoding="utf-8", errors="replace")
        if constitution_path.exists()
        else ""
    )

    section_0 = _section_slice(tasks_text, SECTION_0_RE, [SECTION_1_RE])
    section_1 = _section_slice(tasks_text, SECTION_1_RE, [SECTION_2_RE])
    section_2 = _section_slice(tasks_text, SECTION_2_RE, [SECTION_3_RE])
    section_3 = _section_slice(tasks_text, SECTION_3_RE, [SECTION_4_RE])
    section_4 = _section_slice(tasks_text, SECTION_4_RE, [SECTION_5_RE])
    section_5 = _section_slice(tasks_text, SECTION_5_RE, [])

    # --- section presence ---
    checks_run += 1
    for label, content in [
        ("§0 Input Coverage Checklist", section_0),
        ("§1 Task Dependency Graph", section_1),
        ("§2 Linear Execution Order", section_2),
        ("§3 Task Execution Manifest", section_3),
        ("§4 Task Specifications", section_4),
        ("§5 Orchestration notes", section_5),
    ]:
        if not content.strip():
            failures.append(f"Missing required section: {label}")

    manifest_rows = _parse_manifest_rows(section_3)
    task_ids = {r["task_id"] for r in manifest_rows}
    payload_ids = set(PAYLOAD_HEADER_RE.findall(section_4))

    # --- §3 / §4 parity ---
    checks_run += 1
    if manifest_rows and task_ids != payload_ids:
        only_manifest = sorted(task_ids - payload_ids)
        only_payload = sorted(payload_ids - task_ids)
        if only_manifest:
            failures.append(f"§3 tasks missing §4 payloads: {only_manifest}")
        if only_payload:
            failures.append(f"§4 payloads without §3 manifest rows: {only_payload}")

    # --- complexity Fibonacci ---
    checks_run += 1
    for row in manifest_rows:
        try:
            complexity = int(row["complexity"])
        except ValueError:
            failures.append(f"{row['task_id']}: invalid complexity '{row['complexity']}' (expected 1|2|3|5|8)")
            continue
        if complexity not in FIBONACCI_COMPLEXITY:
            failures.append(
                f"{row['task_id']}: complexity {complexity} not in Fibonacci set {{1,2,3,5,8}}"
            )

    # --- forbidden agents / e2e tasks ---
    checks_run += 1
    for row in manifest_rows:
        agent = row["agent"]
        title = row["title"].lower()
        if agent in FORBIDDEN_AGENTS:
            failures.append(f"{row['task_id']}: Assigned Agent must not be Testing_Agent (e2e out of OAPE scope)")
        if "e2e" in title and "out of oape" not in title:
            failures.append(f"{row['task_id']}: task title suggests e2e work — e2e tasks are forbidden")

    # --- user story column ---
    checks_run += 1
    for row in manifest_rows:
        if not row["user_story"].strip():
            failures.append(f"{row['task_id']}: User Story column is empty in §3 manifest")
        elif not US_ID_RE.search(row["user_story"]):
            failures.append(f"{row['task_id']}: User Story '{row['user_story']}' is not a valid US-xxx ID")

    # --- agent routing ---
    checks_run += 1
    routing_match = AGENT_ROUTING_RE.search(tasks_text)
    routing_mode = routing_match.group(1).upper() if routing_match else ""
    if not routing_mode:
        failures.append("Missing **AgentRoutingMode:** PROVIDED|PROVISIONAL in tasks.md header")
    else:
        allowed_agents = (
            _parse_agents_from_agents_md(agents_text)
            if routing_mode == "PROVIDED" and agents_text.strip()
            else set(PROVISIONAL_AGENTS)
        )
        if routing_mode == "PROVIDED" and not agents_text.strip():
            failures.append("AgentRoutingMode is PROVIDED but agents.md is missing or empty at repo root")
        for row in manifest_rows:
            if row["agent"] not in allowed_agents:
                failures.append(
                    f"{row['task_id']}: agent '{row['agent']}' not in allowed roster "
                    f"({routing_mode})"
                )

    # --- §0 US coverage ---
    checks_run += 1
    if specs_text:
        spec_us_ids = {u.upper() for u in US_ID_RE.findall(specs_text)}
        section_0_us = {u.upper() for u in US_ID_RE.findall(section_0)}
        missing_us = sorted(spec_us_ids - section_0_us)
        if missing_us:
            failures.append(f"§0 missing user story coverage for: {missing_us}")

    # --- §0 FR coverage (best-effort) ---
    checks_run += 1
    if specs_text:
        spec_fr_ids = {f.upper() for f in FR_ID_RE.findall(specs_text)}
        section_0_fr = {f.upper() for f in FR_ID_RE.findall(section_0)}
        missing_fr = sorted(spec_fr_ids - section_0_fr)
        if missing_fr:
            failures.append(f"§0 missing functional requirement coverage for: {missing_fr}")

    # --- §0 e2e note when plan mentions e2e ---
    checks_run += 1
    if plan_path.exists():
        plan_text = plan_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\be2e\b", plan_text, re.I):
            if not re.search(r"out of oape scope", section_0, re.I):
                failures.append(
                    "§0 must note discarded e2e coverage as 'e2e — out of OAPE scope' when plan mentions e2e"
                )

    # --- §4 Covers US-xxx ---
    checks_run += 1
    for tid in sorted(payload_ids):
        block_m = re.search(
            rf"^###\s+Task\s+{re.escape(tid)}\s*:.*?(?=^###\s+Task\s+|\Z)",
            section_4,
            re.I | re.M | re.S,
        )
        if not block_m:
            continue
        block = block_m.group(0)
        if not US_ID_RE.search(block):
            failures.append(f"{tid}: §4 payload missing **Covers:** or User Story US-xxx reference")

    # --- DAG / linear order ---
    checks_run += 1
    if manifest_rows:
        edges = _extract_dag_edges(section_1)
        linear = _extract_linear_order(section_2)
        ok_topo, topo_msg = _is_valid_topological_order(task_ids, edges, linear)
        if not ok_topo:
            failures.append(topo_msg)

    # --- §5 subsections ---
    checks_run += 1
    if section_5.strip():
        s5_lower = section_5.lower()
        for required in ("retry", "merge conflict", "open question"):
            if required not in s5_lower:
                failures.append(f"§5 missing required subsection theme: '{required}'")

    # --- document ends cleanly ---
    checks_run += 1
    if section_4.strip():
        for tid in sorted(payload_ids):
            block_m = re.search(
                rf"^###\s+Task\s+{re.escape(tid)}\s*:.*?(?=^###\s+Task\s+|\Z)",
                section_4,
                re.I | re.M | re.S,
            )
            if block_m and "**Objective:**" not in block_m.group(0):
                failures.append(f"{tid}: §4 payload appears truncated (missing **Objective:**)")

    return {
        "ok": len(failures) == 0,
        "failures": failures,
        "checks_total": checks_run,
        "task_count": len(manifest_rows),
        "agent_routing_mode": routing_mode or None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Structural validation for tasks.md")
    parser.add_argument("--change", required=True, help="Change name under openspec/changes/")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Operator repo root (for agents.md, harness-evals/constitution.md)",
    )
    args = parser.parse_args()

    change_dir = CHANGES_DIR / args.change
    result = validate_tasks_structural(change_dir, repo_root=Path(args.repo_root))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
