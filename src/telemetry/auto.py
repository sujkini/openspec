"""Automatic telemetry hooks for the OpenSpec pipeline.

This module replaces the manual telemetry calls that were previously embedded
in SKILL.md files. It wraps key openspec CLI lifecycle events so telemetry
is emitted transparently without the AI agent needing to know about it.

Usage from a shell wrapper or post-command hook:

    python -m src.telemetry.auto on-new    --change cm-830 --jira-key CM-830
    python -m src.telemetry.auto on-artifact-complete --change cm-830 --artifact specs --status passed --score 91
    python -m src.telemetry.auto on-task-start --change cm-830 --task-id T1_1 --agent API_Agent
    python -m src.telemetry.auto on-task-complete --change cm-830 --task-id T1_1 --status passed
    python -m src.telemetry.auto on-apply-complete --change cm-830
    python -m src.telemetry.auto sync --change cm-830
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CHANGES_DIR = Path("openspec/changes")
STATE_FILE = ".dashboard.json"

ARTIFACT_PHASE_MAP: dict[str, tuple[int, str, bool]] = {
    "validation":      (1, "spec_understanding", False),
    "specs":           (1, "spec_understanding", True),
    "repo-assessment": (2, "repo_assessment",    False),
    "constitution":    (2, "repo_assessment",    True),
    "plan":            (3, "arch_planning",      True),
    "tasks":           (4, "subtask_creation",   True),
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


def _estimate_artifact(change: str, artifact_id: str) -> tuple[int, int]:
    from src.telemetry.tokens import estimate_artifact_tokens
    return estimate_artifact_tokens(CHANGES_DIR / change, artifact_id)


def _estimate_task(change: str, task_id: str) -> tuple[int, int]:
    from src.telemetry.tokens import estimate_task_tokens
    return estimate_task_tokens(CHANGES_DIR / change, task_id)


def _out(data: dict[str, Any]) -> None:
    print(json.dumps(data))


def on_new(args: argparse.Namespace) -> None:
    """Called after /opsx-new creates a change directory."""
    client = _client()
    try:
        change_label = f"{args.jira_key} — {args.change}"
        run_id = client.create_run(
            change_name=change_label,
            jira_key=args.jira_key,
            branch=getattr(args, "branch", "") or f"feature/{args.change}",
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


def on_artifact_start(args: argparse.Namespace) -> None:
    """Called when an artifact creation begins."""
    state = _load_state(args.change)
    run_id = state.get("run_id")
    if not run_id:
        _out({"skip": True, "reason": "no run_id"})
        return

    mapping = ARTIFACT_PHASE_MAP.get(args.artifact)
    if not mapping:
        _out({"skip": True, "reason": f"unknown artifact: {args.artifact}"})
        return

    phase_number, phase_name, _ = mapping
    key = str(phase_number)
    phases = state.setdefault("phases", {})

    if key in phases and not phases[key].get("ended"):
        _out({"ok": True, "phase_id": phases[key]["id"], "already_running": True})
        return

    client = _client()
    try:
        phase_id = client.start_phase(run_id, phase_number, phase_name)
        phases[key] = {"id": phase_id, "name": phase_name, "ended": False}
        _save_state(args.change, state)
        _out({"ok": True, "phase_id": phase_id})
    finally:
        client.close()


def on_artifact_complete(args: argparse.Namespace) -> None:
    """Called after an artifact is approved by the user."""
    state = _load_state(args.change)
    mapping = ARTIFACT_PHASE_MAP.get(args.artifact)
    if not mapping:
        _out({"skip": True, "reason": f"unknown artifact: {args.artifact}"})
        return

    phase_number, phase_name, is_last = mapping
    key = str(phase_number)
    phases = state.get("phases", {})
    phase_info = phases.get(key)

    if not phase_info:
        _out({"skip": True, "reason": f"phase {key} not started"})
        return

    run_id = state.get("run_id", "")
    tokens_in, tokens_out = _estimate_artifact(args.change, args.artifact)

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
                quality_score=getattr(args, "score", 0) or 0,
                quality_label=getattr(args, "label", "") or "",
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                iteration_count=getattr(args, "iterations", 1) or 1,
            )
            phases[key]["ended"] = True
            _save_state(args.change, state)
            _out({"ok": True, "phase_ended": True, "tokens_in": tokens_in, "tokens_out": tokens_out})
        else:
            _save_state(args.change, state)
            _out({"ok": True, "phase_ended": False, "tokens_in": tokens_in, "tokens_out": tokens_out})
    finally:
        client.close()


def on_apply_start(args: argparse.Namespace) -> None:
    """Called when /opsx-apply begins the task loop (phase 5)."""
    state = _load_state(args.change)
    run_id = state.get("run_id")
    if not run_id:
        _out({"skip": True, "reason": "no run_id"})
        return

    phases = state.setdefault("phases", {})
    if "5" in phases and not phases["5"].get("ended"):
        _out({"ok": True, "phase_id": phases["5"]["id"], "already_running": True})
        return

    client = _client()
    try:
        phase_id = client.start_phase(run_id, 5, "code_generation")
        phases["5"] = {"id": phase_id, "name": "code_generation", "ended": False}
        _save_state(args.change, state)
        _out({"ok": True, "phase_id": phase_id})
    finally:
        client.close()


def on_task_start(args: argparse.Namespace) -> None:
    """Called before each task in /opsx-apply."""
    state = _load_state(args.change)
    run_id = state.get("run_id")
    if not run_id:
        _out({"skip": True, "reason": "no run_id"})
        return

    phase_info = state.get("phases", {}).get("5")
    phase_id = phase_info["id"] if phase_info else ""

    client = _client()
    try:
        task_pk = client.start_task(
            run_id=run_id,
            phase_id=phase_id,
            task_id=args.task_id,
            task_title=getattr(args, "title", "") or "",
            agent_id=getattr(args, "agent", "") or "",
        )
        tasks = state.setdefault("tasks", {})
        tasks[args.task_id] = task_pk
        _save_state(args.change, state)
        _out({"ok": True, "task_pk": task_pk})
    finally:
        client.close()


def on_task_complete(args: argparse.Namespace) -> None:
    """Called after a task is approved in /opsx-apply."""
    state = _load_state(args.change)
    tasks = state.get("tasks", {})
    task_pk = tasks.get(args.task_id)

    if not task_pk:
        _out({"skip": True, "reason": f"task {args.task_id} not tracked"})
        return

    tokens_in, tokens_out = _estimate_task(args.change, args.task_id)

    client = _client()
    try:
        client.end_task(
            task_pk,
            status=args.status,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=0,
            self_correction_loops=getattr(args, "loops", 0) or 0,
        )
        _out({"ok": True, "task_pk": task_pk, "tokens_in": tokens_in, "tokens_out": tokens_out})
    finally:
        client.close()


def on_apply_complete(args: argparse.Namespace) -> None:
    """Called after all tasks in /opsx-apply are approved (phase 5 done)."""
    state = _load_state(args.change)
    phases = state.get("phases", {})
    phase_info = phases.get("5")

    if not phase_info:
        _out({"skip": True, "reason": "phase 5 not tracked"})
        return

    change_dir = CHANGES_DIR / args.change
    total_tokens_in = 0
    total_tokens_out = 0
    for task_id in state.get("tasks", {}):
        ti, to = _estimate_task(args.change, task_id)
        total_tokens_in += ti
        total_tokens_out += to

    run_id = state.get("run_id", "")
    client = _client()
    try:
        client.end_phase(
            phase_info["id"],
            status="passed",
            quality_label=getattr(args, "label", "") or "all tasks approved",
            tokens_in=total_tokens_in,
            tokens_out=total_tokens_out,
            iteration_count=1,
        )
        phases["5"]["ended"] = True

        client.end_run(run_id, status="completed")
        _save_state(args.change, state)
        _out({"ok": True, "tokens_in": total_tokens_in, "tokens_out": total_tokens_out})
    finally:
        client.close()


def sync(args: argparse.Namespace) -> None:
    """Sync filesystem state to dashboard — re-scan artifacts and update phases."""
    state = _load_state(args.change)
    run_id = state.get("run_id")
    if not run_id:
        _out({"skip": True, "reason": "no run_id — run on-new first"})
        return

    change_dir = CHANGES_DIR / args.change
    updated = []

    for artifact_id, (phase_number, phase_name, is_last) in ARTIFACT_PHASE_MAP.items():
        artifact_path = change_dir / f"{artifact_id}.md"
        if not artifact_path.exists():
            artifact_path = change_dir / f"{artifact_id}.json"
        if not artifact_path.exists():
            continue

        key = str(phase_number)
        phases = state.setdefault("phases", {})
        if key in phases and phases[key].get("ended"):
            continue

        tokens_in, tokens_out = _estimate_artifact(args.change, artifact_id)

        client = _client()
        try:
            if key not in phases:
                phase_id = client.start_phase(run_id, phase_number, phase_name)
                phases[key] = {"id": phase_id, "name": phase_name, "ended": False}

            if is_last:
                eval_path = change_dir / "eval-results" / f"{artifact_id}.yaml"
                score = 0
                if eval_path.exists():
                    import yaml
                    eval_data = yaml.safe_load(eval_path.read_text()) or {}
                    score = eval_data.get("overall_score", 0)

                client.end_phase(
                    phases[key]["id"],
                    status="passed",
                    quality_score=score,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                )
                phases[key]["ended"] = True
                updated.append(f"phase {key} ({phase_name})")
        finally:
            client.close()

    # --- Phase 5 (code_generation): detect from task reports on disk ---
    phases = state.setdefault("phases", {})
    if not phases.get("5", {}).get("ended"):
        tasks_md = change_dir / "tasks.md"
        task_reports_dir = change_dir / "implementation" / "task-reports"
        if tasks_md.exists() and task_reports_dir.exists():
            import re
            content = tasks_md.read_text()
            task_ids = re.findall(r'\d+\.\s+(T\d+_\d+)\s*[—–-]', content)
            if not task_ids:
                task_ids = re.findall(r'- \[[ x]\]\s+\*?\*?(T\d+_\d+)', content)
            if not task_ids:
                task_ids = re.findall(r'\b(T\d+_\d+)\b', content)
                task_ids = list(dict.fromkeys(task_ids))

            if task_ids:
                existing_reports = {f.stem for f in task_reports_dir.glob("*.md")}
                all_done = all(tid in existing_reports for tid in task_ids)

                if "5" not in phases:
                    client = _client()
                    try:
                        phase_id = client.start_phase(run_id, 5, "code_generation")
                        phases["5"] = {"id": phase_id, "name": "code_generation", "ended": False}
                    except Exception:
                        pass
                    finally:
                        client.close()

                if all_done and "5" in phases and not phases["5"].get("ended"):
                    from src.telemetry.tokens import estimate_task_tokens
                    total_in, total_out = 0, 0
                    for tid in task_ids:
                        ti, to = estimate_task_tokens(change_dir, tid)
                        total_in += ti
                        total_out += to

                    client = _client()
                    try:
                        client.end_phase(
                            phases["5"]["id"],
                            status="passed",
                            quality_label=f"{len(task_ids)}/{len(task_ids)} tasks approved",
                            tokens_in=total_in,
                            tokens_out=total_out,
                        )
                        phases["5"]["ended"] = True
                        updated.append("phase 5 (code_generation)")

                        impl_report = change_dir / "implementation-report.md"
                        if impl_report.exists():
                            client.end_run(run_id, status="completed")
                            updated.append("run completed")
                    except Exception:
                        pass
                    finally:
                        client.close()

    _save_state(args.change, state)
    _out({"ok": True, "updated": updated})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="telemetry-auto",
        description="Automatic telemetry hooks for OpenSpec pipeline",
    )
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("on-new", help="Register a new pipeline run")
    r.add_argument("--change", required=True)
    r.add_argument("--jira-key", required=True)
    r.add_argument("--branch", default="")

    sa = sub.add_parser("on-artifact-start", help="Signal artifact creation started")
    sa.add_argument("--change", required=True)
    sa.add_argument("--artifact", required=True)

    ac = sub.add_parser("on-artifact-complete", help="Signal artifact approved/rejected")
    ac.add_argument("--change", required=True)
    ac.add_argument("--artifact", required=True)
    ac.add_argument("--status", required=True, choices=["passed", "failed"])
    ac.add_argument("--score", type=float, default=0)
    ac.add_argument("--label", default="")
    ac.add_argument("--iterations", type=int, default=1)

    ap = sub.add_parser("on-apply-start", help="Signal /opsx-apply task loop started")
    ap.add_argument("--change", required=True)

    ts = sub.add_parser("on-task-start", help="Signal task execution started")
    ts.add_argument("--change", required=True)
    ts.add_argument("--task-id", required=True)
    ts.add_argument("--title", default="")
    ts.add_argument("--agent", default="")

    tc = sub.add_parser("on-task-complete", help="Signal task approved/failed")
    tc.add_argument("--change", required=True)
    tc.add_argument("--task-id", required=True)
    tc.add_argument("--status", required=True, choices=["passed", "failed"])
    tc.add_argument("--loops", type=int, default=0)

    apc = sub.add_parser("on-apply-complete", help="Signal all tasks done, end phase 5 + run")
    apc.add_argument("--change", required=True)
    apc.add_argument("--label", default="")

    sy = sub.add_parser("sync", help="Sync filesystem state to dashboard")
    sy.add_argument("--change", required=True)

    return p


_DISPATCH = {
    "on-new": on_new,
    "on-artifact-start": on_artifact_start,
    "on-artifact-complete": on_artifact_complete,
    "on-apply-start": on_apply_start,
    "on-task-start": on_task_start,
    "on-task-complete": on_task_complete,
    "on-apply-complete": on_apply_complete,
    "sync": sync,
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
            json.dumps({"warning": f"Auto-telemetry unavailable: {exc}"}),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
