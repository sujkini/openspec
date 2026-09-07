"""Deterministic structural checks for specs.md (no LLM).

Encodes the self-check list embedded in
schemas/openspec-agile-workflow/templates/spec-template.md as hard gates. Run
immediately after specs.md generation (agentic or script).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CHANGES_DIR = Path("openspec/changes")

US_HEADING_RE = re.compile(r"^###\s+(US-\d{3}):.*\(Priority:\s*(P[123])\)", re.M)
FR_RE = re.compile(r"^\-\s+\*\*(FR-\d+)\*\*:", re.M)
SC_RE = re.compile(r"^\-\s+\*\*(SC-\d+)\*\*:", re.M)
ASSUMPTION_RE = re.compile(r"^\-\s+\*\*(A-\d+)\*\*:", re.M)
NEEDS_CLARIFICATION_RE = re.compile(r"\[NEEDS CLARIFICATION\b", re.I)
GWT_RE = re.compile(r"\*\*Given\*\*.+?\*\*When\*\*.+?\*\*Then\*\*", re.I | re.S)
TRACEABILITY_ROW_RE = re.compile(r"^\-\s+\*\*(US-\d{3})\*\*:\s*(.+)$", re.M)
IMPL_LEAK_RE = re.compile(
    r"\b(golang|python3?|typescript|javascript|CustomResourceDefinition|"
    r"\S+\.go\b|\S+\.ts\b|\S+\.py\b|/pkg/|/api/v\d+\b)",
    re.I,
)
REQUIRED_HEADINGS = [
    "## User Scenarios & Testing",
    "### Edge Cases",
    "## Requirements",
    "### Functional Requirements",
    "### Story → FR Traceability",
    "## Success Criteria",
    "## Assumptions",
]


def validate_specs_structural(change_dir: Path) -> dict[str, Any]:
    failures: list[str] = []
    checks = 0

    path = change_dir / "specs.md"
    if not path.exists():
        return {"ok": False, "failures": [f"{path} not found"], "checks_total": 1}

    text = path.read_text(encoding="utf-8", errors="replace")

    checks += 1
    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            failures.append(f"Missing required section: {heading}")

    stories = US_HEADING_RE.findall(text)
    ids = [s[0] for s in stories]

    checks += 1
    if not ids:
        failures.append("No user stories found (expected '### US-001: <title> (Priority: P1)' headings)")

    checks += 1
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    if dup_ids:
        failures.append(f"Duplicate user story IDs: {dup_ids}")

    checks += 1
    for story_id in ids:
        block_m = re.search(rf"^###\s+{re.escape(story_id)}:.*?(?=^###\s+US-|\Z)", text, re.M | re.S)
        block = block_m.group(0) if block_m else ""
        if not GWT_RE.search(block):
            failures.append(f"{story_id}: no Given/When/Then acceptance scenario found")

    frs = FR_RE.findall(text)
    checks += 1
    if not frs:
        failures.append("No functional requirements found (expected '- **FR-001**: ...' bullets)")

    checks += 1
    dup_frs = sorted({f for f in frs if frs.count(f) > 1})
    if dup_frs:
        failures.append(f"Duplicate FR IDs: {dup_frs}")

    checks += 1
    traceability_m = re.search(r"### Story → FR Traceability.*?(?=^##\s|\Z)", text, re.M | re.S)
    traceability_text = traceability_m.group(0) if traceability_m else ""
    traced_frs: set[str] = set()
    for _, fr_list in TRACEABILITY_ROW_RE.findall(traceability_text):
        traced_frs.update(re.findall(r"FR-\d+", fr_list))
    missing_traced = sorted(set(frs) - traced_frs)
    if missing_traced:
        failures.append(f"FRs missing from Story → FR Traceability table: {missing_traced}")

    checks += 1
    if not SC_RE.findall(text):
        failures.append("No success criteria found (expected '- **SC-001**: ...' bullets)")

    checks += 1
    clarification_count = len(NEEDS_CLARIFICATION_RE.findall(text))
    if clarification_count > 3:
        failures.append(f"{clarification_count} [NEEDS CLARIFICATION] markers found — maximum allowed is 3")

    checks += 1
    if not ASSUMPTION_RE.findall(text):
        failures.append("No numbered assumptions found (expected '- **A-001**: ...' bullets)")

    checks += 1
    impl_leaks = sorted({m.group(0) for m in IMPL_LEAK_RE.finditer(text)})
    if impl_leaks:
        failures.append(f"Possible implementation-detail leakage (no languages/frameworks/paths allowed): {impl_leaks[:5]}")

    return {
        "ok": len(failures) == 0,
        "failures": failures,
        "checks_total": checks,
        "story_count": len(ids),
        "fr_count": len(set(frs)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Structural validation for specs.md")
    parser.add_argument("--change", required=True, help="Change name under openspec/changes/")
    args = parser.parse_args()

    result = validate_specs_structural(CHANGES_DIR / args.change)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
