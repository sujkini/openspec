"""Generate metrics-report.json from events.jsonl and filesystem artifacts.

Reconstructs run, phases, tasks, events, global_health, token_burn, and
artifact_edits entirely from local files — no database, no server.
"""
from __future__ import annotations

import json
import logging
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .change_metrics import (
    ARTIFACT_PHASE_MAP,
    count_feedback_rounds,
    phase5_iteration_count,
    phase5_should_close,
    phase_duration_s,
    phase_iteration_count,
    read_eval_refinement_round,
    read_task_refinement_rounds,
)

logger = logging.getLogger(__name__)

CHANGES_DIR = Path("openspec/changes")


def _detect_operator_name() -> str:
    """Extract the operator/repo name from ``git remote get-url origin``."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        url = result.stdout.strip()
        if not url:
            return ""
        name = url.rstrip("/").rsplit("/", 1)[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name
    except Exception:
        return ""


def _read_events(change_dir: Path) -> list[dict[str, Any]]:
    events_file = change_dir / "telemetry" / "events.jsonl"
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


def _reconstruct_run(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build run object from the first run_create event."""
    for ev in events:
        if ev.get("type") == "run_create":
            run: dict[str, Any] = {
                "id": ev.get("id", ""),
                "change_name": ev.get("change_name", ""),
                "jira_key": ev.get("jira_key", ""),
                "branch": ev.get("branch", ""),
                "status": "running",
                "started_at": ev.get("ts", ""),
                "completed_at": None,
                "total_tokens_in": 0,
                "total_tokens_out": 0,
                "total_cost_usd": 0.0,
            }
            break
    else:
        return {}

    for ev in events:
        if ev.get("type") == "run_end":
            run["status"] = ev.get("status", "completed")
            run["completed_at"] = ev.get("ts")
    return run


def _reconstruct_phases(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build phase objects from phase_start / phase_end / phase_progress events."""
    phases: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for ev in events:
        etype = ev.get("type", "")
        if etype == "phase_start":
            pid = ev.get("id", "")
            if pid and pid not in phases:
                order.append(pid)
            phases[pid] = {
                "id": pid,
                "run_id": ev.get("run_id", ""),
                "phase_number": ev.get("phase_number", 0),
                "phase_name": ev.get("phase_name", ""),
                "model_id": ev.get("model_id", ""),
                "status": "running",
                "started_at": ev.get("ts", ""),
                "completed_at": None,
                "tokens_in": 0,
                "tokens_out": 0,
                "quality_score": 0,
                "quality_label": "",
                "iteration_count": 1,
                "duration_s": 0.0,
            }
        elif etype == "phase_end":
            pid = ev.get("phase_id", "")
            if pid in phases:
                phases[pid].update({
                    "status": ev.get("status", "passed"),
                    "completed_at": ev.get("ts"),
                    "tokens_in": ev.get("tokens_in", phases[pid]["tokens_in"]),
                    "tokens_out": ev.get("tokens_out", phases[pid]["tokens_out"]),
                    "quality_score": ev.get("quality_score", phases[pid]["quality_score"]),
                    "quality_label": ev.get("quality_label", phases[pid]["quality_label"]),
                    "iteration_count": ev.get("iteration_count", phases[pid]["iteration_count"]),
                })
                if ev.get("duration_s") is not None:
                    phases[pid]["duration_s"] = ev["duration_s"]
        elif etype == "phase_progress":
            pid = ev.get("phase_id", "")
            if pid in phases:
                for key in ("tokens_in", "tokens_out", "quality_score", "quality_label", "iteration_count"):
                    if ev.get(key) is not None:
                        phases[pid][key] = ev[key]
                if ev.get("duration_s") is not None:
                    phases[pid]["duration_s"] = ev["duration_s"]

    return [phases[pid] for pid in order if pid in phases]


def _reconstruct_tasks(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build task objects from task_start / task_end events."""
    tasks: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for ev in events:
        etype = ev.get("type", "")
        if etype == "task_start":
            tid = ev.get("id", "")
            if tid and tid not in tasks:
                order.append(tid)
            tasks[tid] = {
                "id": tid,
                "run_id": ev.get("run_id", ""),
                "phase_id": ev.get("phase_id", ""),
                "task_id": ev.get("task_id", ""),
                "task_title": ev.get("task_title", ""),
                "agent_id": ev.get("agent_id", ""),
                "status": "running",
                "started_at": ev.get("ts", ""),
                "completed_at": None,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "self_correction_loops": 0,
            }
        elif etype == "task_end":
            tpk = ev.get("task_pk", "")
            if tpk in tasks:
                tasks[tpk].update({
                    "status": ev.get("status", "passed"),
                    "completed_at": ev.get("ts"),
                    "tokens_in": ev.get("tokens_in", 0),
                    "tokens_out": ev.get("tokens_out", 0),
                    "cost_usd": ev.get("cost_usd", 0.0),
                    "self_correction_loops": ev.get("self_correction_loops", 0),
                })

    return [tasks[tid] for tid in order if tid in tasks]


def _collect_log_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract log_event entries."""
    return [
        {
            "id": ev.get("id", ""),
            "ts": ev.get("ts", ""),
            "run_id": ev.get("run_id", ""),
            "task_id": ev.get("task_id"),
            "agent_id": ev.get("agent_id", ""),
            "event_type": ev.get("event_type", ""),
            "message": ev.get("message", ""),
            "metadata_json": ev.get("metadata_json"),
        }
        for ev in events
        if ev.get("type") == "log_event"
    ]


def _compute_global_health(
    run: dict[str, Any],
    phases: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    change_dir: Path,
) -> dict[str, Any]:
    """Compute global health metrics from in-memory data."""
    phase_tokens_in = sum(p.get("tokens_in", 0) for p in phases)
    phase_tokens_out = sum(p.get("tokens_out", 0) for p in phases)
    total_tokens = phase_tokens_in + phase_tokens_out
    if total_tokens == 0:
        total_tokens = run.get("total_tokens_in", 0) + run.get("total_tokens_out", 0)

    wall_time = 0.0
    started_at = run.get("started_at", "")
    if started_at:
        try:
            start = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
            end_raw = run.get("completed_at")
            if end_raw:
                end = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00"))
            else:
                end = datetime.now(timezone.utc)
            wall_time = max(0.0, (end - start).total_seconds())
        except (TypeError, ValueError):
            pass

    total_phases = len(phases)
    first_pass = sum(
        1 for p in phases
        if p.get("iteration_count", 1) == 1 and p.get("status") == "passed"
    )

    compliance = (first_pass / total_phases * 100) if total_phases > 0 else 100.0
    gate_passing = (first_pass / total_phases * 100) if total_phases > 0 else 100.0
    total_refinement = sum(max(0, p.get("iteration_count", 1) - 1) for p in phases)
    human_rejection = (total_refinement / total_phases * 100) if total_phases > 0 else 0.0

    phase_duration = sum(p.get("duration_s", 0) for p in phases)
    if phase_duration > wall_time:
        wall_time = phase_duration

    tasks_total = len(tasks)
    tasks_passed = sum(1 for t in tasks if t.get("status") == "passed")
    success_rate = (tasks_passed / tasks_total * 100) if tasks_total > 0 else 100.0

    task_tokens = sum(t.get("tokens_in", 0) + t.get("tokens_out", 0) for t in tasks)
    total_tokens += task_tokens

    return {
        "total_tokens_consumed": total_tokens,
        "total_run_cost_usd": 0.0,
        "cumulative_wall_time_s": round(wall_time, 1),
        "compliance_index": round(compliance, 1),
        "gate_passing_rate": round(gate_passing, 1),
        "human_rejection_rate": round(human_rejection, 1),
        "total_refinement_iterations": total_refinement,
        "agent_success_rate": round(success_rate, 1),
        "tasks_passed": tasks_passed,
        "tasks_total": tasks_total,
    }


def _compute_token_burn(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Group task tokens by agent_id."""
    by_agent: dict[str, dict[str, Any]] = defaultdict(lambda: {"tokens": 0, "cost_usd": 0.0})

    for t in tasks:
        agent = t.get("agent_id", "") or "unknown"
        by_agent[agent]["tokens"] += t.get("tokens_in", 0) + t.get("tokens_out", 0)
        by_agent[agent]["cost_usd"] += t.get("cost_usd", 0.0)

    entries = [
        {"agent_id": agent, "tokens": data["tokens"], "cost_usd": round(data["cost_usd"], 4)}
        for agent, data in sorted(by_agent.items(), key=lambda x: -x[1]["tokens"])
    ]
    return {
        "entries": entries,
        "total_tokens": sum(e["tokens"] for e in entries),
        "total_cost_usd": round(sum(e["cost_usd"] for e in entries), 4),
    }


def _compute_artifact_edits(change_dir: Path) -> dict[str, Any]:
    """Compute artifact edit metrics from filesystem."""
    entries: list[dict[str, Any]] = []

    for artifact_id, (_phase_num, phase_name, _is_last) in ARTIFACT_PHASE_MAP.items():
        artifact_path = change_dir / f"{artifact_id}.md"
        if not artifact_path.exists():
            artifact_path = change_dir / f"{artifact_id}.json"
        if not artifact_path.exists():
            continue
        eval_ref = read_eval_refinement_round(change_dir, artifact_id)
        fb = count_feedback_rounds(change_dir, artifact_id)
        entries.append({
            "artifact_id": artifact_id,
            "phase_name": phase_name,
            "eval_refinements": eval_ref,
            "feedback_rounds": fb,
            "total_edits": eval_ref + fb,
        })

    return {
        "artifacts": entries,
        "total_edits": sum(e["total_edits"] for e in entries),
    }


def generate_report(change: str) -> Path:
    """Generate metrics-report.json for a single change.

    Returns the path to the written report.
    """
    change_dir = CHANGES_DIR / change
    events = _read_events(change_dir)

    run = _reconstruct_run(events)
    phases = _reconstruct_phases(events)
    tasks = _reconstruct_tasks(events)
    log_events = _collect_log_events(events)

    global_health = _compute_global_health(run, phases, tasks, change_dir) if run else {
        "total_tokens_consumed": 0,
        "total_run_cost_usd": 0.0,
        "cumulative_wall_time_s": 0.0,
        "compliance_index": 100.0,
        "gate_passing_rate": 100.0,
        "human_rejection_rate": 0.0,
        "total_refinement_iterations": 0,
        "agent_success_rate": 100.0,
        "tasks_passed": 0,
        "tasks_total": 0,
    }
    token_burn = _compute_token_burn(tasks)
    artifact_edits = _compute_artifact_edits(change_dir)

    report: dict[str, Any] = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "operator_name": _detect_operator_name(),
        "run": run,
        "phases": phases,
        "tasks": tasks,
        "events": log_events,
        "global_health": global_health,
        "token_burn": token_burn,
        "artifact_edits": artifact_edits,
    }

    report_path = change_dir / "telemetry" / "metrics-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    logger.info("Wrote metrics report: %s", report_path)
    return report_path


def main() -> None:
    """CLI entry point: python -m openspec.telemetry.report --change <name>"""
    import argparse
    parser = argparse.ArgumentParser(description="Generate metrics report for an OpenSpec change")
    parser.add_argument("--change", required=True, help="Change slug (e.g. cm-830)")
    args = parser.parse_args()
    path = generate_report(args.change)
    print(json.dumps({"ok": True, "path": str(path)}))


if __name__ == "__main__":
    main()
