"""Deterministic schema gate for validation.json (no LLM).

Encodes the required JSON schema documented in
schemas/openspec-agile-workflow/templates/validation-template.md as a hard
gate, run immediately after validation.json generation (agentic or script).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CHANGES_DIR = Path("openspec/changes")

VALID_DOC_TYPES = {"jira", "prd", "enhancement"}
VALID_STATUSES = {"PASS", "NEEDS_REVISION", "BLOCKED"}
VALID_ISSUE_TYPES = {"Ambiguity", "Testability", "Sizing", "Consistency"}


def validate_validation_schema(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    checks = 0

    if not path.exists():
        return {"ok": False, "failures": [f"{path} not found"], "checks_total": 1}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "failures": [f"invalid JSON: {exc}"], "checks_total": 1}

    checks += 1
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        failures.append("metadata object missing")
    else:
        if metadata.get("doc_type") not in VALID_DOC_TYPES:
            failures.append(f"metadata.doc_type must be one of {sorted(VALID_DOC_TYPES)} (got {metadata.get('doc_type')!r})")
        if not isinstance(metadata.get("pass_threshold"), (int, float)):
            failures.append("metadata.pass_threshold must be numeric")

    checks += 1
    results = payload.get("validation_results")
    if not isinstance(results, dict):
        return {"ok": False, "failures": failures + ["validation_results object missing"], "checks_total": checks}

    for key in ("completeness_score", "quality_score", "overall_score"):
        checks += 1
        val = results.get(key)
        if not isinstance(val, (int, float)) or not (0 <= val <= 100):
            failures.append(f"validation_results.{key} must be a number 0-100 (got {val!r})")

    checks += 1
    status = results.get("overall_status")
    if status not in VALID_STATUSES:
        failures.append(f"validation_results.overall_status must be one of {sorted(VALID_STATUSES)} (got {status!r})")

    checks += 1
    completeness = results.get("completeness_score")
    quality = results.get("quality_score")
    overall = results.get("overall_score")
    if isinstance(completeness, (int, float)) and isinstance(quality, (int, float)) and isinstance(overall, (int, float)):
        expected = round(0.6 * completeness + 0.4 * quality)
        if abs(expected - overall) > 2:
            failures.append(
                f"overall_score {overall} does not match the required weighting "
                f"round(0.6*completeness + 0.4*quality) = {expected}"
            )

    checks += 1
    if not isinstance(results.get("missing_elements"), list):
        failures.append("validation_results.missing_elements must be a list (use [] when none)")

    checks += 1
    issues = results.get("quality_issues")
    if not isinstance(issues, list):
        failures.append("validation_results.quality_issues must be a list (use [] when none)")
    else:
        for i, issue in enumerate(issues):
            if not isinstance(issue, dict) or issue.get("type") not in VALID_ISSUE_TYPES:
                failures.append(f"quality_issues[{i}].type must be one of {sorted(VALID_ISSUE_TYPES)}")
            elif not issue.get("quote") or not issue.get("suggestion"):
                failures.append(f"quality_issues[{i}] missing 'quote' or 'suggestion'")

    checks += 1
    for key in ("blockers", "non_blockers"):
        if not isinstance(results.get(key), list):
            failures.append(f"validation_results.{key} must be a list (use [] when none)")

    checks += 1
    if status == "BLOCKED" and not results.get("blockers"):
        failures.append("overall_status is BLOCKED but blockers[] is empty")

    return {"ok": len(failures) == 0, "failures": failures, "checks_total": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description="Schema validation for validation.json")
    parser.add_argument("--change", required=True, help="Change name under openspec/changes/")
    args = parser.parse_args()

    path = CHANGES_DIR / args.change / "validation.json"
    result = validate_validation_schema(path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
