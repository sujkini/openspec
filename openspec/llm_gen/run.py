"""CLI entrypoint for openspec.llm_gen — non-agentic stage execution.

The Cursor agent invokes this as a plain tool call (same pattern as
``openspec.telemetry.auto`` / ``openspec.validators.tasks_structural``) and
reads back exactly one line of JSON from stdout to decide how to resume.

Usage:
    python -m openspec.llm_gen.run --stage validation --change "<name>"
    python -m openspec.llm_gen.run --stage specs      --change "<name>"
    python -m openspec.llm_gen.run --stage plan       --change "<name>"
    python -m openspec.llm_gen.run --stage tasks      --change "<name>" [--phase N] \\
        [--task-min N --task-max N --task-consolidation-threshold N]
    python -m openspec.llm_gen.run --stage stage-eval --change "<name>" --artifact-id plan
    python -m openspec.llm_gen.run --stage code-eval  --change "<name>" \\
        --task-id T3_2 --oape-command api-implement --fork-dir /path/to/fork [--results-file /tmp/r.json]
    python -m openspec.llm_gen.run --stage report     --change "<name>" --report-id implementation-report
    python -m openspec.llm_gen.run --stage report     --change "<name>" --report-id deviation-observed
    python -m openspec.llm_gen.run --stage report     --change "<name>" --report-id evaluation-report --artifact-id plan
    python -m openspec.llm_gen.run --stage feedback   --change "<name>" --artifact-id plan \\
        (--feedback "..." | --feedback-file /tmp/fb.txt) [--phase N]

Always prints exactly ONE line of JSON to stdout:
    {"ok": bool, "artifact": "<path>"?, "score": n?, "retries": n?, "tokens_in": n?, "tokens_out": n?, "reason": "..."?}

Exits 0 when ok=true, non-zero when ok=false — fail-closed. Never a silent
best-effort accept: the caller (agent or /opsx-continue instructions) must
either retry, escalate that one artifact to the agent, or halt.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def cmd_validation(args: argparse.Namespace) -> dict[str, Any]:
    from openspec.llm_gen.stages import validation

    return validation.run(args.change, repo_root=Path(args.repo_root))


def cmd_specs(args: argparse.Namespace) -> dict[str, Any]:
    from openspec.llm_gen.stages import specs

    return specs.run(args.change, repo_root=Path(args.repo_root))


def cmd_plan(args: argparse.Namespace) -> dict[str, Any]:
    from openspec.llm_gen.stages import plan

    return plan.run(args.change, repo_root=Path(args.repo_root))


def cmd_tasks(args: argparse.Namespace) -> dict[str, Any]:
    from openspec.llm_gen.stages import tasks

    task_sizing = None
    if args.task_min is not None and args.task_max is not None:
        task_sizing = {
            "min": args.task_min,
            "max": args.task_max,
            "consolidation_threshold": args.task_consolidation_threshold or 2,
        }
    return tasks.run(args.change, repo_root=Path(args.repo_root), phase=args.phase, task_sizing=task_sizing)


def cmd_stage_eval(args: argparse.Namespace) -> dict[str, Any]:
    from openspec.llm_gen.stages import stage_eval

    if not args.artifact_id:
        return {"ok": False, "reason": "--artifact-id is required for --stage stage-eval"}
    return stage_eval.run(args.change, args.artifact_id, repo_root=Path(args.repo_root))


def cmd_code_eval(args: argparse.Namespace) -> dict[str, Any]:
    from openspec.llm_gen.stages import code_eval

    if not args.task_id or not args.oape_command or not args.fork_dir:
        return {"ok": False, "reason": "--task-id, --oape-command, and --fork-dir are required for --stage code-eval"}
    results = None
    if args.results_file:
        results = json.loads(Path(args.results_file).read_text(encoding="utf-8"))
    return code_eval.run(
        args.change,
        args.task_id,
        args.oape_command,
        fork_dir=Path(args.fork_dir),
        results=results,
        repo_root=Path(args.repo_root),
    )


def cmd_report(args: argparse.Namespace) -> dict[str, Any]:
    from openspec.llm_gen.stages import report

    if args.report_id == "implementation-report":
        return report.run_implementation_report(args.change, repo_root=Path(args.repo_root))
    if args.report_id == "deviation-observed":
        return report.run_deviation_observed(args.change, repo_root=Path(args.repo_root))
    if args.report_id == "evaluation-report":
        if not args.artifact_id:
            return {"ok": False, "reason": "--artifact-id is required for --report-id evaluation-report"}
        return report.run_evaluation_report(args.change, args.artifact_id, repo_root=Path(args.repo_root))
    return {"ok": False, "reason": f"unknown --report-id '{args.report_id}'"}


def cmd_feedback(args: argparse.Namespace) -> dict[str, Any]:
    from openspec.llm_gen.stages import feedback as feedback_mod

    if not args.artifact_id:
        return {"ok": False, "reason": "--artifact-id is required for --stage feedback"}
    feedback_text = args.feedback or (Path(args.feedback_file).read_text(encoding="utf-8") if args.feedback_file else "")
    if not feedback_text.strip():
        return {"ok": False, "reason": "--feedback or --feedback-file is required for --stage feedback"}
    return feedback_mod.run(
        args.change, args.artifact_id, feedback_text, repo_root=Path(args.repo_root), phase=args.phase
    )


_DISPATCH = {
    "validation": cmd_validation,
    "specs": cmd_specs,
    "plan": cmd_plan,
    "tasks": cmd_tasks,
    "stage-eval": cmd_stage_eval,
    "code-eval": cmd_code_eval,
    "report": cmd_report,
    "feedback": cmd_feedback,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m openspec.llm_gen.run",
        description="Non-agentic OpenSpec stage execution via direct LLM API calls",
    )
    p.add_argument("--stage", required=True, choices=sorted(_DISPATCH.keys()))
    p.add_argument("--change", required=True, help="Change name under openspec/changes/")
    p.add_argument("--repo-root", default=".", help="Operator repo root (for config.yaml, agents.md, harness-evals/)")
    p.add_argument("--phase", type=int, default=None, help="Plan phase number (phase-iterative tasks generation/feedback)")
    p.add_argument("--task-min", type=int, default=None)
    p.add_argument("--task-max", type=int, default=None)
    p.add_argument("--task-consolidation-threshold", type=int, default=None)
    p.add_argument("--artifact-id", default=None, help="Artifact id for stage-eval / report evaluation-report / feedback")
    p.add_argument("--task-id", default=None, help="Task id for code-eval")
    p.add_argument(
        "--oape-command",
        default=None,
        help="Resolved OAPE command for code-eval (api-generate|api-generate-tests|api-implement|manual)",
    )
    p.add_argument("--fork-dir", default=None, help="Fork/working-copy directory for code-eval git diff")
    p.add_argument(
        "--results-file",
        default=None,
        help="Path to a JSON file with real verification/test_execution results for code-eval "
        '(shape: {"verification": {...}, "test_execution": {...}, "refinement_rounds": n})',
    )
    p.add_argument(
        "--report-id",
        default=None,
        choices=["implementation-report", "deviation-observed", "evaluation-report"],
    )
    p.add_argument("--feedback", default=None, help="Feedback text for --stage feedback")
    p.add_argument("--feedback-file", default=None, help="Path to a file containing feedback text for --stage feedback")
    return p


def _usage_id(args: argparse.Namespace) -> str:
    """Maps a CLI invocation to the telemetry/llm-usage/<usage_id>.json file it
    should update — see openspec.llm_gen.telemetry_bridge."""
    if args.stage in ("validation", "specs", "plan", "tasks"):
        return args.stage
    if args.stage == "feedback":
        return args.artifact_id or args.stage
    if args.stage == "stage-eval":
        return f"stage-eval-{args.artifact_id}"
    if args.stage == "code-eval":
        return f"code-eval-{args.task_id}"
    if args.stage == "report":
        suffix = f"-{args.artifact_id}" if args.artifact_id else ""
        return f"report-{args.report_id}{suffix}"
    return args.stage


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handler = _DISPATCH[args.stage]
    try:
        result = handler(args)
    except Exception as exc:  # fail-closed: never crash without a JSON verdict
        result = {"ok": False, "reason": f"unhandled exception: {exc}"}

    tokens_in = result.get("tokens_in", 0) or 0
    tokens_out = result.get("tokens_out", 0) or 0
    if tokens_in or tokens_out:
        from openspec.llm_gen.telemetry_bridge import record_usage

        record_usage(
            args.change,
            _usage_id(args),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=result.get("model", ""),
            retries=result.get("retries", 0) or 0,
        )

    print(json.dumps(result))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
