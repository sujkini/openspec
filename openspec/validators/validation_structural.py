"""Deterministic structural checks for validation.json (no LLM).

Runs after single-shot validation.json generation (step 7a) in /opsx-continue.
Mirrors the same pattern as tasks_structural.py.

Usage:
    python -m openspec.validators.validation_structural --change "<name>"

Returns JSON to stdout:
    {"ok": true}
    {"ok": false, "failures": ["...", "..."]}

Exit code 0 on ok, 1 on failure.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CHANGES_DIR = Path("openspec/changes")

REQUIRED_KEYS = frozenset({"rubric", "sections", "status"})
VALID_STATUSES = frozenset({"pass", "fail", "needs_review"})


def check(change: str) -> dict:
    cdir = CHANGES_DIR / change
    path = cdir / "validation.json"

    failures: list[str] = []

    if not path.exists():
        return {"ok": False, "failures": [f"validation.json not found at {path}"]}

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "failures": [f"Cannot read validation.json: {exc}"]}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"ok": False, "failures": [f"validation.json is not valid JSON: {exc}"]}

    if not isinstance(data, dict):
        return {"ok": False, "failures": ["validation.json must be a JSON object at the top level."]}

    # Required top-level keys
    missing_keys = REQUIRED_KEYS - set(data.keys())
    if missing_keys:
        failures.append(
            f"validation.json is missing required top-level key(s): {sorted(missing_keys)}"
        )

    # Status field validity
    status = data.get("status")
    if status is None:
        failures.append("validation.json 'status' field is null or missing.")
    elif not isinstance(status, str) or status.lower() not in VALID_STATUSES:
        failures.append(
            f"validation.json 'status' must be one of {sorted(VALID_STATUSES)}, got: {status!r}"
        )

    # Sections: no empty criteria lists
    sections = data.get("sections")
    if sections is not None:
        if not isinstance(sections, list):
            failures.append("validation.json 'sections' must be a list.")
        else:
            for i, section in enumerate(sections):
                if not isinstance(section, dict):
                    continue
                criteria = section.get("criteria")
                name = section.get("name", f"section[{i}]")
                if criteria is None:
                    failures.append(
                        f"Section '{name}' is missing a 'criteria' field."
                    )
                elif isinstance(criteria, list) and len(criteria) == 0:
                    failures.append(
                        f"Section '{name}' has an empty 'criteria' list — "
                        "every section must have at least one criterion."
                    )

    if failures:
        return {"ok": False, "failures": failures}
    return {"ok": True}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Structural validator for validation.json output."
    )
    parser.add_argument("--change", required=True,
                        help="Change name (directory under openspec/changes/).")
    args = parser.parse_args(argv)

    result = check(args.change)
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
