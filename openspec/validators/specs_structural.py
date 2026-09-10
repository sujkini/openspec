"""Deterministic structural checks for specs.md (no LLM).

Runs after single-shot specs.md generation (step 7b) in /opsx-continue.
Encodes the gating-condition and completeness rules from spec-template.md.

Usage:
    python -m openspec.validators.specs_structural --change "<name>"

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

# Regex patterns
FR_PATTERN = re.compile(r"\bFR-\d{3}\b")
US_PATTERN = re.compile(r"\bUS-\d{3}\b")

# Words that signal a conditional FR
CONDITIONAL_WORDS = re.compile(
    r"\b(when|if|only if|unless|provided that)\b", re.IGNORECASE
)

# A backtick-enclosed field name (proxy for gating condition stated)
BACKTICK_FIELD = re.compile(r"`[^`]+`")

# Placeholder / TBD acceptance criteria patterns
EMPTY_AC_PATTERN = re.compile(
    r"(?m)AC:\s*(TBD|\[expected outcome\]|\[.*?\]|)\s*$"
)


def _lines_matching(text: str, pattern: re.Pattern) -> list[str]:
    return [line for line in text.splitlines() if pattern.search(line)]


def check(change: str) -> dict:
    cdir = CHANGES_DIR / change
    path = cdir / "specs.md"
    failures: list[str] = []

    if not path.exists():
        return {"ok": False, "failures": [f"specs.md not found at {path}"]}

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "failures": [f"Cannot read specs.md: {exc}"]}

    if not text.strip():
        return {"ok": False, "failures": ["specs.md is empty."]}

    # Must have at least one FR-xxx
    if not FR_PATTERN.search(text):
        failures.append(
            "specs.md contains no FR-xxx functional requirements "
            "(expected at least one line matching FR-\\d{3})."
        )

    # Must have at least one US-xxx
    if not US_PATTERN.search(text):
        failures.append(
            "specs.md contains no US-xxx user stories "
            "(expected at least one line matching US-\\d{3})."
        )

    # Conditional FRs must have a backtick field reference
    for line in text.splitlines():
        if not FR_PATTERN.search(line):
            continue
        if CONDITIONAL_WORDS.search(line):
            if not BACKTICK_FIELD.search(line):
                fr_match = FR_PATTERN.search(line)
                fr_id = fr_match.group(0) if fr_match else "unknown FR"
                failures.append(
                    f"{fr_id}: conditional requirement (contains 'when/if/unless/...') "
                    "but no backtick-enclosed field name found. "
                    "State the gating field name in backticks within the FR text "
                    "(e.g., 'when `tlsAdherence` is set to Strict')."
                )

    # No empty Acceptance Criteria blocks
    empty_ac_matches = EMPTY_AC_PATTERN.findall(text)
    if empty_ac_matches:
        failures.append(
            f"Found {len(empty_ac_matches)} empty or placeholder Acceptance Criteria section(s) "
            "(matched 'AC: TBD', 'AC: [expected outcome]', or blank after 'AC:'). "
            "Each acceptance criterion must have a concrete outcome."
        )

    if failures:
        return {"ok": False, "failures": failures}
    return {"ok": True}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Structural validator for specs.md output."
    )
    parser.add_argument("--change", required=True,
                        help="Change name (directory under openspec/changes/).")
    args = parser.parse_args(argv)

    result = check(args.change)
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
