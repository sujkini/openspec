"""Transparent wrapper around the `openspec` CLI that emits dashboard telemetry.

Intercepts `openspec status` and `openspec instructions` calls, runs the real
CLI, parses the JSON output, detects lifecycle transitions (new run, artifact
started/completed, task started/completed, phase completed), and pushes
telemetry to the dashboard backend automatically.

Platform-agnostic: works on Cursor, OpenShell, VS Code, bare terminal, CI/CD.

Usage — drop-in replacement for the real openspec CLI::

    python -m src.telemetry.openspec_wrapper status --change my-change --json
    python -m src.telemetry.openspec_wrapper instructions plan --change my-change --json
    python -m src.telemetry.openspec_wrapper list --json

Or as an imported function::

    from src.telemetry.openspec_wrapper import run_openspec
    output = run_openspec(["status", "--change", "my-change", "--json"])

The wrapper is safe to use even when the dashboard backend is down — all
telemetry calls are wrapped in try/except and failures are logged to stderr.
The real openspec output is always printed to stdout unchanged.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
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


def _telem_warning(action: str, exc: Exception) -> None:
    print(
        json.dumps({"telemetry_warning": f"{action}: {exc}"}),
        file=sys.stderr,
    )


def _find_openspec_bin() -> str:
    """Locate the real openspec binary."""
    path = shutil.which("openspec")
    if path:
        return path
    npm_global = Path.home() / ".npm-global" / "bin" / "openspec"
    if npm_global.exists():
        return str(npm_global)
    raise FileNotFoundError(
        "Cannot find openspec CLI. Install with: npm install -g @fission-ai/openspec"
    )


def run_openspec(args: list[str]) -> tuple[str, int]:
    """Run the real openspec CLI and return (stdout, exit_code)."""
    bin_path = _find_openspec_bin()
    result = subprocess.run(
        [bin_path, *args],
        capture_output=True,
        text=True,
    )
    return result.stdout, result.returncode


def _parse_status_json(raw: str) -> dict[str, Any] | None:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None


def _extract_change_name(args: list[str]) -> str | None:
    for i, arg in enumerate(args):
        if arg == "--change" and i + 1 < len(args):
            return args[i + 1]
    return None


def _extract_artifact_id(args: list[str]) -> str | None:
    """Extract artifact positional arg from `instructions <artifact> --change ...`."""
    for arg in args:
        if not arg.startswith("-") and arg != "instructions" and arg != "apply":
            return arg
    return None


def _ensure_run(change: str, jira_key: str = "") -> dict[str, Any]:
    """Ensure a dashboard run exists for this change."""
    state = _load_state(change)
    if state.get("run_id"):
        return state

    if not jira_key:
        jira_path = CHANGES_DIR / change / "inputs" / "jira.yaml"
        if jira_path.exists():
            import yaml
            jira_data = yaml.safe_load(jira_path.read_text()) or {}
            jira_key = str(jira_data.get("jira_key", change.upper()))
        else:
            jira_key = change.upper()

    client = _client()
    try:
        run_id = client.create_run(
            change_name=f"{jira_key} — {change}",
            jira_key=jira_key,
            branch=f"feature/{change}",
        )
        state = {
            "run_id": run_id,
            "jira_key": jira_key,
            "change": change,
            "phases": {},
            "tasks": {},
        }
        _save_state(change, state)
        logger.info("Created dashboard run %s for change %s", run_id, change)
        return state
    except Exception as exc:
        _telem_warning("create_run", exc)
        return state
    finally:
        client.close()


def _sync_artifact_phases(change: str, status_data: dict[str, Any]) -> None:
    """Detect artifact state changes from `openspec status --json` output and sync."""
    artifacts = status_data.get("artifacts", [])
    if not artifacts:
        return

    state = _ensure_run(change)
    if not state.get("run_id"):
        return

    phases = state.setdefault("phases", {})
    changed = False

    for artifact_info in artifacts:
        artifact_id = artifact_info.get("id", "")
        artifact_status = artifact_info.get("status", "")

        mapping = ARTIFACT_PHASE_MAP.get(artifact_id)
        if not mapping:
            continue

        phase_number, phase_name, is_last = mapping
        key = str(phase_number)

        if artifact_status == "done":
            if key not in phases:
                client = _client()
                try:
                    phase_id = client.start_phase(state["run_id"], phase_number, phase_name)
                    phases[key] = {"id": phase_id, "name": phase_name, "ended": False}
                    changed = True
                except Exception as exc:
                    _telem_warning(f"start_phase({phase_name})", exc)
                    continue
                finally:
                    client.close()

            if is_last and not phases[key].get("ended"):
                tokens_in, tokens_out = _estimate_artifact(change, artifact_id)

                eval_path = CHANGES_DIR / change / "eval-results" / f"{artifact_id}.yaml"
                score = 0.0
                if eval_path.exists():
                    try:
                        import yaml
                        eval_data = yaml.safe_load(eval_path.read_text()) or {}
                        score = float(eval_data.get("overall_score", 0))
                    except Exception:
                        pass

                client = _client()
                try:
                    client.end_phase(
                        phases[key]["id"],
                        status="passed",
                        quality_score=score,
                        quality_label=f"Score: {score}/100" if score else "",
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                    )
                    phases[key]["ended"] = True
                    changed = True

                    client.log_event(
                        run_id=state["run_id"],
                        agent_id="Pipeline",
                        event_type="state_machine",
                        message=f"Phase {phase_number} ({phase_name}) completed — {artifact_id} done, tokens_in={tokens_in}, tokens_out={tokens_out}",
                    )
                except Exception as exc:
                    _telem_warning(f"end_phase({phase_name})", exc)
                finally:
                    client.close()

        elif artifact_status in ("ready", "in-progress"):
            if key not in phases:
                client = _client()
                try:
                    phase_id = client.start_phase(state["run_id"], phase_number, phase_name)
                    phases[key] = {"id": phase_id, "name": phase_name, "ended": False}
                    changed = True
                except Exception as exc:
                    _telem_warning(f"start_phase({phase_name})", exc)
                finally:
                    client.close()

    if changed:
        state["phases"] = phases
        _save_state(change, state)


def _sync_phase5(change: str, status_data: dict[str, Any]) -> None:
    """Detect phase 5 (code_generation) completion from task reports on disk."""
    state = _load_state(change)
    if not state.get("run_id"):
        return

    phases = state.setdefault("phases", {})
    if phases.get("5", {}).get("ended"):
        return

    tasks_md = CHANGES_DIR / change / "tasks.md"
    if not tasks_md.exists():
        return

    task_reports_dir = CHANGES_DIR / change / "implementation" / "task-reports"
    if not task_reports_dir.exists():
        return

    content = tasks_md.read_text()
    import re
    task_ids = re.findall(r'\d+\.\s+(T\d+_\d+)\s*[—–-]', content)
    if not task_ids:
        task_ids = re.findall(r'- \[[ x]\]\s+\*?\*?(T\d+_\d+)', content)
    if not task_ids:
        task_ids = re.findall(r'\b(T\d+_\d+)\b', content)
        task_ids = list(dict.fromkeys(task_ids))
    if not task_ids:
        return

    existing_reports = {f.stem for f in task_reports_dir.glob("*.md")}
    all_done = all(tid in existing_reports for tid in task_ids)

    if not all_done:
        if "5" not in phases:
            client = _client()
            try:
                phase_id = client.start_phase(state["run_id"], 5, "code_generation")
                phases["5"] = {"id": phase_id, "name": "code_generation", "ended": False}
                _save_state(change, state)
            except Exception as exc:
                _telem_warning("start_phase(code_generation)", exc)
            finally:
                client.close()
        return

    from src.telemetry.tokens import estimate_task_tokens
    total_in = 0
    total_out = 0
    for tid in task_ids:
        ti, to = estimate_task_tokens(CHANGES_DIR / change, tid)
        total_in += ti
        total_out += to

    if "5" not in phases:
        client = _client()
        try:
            phase_id = client.start_phase(state["run_id"], 5, "code_generation")
            phases["5"] = {"id": phase_id, "name": "code_generation", "ended": False}
        except Exception as exc:
            _telem_warning("start_phase(code_generation)", exc)
            return
        finally:
            client.close()

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

        client.log_event(
            run_id=state["run_id"],
            agent_id="Pipeline",
            event_type="state_machine",
            message=f"Phase 5 (code_generation) completed — {len(task_ids)} tasks, tokens_in={total_in}, tokens_out={total_out}",
        )

        impl_report = CHANGES_DIR / change / "implementation-report.md"
        if impl_report.exists():
            client.end_run(state["run_id"], status="completed")

    except Exception as exc:
        _telem_warning("end_phase(code_generation)", exc)
    finally:
        client.close()

    _save_state(change, state)


def _on_instructions(change: str, artifact_id: str | None) -> None:
    """When `openspec instructions <artifact>` is called, start the phase."""
    if not artifact_id:
        return

    mapping = ARTIFACT_PHASE_MAP.get(artifact_id)
    if not mapping:
        return

    state = _ensure_run(change)
    if not state.get("run_id"):
        return

    phase_number, phase_name, _ = mapping
    key = str(phase_number)
    phases = state.setdefault("phases", {})

    if key in phases:
        return

    client = _client()
    try:
        phase_id = client.start_phase(state["run_id"], phase_number, phase_name)
        phases[key] = {"id": phase_id, "name": phase_name, "ended": False}
        _save_state(change, state)

        client.log_event(
            run_id=state["run_id"],
            agent_id="Pipeline",
            event_type="state_machine",
            message=f"Phase {phase_number} ({phase_name}) started — creating artifact '{artifact_id}'",
        )
    except Exception as exc:
        _telem_warning(f"start_phase({phase_name})", exc)
    finally:
        client.close()


def main() -> None:
    """Entry point: wraps real openspec CLI with telemetry side-effects."""
    cli_args = sys.argv[1:]

    if not cli_args:
        stdout, code = run_openspec(["--help"])
        print(stdout, end="")
        sys.exit(code)

    stdout, exit_code = run_openspec(cli_args)
    print(stdout, end="")

    if exit_code != 0:
        sys.exit(exit_code)

    command = cli_args[0] if cli_args else ""
    change = _extract_change_name(cli_args)
    has_json = "--json" in cli_args

    try:
        if command == "status" and change and has_json:
            data = _parse_status_json(stdout)
            if data:
                _sync_artifact_phases(change, data)
                _sync_phase5(change, data)

        elif command == "instructions" and change:
            artifact_id = _extract_artifact_id(cli_args[1:])
            _on_instructions(change, artifact_id)

        elif command == "list" and has_json:
            data = _parse_status_json(stdout)
            if data and data.get("changes"):
                for ch in data["changes"]:
                    ch_name = ch.get("name", "")
                    if ch_name:
                        _ensure_run(ch_name)

    except Exception as exc:
        _telem_warning("wrapper_hook", exc)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
