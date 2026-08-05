"""Compute QE metrics from E2E workflow artifacts and telemetry events.

Reads artifacts from ``openspec/changes/<change>/e2e/`` and events from
``openspec/changes/<change>/telemetry/e2e-events.jsonl``.
Writes ``qe-metrics.json`` to ``openspec/changes/<change>/telemetry/``.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .tokens import count_tokens, estimate_file_tokens

logger = logging.getLogger(__name__)

CHANGES_DIR = Path("openspec/changes")

PRICE_TABLE: dict[str, dict[str, float]] = {
    "default": {"input": 3.0, "output": 15.0},
    "claude-sonnet": {"input": 3.0, "output": 15.0},
    "claude-opus": {"input": 15.0, "output": 75.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
}


def _estimate_cost(tokens_in: int, tokens_out: int, model: str = "default") -> float:
    rates = PRICE_TABLE.get(model, PRICE_TABLE["default"])
    return (tokens_in * rates["input"] + tokens_out * rates["output"]) / 1_000_000


# ---------------------------------------------------------------------------
# Event parsing
# ---------------------------------------------------------------------------

def _read_e2e_events(change_dir: Path) -> list[dict[str, Any]]:
    events_file = change_dir / "telemetry" / "e2e-events.jsonl"
    if not events_file.exists():
        return []
    events = []
    for line in events_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


# ---------------------------------------------------------------------------
# Metric 1: AC → Scenario Coverage %
# ---------------------------------------------------------------------------

def _count_acceptance_criteria(specs_path: Path) -> tuple[int, list[str]]:
    """Count acceptance criteria IDs in specs.md (Given/When/Then blocks + FR-xxx)."""
    if not specs_path.exists():
        return 0, []
    content = specs_path.read_text()
    fr_ids = re.findall(r"\b(FR-\d+)\b", content)
    fr_ids = list(dict.fromkeys(fr_ids))
    gwt_count = len(re.findall(
        r"\*\*Given\*\*.*?\*\*When\*\*.*?\*\*Then\*\*", content, re.DOTALL
    ))
    us_ids = re.findall(r"\b(US-\d+)\b", content)
    us_ids = list(dict.fromkeys(us_ids))
    sc_ids = re.findall(r"\b(SC-\d+)\b", content)
    sc_ids = list(dict.fromkeys(sc_ids))
    all_ids = fr_ids + us_ids + sc_ids
    total = max(len(all_ids), gwt_count)
    return total, all_ids


def _count_covered_criteria(test_plan_path: Path, all_ids: list[str]) -> tuple[int, list[str]]:
    """Count which AC IDs are referenced in the test plan traceability."""
    if not test_plan_path.exists():
        return 0, []
    content = test_plan_path.read_text()
    covered = [aid for aid in all_ids if aid in content]
    uncovered = [aid for aid in all_ids if aid not in content]
    return len(covered), uncovered


def compute_ac_coverage(change_dir: Path) -> dict[str, Any]:
    specs_path = change_dir / "specs.md"
    test_plan_path = change_dir / "e2e" / "test-plan.md"

    total, all_ids = _count_acceptance_criteria(specs_path)
    if total == 0:
        return {
            "total_acceptance_criteria": 0,
            "criteria_covered_by_tests": 0,
            "coverage_pct": None,
            "uncovered": [],
            "source": "no_specs_available",
        }

    covered_count, uncovered = _count_covered_criteria(test_plan_path, all_ids)
    pct = (covered_count / total * 100) if total > 0 else 0.0
    return {
        "total_acceptance_criteria": total,
        "criteria_covered_by_tests": covered_count,
        "coverage_pct": round(pct, 1),
        "uncovered": uncovered,
    }


# ---------------------------------------------------------------------------
# Metric 2: Automation Coverage %
# ---------------------------------------------------------------------------

def _count_scenarios_in_plan(revised_plan_path: Path) -> int:
    """Count consolidated journeys/test cases in revised-test-plan.md."""
    if not revised_plan_path.exists():
        return 0
    content = revised_plan_path.read_text()
    journey_headers = re.findall(r"^#{1,3}\s+Journey\s+\d+", content, re.MULTILINE)
    if journey_headers:
        return len(journey_headers)
    e2e_ids = re.findall(r"\b(E2E-\d+|NEG-\d+|REG-\d+)\b", content)
    return len(set(e2e_ids))


def _count_automated(generated_dir: Path) -> int:
    """Count generated test files."""
    if not generated_dir.exists():
        return 0
    return len(list(generated_dir.glob("*_test.go")))


def compute_automation_coverage(change_dir: Path) -> dict[str, Any]:
    revised_plan = change_dir / "e2e" / "revised-test-plan.md"
    generated_dir = change_dir / "e2e" / "generated"

    total = _count_scenarios_in_plan(revised_plan)
    automated = _count_automated(generated_dir)
    manual = max(0, total - automated)
    pct = (automated / total * 100) if total > 0 else 0.0

    return {
        "total_scenarios": total,
        "automated": automated,
        "manual": manual,
        "coverage_pct": round(pct, 1),
    }


# ---------------------------------------------------------------------------
# Metric 3: E2E First-Pass Pass Rate
# ---------------------------------------------------------------------------

def compute_first_pass_rate(events: list[dict[str, Any]]) -> dict[str, Any]:
    """From the first execution attempt (attempt=1), compute pass rate."""
    first_attempts = [
        ev for ev in events
        if ev.get("type") == "e2e_execution" and ev.get("attempt", 1) == 1
    ]
    if not first_attempts:
        return {
            "tests_executed": 0,
            "tests_passed_first_run": 0,
            "tests_failed_first_run": 0,
            "pass_rate_pct": None,
            "execution_source": None,
            "reason": "execution_skipped",
        }

    ev = first_attempts[-1]
    tests_run = ev.get("tests_run", 0)
    tests_passed = ev.get("tests_passed", 0)
    tests_failed = ev.get("tests_failed", 0)
    pct = (tests_passed / tests_run * 100) if tests_run > 0 else 0.0

    return {
        "tests_executed": tests_run,
        "tests_passed_first_run": tests_passed,
        "tests_failed_first_run": tests_failed,
        "pass_rate_pct": round(pct, 1),
        "execution_source": ev.get("source", "local"),
    }


# ---------------------------------------------------------------------------
# Metric 4: Flake Rate
# ---------------------------------------------------------------------------

def compute_flake_rate(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Retries that pass without code change (same file_hash)."""
    executions = [ev for ev in events if ev.get("type") == "e2e_execution"]
    if len(executions) < 2:
        return {
            "total_retries": 0,
            "retries_passed_no_code_change": 0,
            "flake_rate_pct": 0.0,
        }

    retries = [ev for ev in executions if ev.get("attempt", 1) > 1]
    if not retries:
        return {
            "total_retries": 0,
            "retries_passed_no_code_change": 0,
            "flake_rate_pct": 0.0,
        }

    first_hash = executions[0].get("file_hash", "")
    flakes = 0
    for ev in retries:
        if ev.get("file_hash") == first_hash and ev.get("exit_code", 1) == 0:
            flakes += 1

    total_retries = len(retries)
    pct = (flakes / total_retries * 100) if total_retries > 0 else 0.0

    return {
        "total_retries": total_retries,
        "retries_passed_no_code_change": flakes,
        "flake_rate_pct": round(pct, 1),
    }


# ---------------------------------------------------------------------------
# Metric 5: Bugs Found / Verified
# ---------------------------------------------------------------------------

def compute_bugs(events: list[dict[str, Any]]) -> dict[str, Any]:
    bugs_found: dict[str, dict[str, Any]] = {}
    bugs_verified: set[str] = set()

    for ev in events:
        if ev.get("type") == "e2e_bug_found":
            name = ev.get("test_name", "")
            if name:
                bugs_found[name] = {
                    "test_name": name,
                    "failure_message": ev.get("failure_message", ""),
                    "rca": ev.get("rca", ""),
                }
        elif ev.get("type") == "e2e_bug_verified":
            name = ev.get("test_name", "")
            if name:
                bugs_verified.add(name)

    details = []
    for name, info in bugs_found.items():
        details.append({
            "test_name": name,
            "status": "verified" if name in bugs_verified else "found",
            "rca": info.get("rca", ""),
        })

    return {
        "found": len(bugs_found),
        "verified": len(bugs_verified),
        "details": details,
    }


# ---------------------------------------------------------------------------
# Metric 6: Triage Accuracy %
# ---------------------------------------------------------------------------

def compute_triage_accuracy(events: list[dict[str, Any]]) -> dict[str, Any]:
    triages = [ev for ev in events if ev.get("type") == "e2e_triage"]
    if not triages:
        return {
            "total_triaged": 0,
            "correct": 0,
            "accuracy_pct": None,
            "reason": "no_triage_data",
        }

    confirmed = [t for t in triages if t.get("user_confirmed") is not None]
    if not confirmed:
        return {
            "total_triaged": len(triages),
            "correct": 0,
            "accuracy_pct": None,
            "reason": "user_skipped_confirmation",
        }

    correct = sum(1 for t in confirmed if t.get("user_confirmed") is True)
    pct = (correct / len(confirmed) * 100) if confirmed else 0.0

    return {
        "total_triaged": len(confirmed),
        "correct": correct,
        "accuracy_pct": round(pct, 1),
    }


# ---------------------------------------------------------------------------
# Metric 7: QE Tokens / $ / Wall Time
# ---------------------------------------------------------------------------

def compute_cost_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute token usage, cost, and wall time from stage events."""
    stages: list[dict[str, Any]] = []
    stage_map: dict[str, dict[str, Any]] = {}

    total_in = 0
    total_out = 0
    run_start: str | None = None
    run_end: str | None = None

    for ev in events:
        etype = ev.get("type", "")
        if etype == "e2e_run_start":
            run_start = ev.get("ts")
        elif etype == "e2e_run_end":
            run_end = ev.get("ts")
        elif etype == "e2e_stage_start":
            stage_map[ev.get("id", "")] = {
                "stage_name": ev.get("stage_name", ""),
                "started_at": ev.get("ts"),
            }
        elif etype == "e2e_stage_end":
            sid = ev.get("stage_id", "")
            start_info = stage_map.get(sid, {})
            t_in = ev.get("tokens_in", 0)
            t_out = ev.get("tokens_out", 0)
            total_in += t_in
            total_out += t_out
            stages.append({
                "stage": start_info.get("stage_name", "unknown"),
                "tokens_in": t_in,
                "tokens_out": t_out,
                "duration_s": ev.get("duration_s", 0.0),
            })

    wall_time = 0.0
    if run_start and run_end:
        try:
            t0 = datetime.fromisoformat(run_start.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(run_end.replace("Z", "+00:00"))
            wall_time = max(0.0, (t1 - t0).total_seconds())
        except (TypeError, ValueError):
            pass

    if wall_time == 0.0:
        wall_time = sum(s.get("duration_s", 0) for s in stages)

    cost = _estimate_cost(total_in, total_out)

    return {
        "tokens_in": total_in,
        "tokens_out": total_out,
        "tokens_total": total_in + total_out,
        "estimated_cost_usd": round(cost, 4),
        "wall_time_s": round(wall_time, 1),
        "per_stage": stages,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_qe_report(change: str) -> Path:
    """Generate qe-metrics.json for a change's E2E workflow run.

    Returns the path to the written report.
    """
    change_dir = CHANGES_DIR / change
    events = _read_e2e_events(change_dir)

    run_event = next(
        (ev for ev in events if ev.get("type") == "e2e_run_start"),
        {},
    )

    ac_coverage = compute_ac_coverage(change_dir)
    automation = compute_automation_coverage(change_dir)
    first_pass = compute_first_pass_rate(events)
    flake = compute_flake_rate(events)
    bugs = compute_bugs(events)
    triage = compute_triage_accuracy(events)
    cost = compute_cost_metrics(events)

    report: dict[str, Any] = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "change_name": change,
        "pr_url": run_event.get("pr_url", ""),
        "phase": run_event.get("phase"),
        "mode": run_event.get("mode", "phase-iterative"),
        "ac_scenario_coverage": ac_coverage,
        "automation_coverage": automation,
        "first_pass_rate": first_pass,
        "flake_rate": flake,
        "bugs": bugs,
        "triage_accuracy": triage,
        "cost": cost,
    }

    report_path = change_dir / "telemetry" / "qe-metrics.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    logger.info("Wrote QE metrics report: %s", report_path)
    return report_path


def main() -> None:
    """CLI entry point: python -m openspec.telemetry.qe_metrics --change <name>"""
    import argparse
    parser = argparse.ArgumentParser(description="Generate QE metrics report for an OpenSpec change")
    parser.add_argument("--change", required=True, help="Change slug (e.g. cm-830)")
    args = parser.parse_args()
    path = generate_qe_report(args.change)
    print(json.dumps({"ok": True, "path": str(path)}))


if __name__ == "__main__":
    main()
