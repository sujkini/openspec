"""CLI wrapper for dashboard telemetry.

Designed to be called from Cursor agent skills via shell commands.
All commands are failure-tolerant: if the dashboard backend is not running,
they print a warning and exit 0 so the pipeline continues unaffected.

State is persisted in ``openspec/changes/<name>/.dashboard.json`` so that
run_id, phase_ids, and task PKs survive across separate /opsx-* invocations.

Usage examples::

    python -m src.telemetry.cli init-run   --change cm-830 --jira-key CM-830
    python -m src.telemetry.cli start-phase --change cm-830 --artifact repo-assessment
    python -m src.telemetry.cli end-artifact --change cm-830 --artifact repo-assessment --status passed --score 91
    python -m src.telemetry.cli start-task  --change cm-830 --task-id T1.1 --title "Scaffold middleware" --agent Backend_Agent
    python -m src.telemetry.cli end-task    --change cm-830 --task-id T1.1 --status passed
    python -m src.telemetry.cli log         --change cm-830 --agent API_Agent --type tool_call --message "Generated file..."
    python -m src.telemetry.cli end-run     --change cm-830 --status completed
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CHANGES_DIR = Path("openspec/changes")
STATE_FILE = ".dashboard.json"

ARTIFACT_PHASE_MAP: dict[str, tuple[int, str, bool]] = {
    "validation":     (1, "spec_understanding", False),
    "specs":          (1, "spec_understanding", True),
    "repo-assessment":(2, "repo_assessment",    False),
    "constitution":   (2, "repo_assessment",    True),
    "plan":           (3, "arch_planning",      True),
    "tasks":          (4, "subtask_creation",   True),
}


def _state_path(change: str) -> Path:
    return CHANGES_DIR / change / STATE_FILE


def _load_state(change: str) -> dict[str, Any]:
    p = _state_path(change)
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _save_state(change: str, state: dict[str, Any]) -> None:
    p = _state_path(change)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2) + "\n")


def _client():
    from src.telemetry.client import TelemetryClient
    return TelemetryClient()


def _out(data: dict[str, Any]) -> None:
    print(json.dumps(data))


def cmd_init_run(args: argparse.Namespace) -> None:
    """Create a new pipeline run in the dashboard and persist run_id."""
    client = _client()
    try:
        change_label = f"{args.jira_key} — {args.change}"
        run_id = client.create_run(
            change_name=change_label,
            jira_key=args.jira_key,
            branch=args.branch or f"feature/{args.change}",
        )
        state: dict[str, Any] = {
            "run_id": run_id,
            "jira_key": args.jira_key,
            "change": args.change,
            "phases": {},
            "tasks": {},
        }
        _save_state(args.change, state)
        _out({"ok": True, "run_id": run_id})
    finally:
        client.close()


def cmd_start_phase(args: argparse.Namespace) -> None:
    """Start a phase. Resolves from --artifact or explicit --phase/--phase-name."""
    state = _load_state(args.change)
    run_id = state.get("run_id")
    if not run_id:
        _out({"error": "No run_id. Run init-run first."})
        sys.exit(1)

    if args.artifact:
        mapping = ARTIFACT_PHASE_MAP.get(args.artifact)
        if not mapping:
            _out({"error": f"Unknown artifact: {args.artifact}"})
            sys.exit(1)
        phase_number, phase_name, _ = mapping
    elif args.phase and args.phase_name:
        phase_number = args.phase
        phase_name = args.phase_name
    else:
        _out({"error": "Provide --artifact or both --phase and --phase-name"})
        sys.exit(1)

    phases = state.setdefault("phases", {})
    key = str(phase_number)

    if key in phases and not phases[key].get("ended"):
        _out({"ok": True, "phase_id": phases[key]["id"], "already_running": True})
        return

    client = _client()
    try:
        phase_id = client.start_phase(run_id, phase_number, phase_name, args.model or "")
        phases[key] = {"id": phase_id, "name": phase_name, "ended": False}
        _save_state(args.change, state)
        _out({"ok": True, "phase_id": phase_id})
    finally:
        client.close()


def cmd_end_artifact(args: argparse.Namespace) -> None:
    """End an artifact's contribution to its phase.

    If this is the last artifact in the phase, the phase is ended too.
    """
    state = _load_state(args.change)
    mapping = ARTIFACT_PHASE_MAP.get(args.artifact)
    if not mapping:
        _out({"error": f"Unknown artifact: {args.artifact}"})
        sys.exit(1)

    phase_number, phase_name, is_last = mapping
    key = str(phase_number)
    phases = state.get("phases", {})
    phase_info = phases.get(key)

    if not phase_info:
        _out({"warning": f"Phase {key} not started. Skipping."})
        return

    run_id = state.get("run_id", "")
    client = _client()
    try:
        client.log_event(
            run_id=run_id,
            agent_id="Pipeline",
            event_type="state_machine",
            message=f"Artifact '{args.artifact}' completed with status: {args.status}",
        )

        if is_last or args.status == "failed":
            client.end_phase(
                phase_info["id"],
                status="passed" if args.status == "passed" else "failed",
                quality_score=args.score or 0,
                quality_label=args.label or "",
                tokens_in=args.tokens_in or 0,
                tokens_out=args.tokens_out or 0,
                iteration_count=args.iterations or 1,
            )
            phases[key]["ended"] = True
            _save_state(args.change, state)
            _out({"ok": True, "phase_ended": True, "phase_id": phase_info["id"]})
        else:
            _save_state(args.change, state)
            _out({"ok": True, "phase_ended": False, "artifact_recorded": True})
    finally:
        client.close()


def cmd_end_phase(args: argparse.Namespace) -> None:
    """Explicitly end a phase (used by /opsx-apply for code_generation)."""
    state = _load_state(args.change)
    key = str(args.phase)
    phases = state.get("phases", {})
    phase_info = phases.get(key)

    if not phase_info:
        _out({"warning": f"Phase {key} not tracked. Skipping."})
        return

    client = _client()
    try:
        client.end_phase(
            phase_info["id"],
            status=args.status,
            quality_score=args.score or 0,
            quality_label=args.label or "",
            tokens_in=args.tokens_in or 0,
            tokens_out=args.tokens_out or 0,
            iteration_count=args.iterations or 1,
        )
        phases[key]["ended"] = True
        _save_state(args.change, state)
        _out({"ok": True, "phase_id": phase_info["id"]})
    finally:
        client.close()


def cmd_start_task(args: argparse.Namespace) -> None:
    """Start tracking a task within the code_generation phase."""
    state = _load_state(args.change)
    run_id = state.get("run_id")
    if not run_id:
        _out({"error": "No run_id. Run init-run first."})
        sys.exit(1)

    phase_info = state.get("phases", {}).get("5")
    phase_id = phase_info["id"] if phase_info else ""

    client = _client()
    try:
        task_pk = client.start_task(
            run_id=run_id,
            phase_id=phase_id,
            task_id=args.task_id,
            task_title=args.title or "",
            agent_id=args.agent or "",
        )
        tasks = state.setdefault("tasks", {})
        tasks[args.task_id] = task_pk
        _save_state(args.change, state)
        _out({"ok": True, "task_pk": task_pk})
    finally:
        client.close()


def cmd_end_task(args: argparse.Namespace) -> None:
    """End a tracked task."""
    state = _load_state(args.change)
    tasks = state.get("tasks", {})
    task_pk = tasks.get(args.task_id)

    if not task_pk:
        _out({"warning": f"Task {args.task_id} not tracked. Skipping."})
        return

    client = _client()
    try:
        client.end_task(
            task_pk,
            status=args.status,
            tokens_in=args.tokens_in or 0,
            tokens_out=args.tokens_out or 0,
            cost_usd=args.cost or 0,
            self_correction_loops=args.loops or 0,
        )
        _out({"ok": True, "task_pk": task_pk})
    finally:
        client.close()


def cmd_log(args: argparse.Namespace) -> None:
    """Log an agent event."""
    state = _load_state(args.change)
    run_id = state.get("run_id")
    if not run_id:
        _out({"error": "No run_id. Run init-run first."})
        sys.exit(1)

    task_pk = None
    if args.task_id:
        task_pk = state.get("tasks", {}).get(args.task_id)

    client = _client()
    try:
        event_id = client.log_event(
            run_id=run_id,
            agent_id=args.agent,
            event_type=args.type,
            message=args.message,
            task_id=task_pk,
        )
        _out({"ok": True, "event_id": event_id})
    finally:
        client.close()


def cmd_end_run(args: argparse.Namespace) -> None:
    """End the pipeline run."""
    state = _load_state(args.change)
    run_id = state.get("run_id")
    if not run_id:
        _out({"warning": "No run_id. Nothing to end."})
        return

    client = _client()
    try:
        client.end_run(run_id, status=args.status)
        _out({"ok": True, "run_id": run_id, "status": args.status})
    finally:
        client.close()


def cmd_status(args: argparse.Namespace) -> None:
    """Print current dashboard tracking state for a change."""
    state = _load_state(args.change)
    if not state:
        _out({"tracked": False, "message": "No dashboard state for this change."})
    else:
        _out({"tracked": True, **state})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="telemetry-cli",
        description="Dashboard telemetry CLI for OpenSpec pipeline",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # init-run
    r = sub.add_parser("init-run", help="Create a new dashboard run")
    r.add_argument("--change", required=True)
    r.add_argument("--jira-key", required=True)
    r.add_argument("--branch", default="")

    # start-phase
    sp = sub.add_parser("start-phase", help="Start tracking a phase")
    sp.add_argument("--change", required=True)
    sp.add_argument("--artifact", help="Artifact ID (auto-maps to phase)")
    sp.add_argument("--phase", type=int, help="Explicit phase number")
    sp.add_argument("--phase-name", help="Explicit phase name")
    sp.add_argument("--model", default="")

    # end-artifact
    ea = sub.add_parser("end-artifact", help="Record artifact completion; ends phase if last in group")
    ea.add_argument("--change", required=True)
    ea.add_argument("--artifact", required=True)
    ea.add_argument("--status", required=True, choices=["passed", "failed"])
    ea.add_argument("--score", type=float, default=0)
    ea.add_argument("--label", default="")
    ea.add_argument("--tokens-in", type=int, default=0)
    ea.add_argument("--tokens-out", type=int, default=0)
    ea.add_argument("--iterations", type=int, default=1)

    # end-phase
    ep = sub.add_parser("end-phase", help="Explicitly end a phase")
    ep.add_argument("--change", required=True)
    ep.add_argument("--phase", type=int, required=True)
    ep.add_argument("--status", required=True, choices=["passed", "failed", "waiting"])
    ep.add_argument("--score", type=float, default=0)
    ep.add_argument("--label", default="")
    ep.add_argument("--tokens-in", type=int, default=0)
    ep.add_argument("--tokens-out", type=int, default=0)
    ep.add_argument("--iterations", type=int, default=1)

    # start-task
    st = sub.add_parser("start-task", help="Start tracking a task")
    st.add_argument("--change", required=True)
    st.add_argument("--task-id", required=True)
    st.add_argument("--title", default="")
    st.add_argument("--agent", default="")

    # end-task
    et = sub.add_parser("end-task", help="End a tracked task")
    et.add_argument("--change", required=True)
    et.add_argument("--task-id", required=True)
    et.add_argument("--status", required=True, choices=["passed", "failed"])
    et.add_argument("--tokens-in", type=int, default=0)
    et.add_argument("--tokens-out", type=int, default=0)
    et.add_argument("--cost", type=float, default=0)
    et.add_argument("--loops", type=int, default=0)

    # log
    lg = sub.add_parser("log", help="Log an agent event")
    lg.add_argument("--change", required=True)
    lg.add_argument("--agent", required=True)
    lg.add_argument("--type", required=True, choices=["tool_call", "harness_alert", "self_correction", "state_machine"])
    lg.add_argument("--message", required=True)
    lg.add_argument("--task-id", default=None)

    # end-run
    er = sub.add_parser("end-run", help="End the pipeline run")
    er.add_argument("--change", required=True)
    er.add_argument("--status", default="completed", choices=["completed", "failed", "waiting_for_human"])

    # status
    ss = sub.add_parser("status", help="Show dashboard tracking state")
    ss.add_argument("--change", required=True)

    return p


_DISPATCH = {
    "init-run": cmd_init_run,
    "start-phase": cmd_start_phase,
    "end-artifact": cmd_end_artifact,
    "end-phase": cmd_end_phase,
    "start-task": cmd_start_task,
    "end-task": cmd_end_task,
    "log": cmd_log,
    "end-run": cmd_end_run,
    "status": cmd_status,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handler = _DISPATCH.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)
    try:
        handler(args)
    except Exception as exc:
        print(
            json.dumps({"warning": f"Dashboard telemetry unavailable: {exc}"}),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
