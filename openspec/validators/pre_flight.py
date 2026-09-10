"""Pre-flight input validators for /opsx-continue (no LLM).

Checks that each artifact's required INPUT files exist and are well-formed
before any LLM call is made.  Prevents expensive retries caused by missing
or corrupt inputs.

Usage (from repo root):
    python -m openspec.validators.pre_flight \
        --artifact <specs|plan|tasks|validation> \
        --change "<name>" \
        [--phase N]

Returns JSON to stdout:
    {"ok": true}
    {"ok": false, "reason": "...", "failures": ["...", "..."]}

Exit code 0 on ok, 1 on failure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CHANGES_DIR = Path("openspec/changes")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fail(reason: str, failures: list[str]) -> dict:
    return {"ok": False, "reason": reason, "failures": failures}


def _ok() -> dict:
    return {"ok": True}


def _read(path: Path) -> str | None:
    """Return file text or None if missing/unreadable."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _has_pattern(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, re.MULTILINE))


# ---------------------------------------------------------------------------
# Per-artifact input validators
# ---------------------------------------------------------------------------

def validate_validation_inputs(cdir: Path) -> dict:
    """Check inputs required before validation.json generation (step 7a).

    Required:
    - inputs/jira-spec.md  exists and is non-empty (or inputs/jira.yaml)
    """
    failures: list[str] = []

    jira_spec = cdir / "inputs" / "jira-spec.md"
    jira_yaml = cdir / "inputs" / "jira.yaml"

    if not jira_spec.exists() and not jira_yaml.exists():
        failures.append(
            "Neither inputs/jira-spec.md nor inputs/jira.yaml found. "
            "Provide at least one Jira input before generating validation.json."
        )
    else:
        for p in (jira_spec, jira_yaml):
            if p.exists():
                text = _read(p)
                if not text or not text.strip():
                    failures.append(f"{p.relative_to(cdir)} is empty — populate it before proceeding.")

    if failures:
        return _fail("Missing or empty Jira inputs for validation stage.", failures)
    return _ok()


def validate_specs_inputs(cdir: Path) -> dict:
    """Check inputs required before specs.md generation (step 7b).

    Required:
    - inputs/jira-spec.md  non-empty
    - validation.json  exists and status != "failed"
    """
    failures: list[str] = []

    jira_spec = cdir / "inputs" / "jira-spec.md"
    if not jira_spec.exists():
        failures.append(
            "inputs/jira-spec.md not found. "
            "Run the Jira fetch step or provide jira-spec.md before generating specs."
        )
    else:
        text = _read(jira_spec)
        if not text or not text.strip():
            failures.append("inputs/jira-spec.md is empty.")

    validation_json = cdir / "validation.json"
    if not validation_json.exists():
        failures.append(
            "validation.json not found. "
            "Complete the validation stage before generating specs.md."
        )
    else:
        raw = _read(validation_json)
        if raw is None:
            failures.append("validation.json cannot be read.")
        else:
            try:
                data = json.loads(raw)
                status = data.get("status", "")
                if isinstance(status, str) and status.lower() == "failed":
                    failures.append(
                        f"validation.json has status='failed'. "
                        "Fix validation issues before proceeding to specs generation."
                    )
            except json.JSONDecodeError as exc:
                failures.append(f"validation.json is not valid JSON: {exc}")

    if failures:
        return _fail("Input pre-flight failed for specs generation.", failures)
    return _ok()


def validate_plan_inputs(cdir: Path) -> dict:
    """Check inputs required before plan.md generation.

    Required:
    - specs.md  contains at least one FR-xxx and one US-xxx pattern
    - repo-assessment.md  exists
    """
    failures: list[str] = []

    specs = cdir / "specs.md"
    if not specs.exists():
        failures.append(
            "specs.md not found. "
            "Complete the specs stage before generating plan.md."
        )
    else:
        text = _read(specs)
        if not text or not text.strip():
            failures.append("specs.md is empty.")
        else:
            if not _has_pattern(text, r"FR-\d{3}"):
                failures.append(
                    "specs.md contains no FR-xxx functional requirements. "
                    "The spec must define at least one FR before planning can proceed."
                )
            if not _has_pattern(text, r"US-\d{3}"):
                failures.append(
                    "specs.md contains no US-xxx user stories. "
                    "The spec must define at least one user story before planning can proceed."
                )

    assessment = cdir / "repo-assessment.md"
    if not assessment.exists():
        failures.append(
            "repo-assessment.md not found. "
            "Complete the repo-assessment stage before generating plan.md."
        )

    if failures:
        return _fail("Input pre-flight failed for plan generation.", failures)
    return _ok()


def validate_tasks_inputs(cdir: Path, phase: int | None) -> dict:
    """Check inputs required before tasks.md generation (step 7c).

    Required:
    - plan.md  exists and contains §5 Implementation phases section
    - If phase is given: plan phase count matches, and tasks.md headers exist for prior phases
    """
    failures: list[str] = []

    plan = cdir / "plan.md"
    if not plan.exists():
        failures.append(
            "plan.md not found. "
            "Complete the plan stage before generating tasks.md."
        )
        return _fail("Input pre-flight failed for tasks generation.", failures)

    plan_text = _read(plan)
    if not plan_text or not plan_text.strip():
        failures.append("plan.md is empty.")
        return _fail("Input pre-flight failed for tasks generation.", failures)

    # Check for implementation phases section
    if not _has_pattern(plan_text, r"##\s+(5\.|Implementation phases)"):
        failures.append(
            "plan.md is missing §5 Implementation phases section. "
            "The plan must define implementation phases before tasks can be generated."
        )

    if phase is not None and phase > 1:
        tasks_path = cdir / "tasks.md"
        if not tasks_path.exists():
            failures.append(
                f"phase={phase} requested but tasks.md does not exist. "
                "Prior phase tasks must be written before appending phase N."
            )
        else:
            tasks_text = _read(tasks_path) or ""
            # Look for prior phase headers: "## Phase <N-1>" or "# Phase <N-1>"
            prior = phase - 1
            prior_header_pat = rf"#{1,3}\s+Phase\s+{prior}\b"
            if not _has_pattern(tasks_text, prior_header_pat):
                failures.append(
                    f"tasks.md does not contain a Phase {prior} header. "
                    f"Expected prior phases to be completed before appending Phase {phase}."
                )

        # Count phases in plan and compare
        plan_phase_matches = re.findall(r"##\s+Phase\s+(\d+)", plan_text)
        if plan_phase_matches:
            max_plan_phase = max(int(m) for m in plan_phase_matches)
            if phase > max_plan_phase:
                failures.append(
                    f"Requested phase={phase} but plan.md only defines {max_plan_phase} phase(s). "
                    "Check the phase argument or update the plan."
                )

    if failures:
        return _fail("Input pre-flight failed for tasks generation.", failures)
    return _ok()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

ARTIFACT_VALIDATORS = {
    "validation": lambda cdir, phase: validate_validation_inputs(cdir),
    "specs": lambda cdir, phase: validate_specs_inputs(cdir),
    "plan": lambda cdir, phase: validate_plan_inputs(cdir),
    "tasks": lambda cdir, phase: validate_tasks_inputs(cdir, phase),
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Pre-flight input validator for /opsx-continue stages."
    )
    parser.add_argument("--artifact", required=True,
                        choices=list(ARTIFACT_VALIDATORS),
                        help="Artifact type being generated.")
    parser.add_argument("--change", required=True,
                        help="Change name (directory under openspec/changes/).")
    parser.add_argument("--phase", type=int, default=None,
                        help="Phase number (for tasks artifact, phase-iterative mode).")
    args = parser.parse_args(argv)

    cdir = CHANGES_DIR / args.change
    if not cdir.exists():
        result = _fail(
            f"Change directory not found: {cdir}",
            [f"Directory {cdir} does not exist."],
        )
        print(json.dumps(result))
        sys.exit(1)

    validator = ARTIFACT_VALIDATORS[args.artifact]
    result = validator(cdir, args.phase)

    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
