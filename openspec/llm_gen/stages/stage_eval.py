"""Non-agentic stage-eval judge: scoring + refinement (STAGE_EVAL_GATE_PROMPT.md
Steps 2-3), executed as a direct LLM API call instead of inside the Cursor
agent session.

Judges an artifact that ALREADY EXISTS on disk — no tools or repo discovery
needed, which is why this is safe to run non-agentically even for
repo-assessment. However, when scoring fails, only ``plan``/``tasks`` are
auto-refined here (regeneration without new evidence). ``repo-assessment``
refinement always stays agentic (may require re-verifying against the repo) —
this module only *scores* it and reports pass/fail back to the caller.

Invoked as:
    python -m openspec.llm_gen.run --stage stage-eval --change "<name>" --artifact-id plan
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from openspec.llm_gen import context_pack as ctx
from openspec.llm_gen.config import load_llm_config
from openspec.llm_gen.provider import LLMError, extract_json, get_provider

ARTIFACT_EVAL_MAP_PATH = ctx.SCHEMA_ROOT / "stage-gate" / "artifact-eval-map.yaml"
MAX_AUTO_REFINE_PASSES = 2
_AUTO_REFINABLE = {"plan", "tasks"}  # validation/specs have no stage_evals gate today; repo-assessment stays agentic

_JUDGE_SYSTEM_PROMPT = """You are a strict stage-eval scorer for the OpenSpec pipeline.
You are given one artifact and a list of eval cases, each with a prompt, assertions, and a
pass_threshold. Score the artifact against EACH case independently, using ONLY the artifact text
provided. Do not reward content that is not evidenced in the artifact. Do not penalize formatting
choices not covered by an assertion.

Return ONLY a single JSON object of this exact shape:
{
  "cases": [
    {"id": "<case id>", "score": <0-100 integer>, "pass": <bool>, "failures": ["<specific missed assertion, quoting the assertion text>"]}
  ]
}
Every case id from the input MUST appear exactly once in "cases". No prose, no markdown fences.
"""


def _load_artifact_eval_map(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ARTIFACT_EVAL_MAP_PATH
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _resolve_gate(artifact_id: str, repo_root: Path) -> dict[str, Any]:
    mapping = _load_artifact_eval_map(repo_root)
    return (mapping.get("artifacts", {}) or {}).get(artifact_id, {}) or {}


def _score(
    artifact_id: str,
    artifact_text: str,
    cases: list[dict[str, Any]],
    llm_config,
    provider,
) -> tuple[list[dict[str, Any]], int, int]:
    user = (
        f"artifact_id: {artifact_id}\n\n"
        f"artifact:\n{artifact_text}\n\n"
        f"eval_cases (JSON):\n{json.dumps(cases, indent=2)}"
    )
    resp = provider.complete(system=_JUDGE_SYSTEM_PROMPT, user=user, role="judge")
    judged = extract_json(resp.text)
    return judged.get("cases", []), resp.tokens_in, resp.tokens_out


def _write_eval_results(
    eval_results_path: Path,
    *,
    artifact_id: str,
    artifact_path: Path,
    stage_eval_file: str,
    overall_score: int,
    overall_pass: bool,
    cases: list[dict[str, Any]],
    refinement_round: int,
) -> None:
    eval_results_path.parent.mkdir(parents=True, exist_ok=True)
    eval_results_path.write_text(
        yaml.safe_dump(
            {
                "artifact_id": artifact_id,
                "artifact_path": str(artifact_path),
                "stage": artifact_id,
                "stage_eval_file": stage_eval_file,
                "scored_at": datetime.now(timezone.utc).isoformat(),
                "overall_score": overall_score,
                "overall_pass": overall_pass,
                "refinement_round": refinement_round,
                "cases": cases,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def run(change: str, artifact_id: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root or Path(".")
    cdir = ctx.change_dir(change)
    gate = _resolve_gate(artifact_id, repo_root)
    gate_type = gate.get("gate", "skip")

    ext = "json" if artifact_id == "validation" else "md"
    artifact_path = cdir / f"{artifact_id}.{ext}"
    eval_results_path = cdir / "eval-results" / f"{artifact_id}.yaml"

    if not gate or gate_type == "skip":
        return {"ok": True, "skipped": True, "reason": f"gate is '{gate_type or 'undefined'}' — no scoring required"}

    if gate_type == "rubric_only":
        return {
            "ok": True,
            "skipped": True,
            "reason": "rubric_only gate is scored inline during generation (validation stage)",
        }

    stage_eval_file = gate.get("stage_eval_file")
    if not stage_eval_file:
        return {"ok": True, "skipped": True, "reason": "no stage_eval_file configured"}

    eval_path = repo_root / stage_eval_file
    if not eval_path.exists():
        return {
            "ok": True,
            "skipped": True,
            "reason": f"{stage_eval_file} not found — skipping eval scoring",
        }

    eval_data = yaml.safe_load(eval_path.read_text(encoding="utf-8")) or {}
    cases_spec = eval_data.get("evals") or []
    if not cases_spec:
        return {"ok": True, "skipped": True, "reason": "evals list is empty — skipping eval scoring"}

    if not artifact_path.exists():
        return {"ok": False, "reason": f"{artifact_path} not found"}

    llm_config = load_llm_config(repo_root)
    provider = get_provider(llm_config)

    tokens_in_total = 0
    tokens_out_total = 0
    refinement_round = 1
    case_results: list[dict[str, Any]] = []
    overall_score = 0
    overall_pass = False

    for refinement_round in range(1, MAX_AUTO_REFINE_PASSES + 2):
        artifact_text = artifact_path.read_text(encoding="utf-8", errors="replace")
        try:
            case_results, tin, tout = _score(artifact_id, artifact_text, cases_spec, llm_config, provider)
        except LLMError as exc:
            return {"ok": False, "reason": str(exc)}
        tokens_in_total += tin
        tokens_out_total += tout

        scores = [c.get("score", 0) for c in case_results if isinstance(c.get("score"), (int, float))]
        overall_score = round(sum(scores) / len(scores)) if scores else 0
        overall_pass = bool(case_results) and all(c.get("pass") for c in case_results)

        _write_eval_results(
            eval_results_path,
            artifact_id=artifact_id,
            artifact_path=artifact_path,
            stage_eval_file=stage_eval_file,
            overall_score=overall_score,
            overall_pass=overall_pass,
            cases=case_results,
            refinement_round=refinement_round,
        )

        if overall_pass or artifact_id not in _AUTO_REFINABLE:
            break
        if refinement_round > MAX_AUTO_REFINE_PASSES:
            break

        failures_text = "\n".join(
            f"- case {c.get('id')} (score {c.get('score')}): " + "; ".join(c.get("failures", []))
            for c in case_results
            if not c.get("pass")
        )
        refine_result = _refine_artifact(change, artifact_id, failures_text, repo_root=repo_root)
        if not refine_result.get("ok"):
            return {
                "ok": True,
                "artifact": str(artifact_path),
                "eval_results": str(eval_results_path),
                "score": overall_score,
                "pass": overall_pass,
                "refinement_round": refinement_round,
                "refine_failed": refine_result.get("reason"),
                "tokens_in": tokens_in_total,
                "tokens_out": tokens_out_total,
            }
        tokens_in_total += refine_result.get("tokens_in", 0)
        tokens_out_total += refine_result.get("tokens_out", 0)

    return {
        "ok": True,
        "artifact": str(artifact_path),
        "eval_results": str(eval_results_path),
        "score": overall_score,
        "pass": overall_pass,
        "refinement_round": refinement_round,
        "cases_total": len(case_results),
        "cases_pass": sum(1 for c in case_results if c.get("pass")),
        "tokens_in": tokens_in_total,
        "tokens_out": tokens_out_total,
    }


def _refine_artifact(change: str, artifact_id: str, failures_text: str, *, repo_root: Path) -> dict[str, Any]:
    """Regenerate plan/tasks with failed eval cases fed back as feedback — a
    non-agentic repair, never used for repo-assessment (see module docstring)."""
    feedback = f"Stage-eval scoring failed these cases — fix EVERY one, preserve everything else:\n{failures_text}"
    if artifact_id == "plan":
        from openspec.llm_gen.stages import plan as mod

        return mod.run(change, repo_root=repo_root, feedback=feedback)
    if artifact_id == "tasks":
        from openspec.llm_gen.stages import tasks as mod

        return mod.run(change, repo_root=repo_root, feedback=feedback)
    return {"ok": False, "reason": f"artifact '{artifact_id}' has no non-agentic refinement path"}
