"""Deterministic structural checks for plan.md (no LLM).

Runs after agentic plan.md generation (before step 8 telemetry) in /opsx-continue.
Checks for §1.4 pattern alignment, §1.5 startup resolution, and per-phase
discovery tasks / watcher mechanism fields added by plan-template.md.

Unlike validation/specs/tasks validators, plan remains agentic — on failure the
agent re-runs plan refinement with tool reads freely (not single-shot).

Usage:
    python -m openspec.validators.plan_structural --change "<name>"

Returns JSON to stdout:
    {"ok": true}
    {"ok": false, "failures": ["...", "..."]}

Exit code 0 on ok, 1 on failure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CHANGES_DIR = Path("openspec/changes")

# §1.4 — Pattern alignment section detection
PATTERN_ALIGNMENT = re.compile(
    r"(§\s*1\.4|Pattern alignment)", re.IGNORECASE
)

# §1.5 — Startup-time section detection
STARTUP_SECTION = re.compile(
    r"(§\s*1\.5|Startup.time|Startup-time|Startup vs)", re.IGNORECASE
)

# Phase block header
PHASE_HEADER = re.compile(r"^#{1,3}\s+Phase\s+\d+", re.MULTILINE)

# Discovery tasks field present in a phase block
DISCOVERY_FIELD = re.compile(
    r"\*\*Discovery tasks[:\*]|\bDiscovery tasks\b", re.IGNORECASE
)

# Watcher / update mechanism field
WATCHER_FIELD = re.compile(
    r"\*\*Watcher\b|\bWatcher\s*/\s*update mechanism\b|\bupdate mechanism\b",
    re.IGNORECASE,
)

# repo-assessment §13 sentinel — if present, §1.4 is required
ASSESSMENT_S13 = re.compile(r"§\s*13|Similar\s+PR\s*&\s*Pattern", re.IGNORECASE)


def _split_phases(text: str) -> list[str]:
    """Split plan text into per-phase blocks (returns text between phase headers)."""
    positions = [m.start() for m in PHASE_HEADER.finditer(text)]
    if not positions:
        return []
    blocks = []
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        blocks.append(text[start:end])
    return blocks


def check(change: str) -> dict:
    cdir = CHANGES_DIR / change
    plan_path = cdir / "plan.md"
    failures: list[str] = []

    if not plan_path.exists():
        return {"ok": False, "failures": [f"plan.md not found at {plan_path}"]}

    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "failures": [f"Cannot read plan.md: {exc}"]}

    if not text.strip():
        return {"ok": False, "failures": ["plan.md is empty."]}

    # Check whether repo-assessment for this change has §13 (signals §1.4 is required)
    assessment_path = cdir / "repo-assessment.md"
    assessment_has_s13 = False
    if assessment_path.exists():
        try:
            assessment_text = assessment_path.read_text(encoding="utf-8")
            assessment_has_s13 = bool(ASSESSMENT_S13.search(assessment_text))
        except OSError:
            pass

    # §1.4 Pattern alignment — required when repo-assessment §13 present
    if assessment_has_s13:
        if not PATTERN_ALIGNMENT.search(text):
            failures.append(
                "plan.md is missing §1.4 Pattern alignment section. "
                "repo-assessment.md contains §13 Similar-PR data — "
                "the plan must include a Pattern alignment subsection in §1 "
                "documenting the dominant pattern chosen, deprecated patterns avoided, "
                "and config delivery method."
            )

    # §1.5 Startup-time vs runtime resolution — always required
    if not STARTUP_SECTION.search(text):
        failures.append(
            "plan.md is missing §1.5 Startup-time vs. runtime resolution section. "
            "Every plan must state whether startup-time config is required, "
            "which hook resolves it, and whether a runtime watcher is needed."
        )

    # Per-phase checks
    phase_blocks = _split_phases(text)
    if not phase_blocks:
        failures.append(
            "plan.md contains no Phase sections (expected '## Phase N' or '### Phase N' headers)."
        )
    else:
        for i, block in enumerate(phase_blocks, start=1):
            phase_label = f"Phase {i}"
            # Extract the actual phase number from the header if possible
            header_match = PHASE_HEADER.match(block)
            if header_match:
                num_match = re.search(r"\d+", header_match.group(0))
                if num_match:
                    phase_label = f"Phase {num_match.group(0)}"

            if not DISCOVERY_FIELD.search(block):
                failures.append(
                    f"{phase_label}: missing 'Discovery tasks:' field. "
                    "Every phase must include this field (value can be 'None' if no prereqs)."
                )

            if not WATCHER_FIELD.search(block):
                failures.append(
                    f"{phase_label}: missing 'Watcher / update mechanism:' field. "
                    "Every phase must include this field (value can be 'N/A' if stateless)."
                )

    if failures:
        return {"ok": False, "failures": failures}
    return {"ok": True}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Structural validator for plan.md output."
    )
    parser.add_argument("--change", required=True,
                        help="Change name (directory under openspec/changes/).")
    args = parser.parse_args(argv)

    result = check(args.change)
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
