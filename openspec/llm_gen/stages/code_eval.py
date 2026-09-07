"""Non-agentic scoring for the code-generation eval gate
(CODE_GENERATION_EVAL_PROMPT.md Step 3 ONLY).

Verification (``go build``/``go vet``/``make`` targets, Step 2) and test
execution (Step 4) are NEVER handled here — those are real shell commands the
Cursor agent must actually run in the fork working copy (they were never LLM
reasoning to begin with, so there is nothing to offload). The agent passes
their real, already-captured results in via ``--results-file`` so this
script can assemble the single eval-results YAML the workflow expects
(Step 6 schema), scoring only the LLM-judgeable assertions itself.

Invoked as:
    python -m openspec.llm_gen.run --stage code-eval --change "<name>" \\
        --task-id T3_2 --oape-command api-implement --fork-dir /path/to/fork \\
        [--results-file /tmp/verification_and_tests.json]
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from openspec.llm_gen import context_pack as ctx
from openspec.llm_gen.config import load_llm_config
from openspec.llm_gen.provider import LLMError, extract_json, get_provider

CODE_EVAL_FILE = "harness-evals/evals/code-generation_eval.yaml"

_JUDGE_SYSTEM_PROMPT = """You are a strict code-generation eval scorer for the OpenSpec pipeline.
You are given: a task payload, the git diff produced for that task, real verification/test
results (already executed — trust these, do not re-derive pass/fail for assertions they cover),
and a list of eval cases (assertions) filtered to this task's oape_command. Score the diff
against EACH case using ONLY the diff content, task payload, and verification/test results
provided — you do not have repo access beyond the diff.

Return ONLY a single JSON object:
{
  "cases": [
    {"id": "<case id>", "score": <0-100 integer>, "pass": <bool>, "failures": ["<specific miss>"]}
  ]
}
Every case id from the input MUST appear exactly once. No prose, no markdown fences.
"""


def _task_payload(tasks_text: str, task_id: str) -> str:
    m = re.search(
        rf"^###\s+Task\s+{re.escape(task_id)}\s*:.*?(?=^###\s+Task\s+|\Z)",
        tasks_text,
        re.I | re.M | re.S,
    )
    return m.group(0) if m else ""


def _git_diff(fork_dir: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=fork_dir,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return result.stdout
    except (OSError, subprocess.SubprocessError) as exc:
        return f"(git diff failed: {exc})"


def run(
    change: str,
    task_id: str,
    oape_command: str,
    *,
    fork_dir: Path,
    results: dict[str, Any] | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root or Path(".")
    cdir = ctx.change_dir(change)
    eval_path = repo_root / CODE_EVAL_FILE
    results = results or {}
    verification = results.get("verification", {})
    test_execution = results.get("test_execution", {})

    eval_results_path = cdir / "eval-results" / f"code-generation-{task_id}.yaml"

    if not eval_path.exists():
        cases_available = False
        case_results: list[dict[str, Any]] = []
        overall_score = 0
        overall_pass = bool(verification.get("overall_pass", True)) and bool(test_execution.get("overall_pass", True))
        tokens_in, tokens_out = 0, 0
        skip_reason = f"{CODE_EVAL_FILE} not found — skipping eval scoring"
    else:
        eval_data = yaml.safe_load(eval_path.read_text(encoding="utf-8")) or {}
        all_cases = eval_data.get("evals") or []
        cases = [c for c in all_cases if c.get("oape_command") in (oape_command, "any")]
        cases_available = bool(cases)
        skip_reason = "" if cases_available else "no eval cases match this oape_command"

        if not cases_available:
            case_results = []
            overall_score = 0
            overall_pass = bool(verification.get("overall_pass", True)) and bool(test_execution.get("overall_pass", True))
            tokens_in, tokens_out = 0, 0
        else:
            tasks_text = ctx.read_text(cdir / "tasks.md")
            task_payload = _task_payload(tasks_text, task_id)
            diff_text = _git_diff(fork_dir)

            llm_config = load_llm_config(repo_root)
            provider = get_provider(llm_config)

            user = (
                f"task_id: {task_id}\noape_command: {oape_command}\n\n"
                f"task_payload:\n{task_payload or '(not found in tasks.md)'}\n\n"
                f"git_diff:\n{diff_text}\n\n"
                f"verification (real exit codes — trust these):\n{json.dumps(verification, indent=2)}\n\n"
                f"test_execution (real exit codes — trust these):\n{json.dumps(test_execution, indent=2)}\n\n"
                f"eval_cases (JSON):\n{json.dumps(cases, indent=2)}"
            )

            try:
                resp = provider.complete(system=_JUDGE_SYSTEM_PROMPT, user=user, role="judge")
                judged = extract_json(resp.text)
            except LLMError as exc:
                return {"ok": False, "reason": str(exc)}

            case_results = judged.get("cases", [])
            tokens_in, tokens_out = resp.tokens_in, resp.tokens_out
            scores = [c.get("score", 0) for c in case_results if isinstance(c.get("score"), (int, float))]
            overall_score = round(sum(scores) / len(scores)) if scores else 0
            overall_pass = (
                bool(case_results)
                and all(c.get("pass") for c in case_results)
                and bool(verification.get("overall_pass", True))
                and bool(test_execution.get("overall_pass", True))
            )

    eval_results_path.parent.mkdir(parents=True, exist_ok=True)
    eval_results_path.write_text(
        yaml.safe_dump(
            {
                "task_id": task_id,
                "oape_command": oape_command,
                "stage": "code-generation",
                "stage_eval_file": CODE_EVAL_FILE,
                "scored_at": datetime.now(timezone.utc).isoformat(),
                "refinement_rounds": results.get("refinement_rounds", 1),
                "overall_score": overall_score,
                "overall_pass": overall_pass,
                "verification": verification,
                "test_execution": test_execution,
                "cases": case_results,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "skipped_scoring": not cases_available,
        "reason": skip_reason or None,
        "eval_results": str(eval_results_path),
        "score": overall_score,
        "pass": overall_pass,
        "cases_total": len(case_results),
        "cases_pass": sum(1 for c in case_results if c.get("pass")),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }
