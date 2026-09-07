"""Deterministic structural checks for plan.md (no LLM).

Encodes the "Quality self-check" list embedded in
schemas/openspec-agile-workflow/templates/plan-template.md as hard gates. Run
immediately after plan.md generation (agentic or script).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CHANGES_DIR = Path("openspec/changes")

REQUIRED_SECTIONS = [
    r"^##\s+0\.\s+Inputs acknowledged",
    r"^##\s+1\.\s+Architectural strategy",
    r"^##\s+2\.\s+Persistence & state",
    r"^##\s+3\.\s+Interfaces & contracts",
    r"^##\s+4\.\s+Dependencies & sequencing graph",
    r"^##\s+5\.\s+Implementation phases",
    r"^##\s+6\.\s+Verification matrix",
    r"^##\s+7\.\s+Risks, migrations",
    r"^##\s+8\.\s+Open questions",
]
PHASE_BLOCK_FIELDS = [
    "User Story:",
    "Goal:",
    "Dependencies:",
    "Target files:",
    "Required capabilities:",
    "Verification hooks:",
]
US_ID_RE = re.compile(r"\bUS-\d{3}\b", re.I)
AGENT_ROUTING_RE = re.compile(r"AgentRoutingMode.{0,20}?(PROVIDED|PROVISIONAL)", re.I | re.S)
E2E_PHASE_RE = re.compile(r"^###\s+Phase\s+\d+:.*\b(e2e|end-to-end)\b", re.I | re.M)


def validate_plan_structural(change_dir: Path) -> dict[str, Any]:
    failures: list[str] = []
    checks = 0

    path = change_dir / "plan.md"
    if not path.exists():
        return {"ok": False, "failures": [f"{path} not found"], "checks_total": 1}

    text = path.read_text(encoding="utf-8", errors="replace")
    specs_path = change_dir / "specs.md"
    specs_text = specs_path.read_text(encoding="utf-8", errors="replace") if specs_path.exists() else ""

    checks += 1
    for pattern in REQUIRED_SECTIONS:
        if not re.search(pattern, text, re.M):
            failures.append(f"Missing required section matching: {pattern}")

    checks += 1
    if not AGENT_ROUTING_RE.search(text):
        failures.append("§0 must state AgentRoutingMode: PROVIDED or PROVISIONAL")

    section_5_m = re.search(r"^##\s+5\.\s+Implementation phases.*?(?=^##\s+6\.|\Z)", text, re.M | re.S)
    section_5 = section_5_m.group(0) if section_5_m else ""

    phase_blocks = list(re.finditer(r"^###\s+Phase\s+(\d+):.*?(?=^###\s+Phase\s+\d+:|\Z)", section_5, re.M | re.S))

    checks += 1
    if not phase_blocks:
        failures.append("§5 has no '### Phase N:' headings")

    checks += 1
    for m in phase_blocks:
        block = m.group(0)
        phase_num = m.group(1)
        for field_name in PHASE_BLOCK_FIELDS:
            if field_name not in block:
                failures.append(f"Phase {phase_num}: missing required field '{field_name}'")

    checks += 1
    if E2E_PHASE_RE.search(section_5):
        failures.append("§5 contains a standalone e2e-only phase heading — e2e belongs in §6 only")

    checks += 1
    if specs_text:
        spec_us_ids = {u.upper() for u in US_ID_RE.findall(specs_text)}
        plan_phase_us_ids = {u.upper() for u in US_ID_RE.findall(section_5)}
        missing_us = sorted(spec_us_ids - plan_phase_us_ids)
        if missing_us:
            failures.append(f"§5 phases do not reference these specs.md user stories: {missing_us}")

    return {
        "ok": len(failures) == 0,
        "failures": failures,
        "checks_total": checks,
        "phase_count": len(phase_blocks),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Structural validation for plan.md")
    parser.add_argument("--change", required=True, help="Change name under openspec/changes/")
    args = parser.parse_args()

    result = validate_plan_structural(CHANGES_DIR / args.change)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
