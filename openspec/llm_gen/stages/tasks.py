"""Non-agentic tasks.md generation (Task Creation stage) — single-pass mode
only (avoid multi-pass unless output is genuinely truncated, matching the
existing README guidance for the agentic single-shot path this replaces).

Invoked as:
    python -m openspec.llm_gen.run --stage tasks --change "<name>" \\
        [--phase N] [--task-min N --task-max N --task-consolidation-threshold N]
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from openspec.llm_gen import context_pack as ctx
from openspec.llm_gen.config import load_llm_config
from openspec.llm_gen.provider import LLMError, get_provider
from openspec.validators.tasks_structural import validate_tasks_structural

ARTIFACT_ID = "tasks"


def _provided(flag: bool) -> str:
    return "PROVIDED" if flag else "NOT_PROVIDED"


def _build_user_message(
    cdir: Path,
    repo_root: Path,
    constitution_text: str,
    *,
    phase: int | None,
    task_sizing: dict[str, int] | None,
) -> str:
    specs_text, _ = ctx.read_or_not_provided(cdir / "specs.md")
    plan_text, _ = ctx.read_or_not_provided(cdir / "plan.md")
    assessment_text, assessment_ok = ctx.read_or_not_provided(cdir / "repo-assessment.md")
    agents_text, agents_ok = ctx.read_agents_md(repo_root)
    validation_text, validation_ok = ctx.read_or_not_provided(cdir / "validation.json")

    lines = [
        "metadata:",
        f'  feature_name: "{cdir.name}"',
        f'  backlog_id: "{cdir.name}"',
    ]
    if phase is not None:
        lines.append(f"  phase_scope: {phase}")
    if task_sizing:
        lines.append(
            "  task_sizing: {"
            f"min: {task_sizing['min']}, max: {task_sizing['max']}, "
            f"consolidation_threshold: {task_sizing.get('consolidation_threshold', 2)}"
            "}"
        )

    lines += [
        "",
        "inputs:",
        "  constitution_md: PROVIDED",
        "  validated_specs_md: PROVIDED",
        "  technical_plan_md: PROVIDED",
        f"  repo_assessment_md: {_provided(assessment_ok)}",
        f"  agents_md: {_provided(agents_ok)}",
        f"  spec_validator_json: {_provided(validation_ok)}",
        "",
        "constitution.md:",
        constitution_text,
        "",
        "validated_specs.md:",
        specs_text,
        "",
        "technical_plan.md:",
        plan_text,
        "",
        "repo_assessment.md:",
        assessment_text,
        "",
        "agents.md:",
        agents_text,
        "",
        "spec_validator_results.json:",
        validation_text,
    ]

    if phase is not None and phase > 1:
        existing_tasks = ctx.read_text(cdir / "tasks.md")
        if existing_tasks.strip():
            lines += [
                "",
                "existing_tasks.md (prior phases — READ-ONLY context; do NOT re-emit; your output will "
                "be appended below a `---` separator and a new phase header):",
                existing_tasks,
            ]

    lines += [
        "",
        "instructions:",
        "Generate tasks.md / Execution Backlog exactly per the system schema (single-pass mode — "
        "§0 through §5 in one response). Do not write code.",
    ]
    return "\n".join(lines)


def run(
    change: str,
    *,
    repo_root: Path | None = None,
    phase: int | None = None,
    task_sizing: dict[str, int] | None = None,
    feedback: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root or Path(".")
    cdir = ctx.change_dir(change)
    output_path = cdir / "tasks.md"

    plan_path = cdir / "plan.md"
    if not plan_path.exists() or not plan_path.read_text(encoding="utf-8").strip():
        return {"ok": False, "reason": f"{plan_path} not found — plan.md must be approved before task creation"}

    constitution_text, _ = ctx.read_constitution_md(repo_root)

    system = ctx.read_template("tasks-template.md") + "\n\n---\n\n" + ctx.read_template("tasks-modes/single-template.md")
    user = _build_user_message(cdir, repo_root, constitution_text, phase=phase, task_sizing=task_sizing)
    if feedback:
        user += f"\n\nrevision_feedback (address every point; do not regress passing sections):\n{feedback}"

    llm_config = load_llm_config(repo_root)
    provider = get_provider(llm_config)

    append_mode = bool(phase and phase > 1 and output_path.exists() and output_path.read_text(encoding="utf-8").strip())
    prior_text = output_path.read_text(encoding="utf-8") if append_mode else ""

    last_error = ""
    tokens_in_total = 0
    tokens_out_total = 0
    model_used = ""
    for attempt in range(1, llm_config.max_retries + 2):
        try:
            resp = provider.complete(system=system, user=user, role="generation")
        except LLMError as exc:
            last_error = str(exc)
            break

        tokens_in_total += resp.tokens_in
        tokens_out_total += resp.tokens_out
        model_used = resp.model

        text = resp.text.strip()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if append_mode:
            output_path.write_text(prior_text.rstrip() + f"\n\n---\n\n{text}\n", encoding="utf-8")
        else:
            output_path.write_text(text + "\n", encoding="utf-8")

        gate = validate_tasks_structural(cdir, repo_root=repo_root)
        if gate["ok"]:
            return {
                "ok": True,
                "artifact": str(output_path),
                "task_count": gate.get("task_count"),
                "retries": attempt - 1,
                "tokens_in": tokens_in_total,
                "tokens_out": tokens_out_total,
                "model": model_used,
            }
        last_error = "; ".join(gate["failures"])
        user += (
            f"\n\n(retry {attempt}: structural gate failed — fix these issues and re-emit the FULL corrected "
            f"tasks.md section for this phase: {last_error})"
        )

    return {
        "ok": False,
        "artifact": str(output_path),
        "reason": last_error or "unknown failure",
        "retries": llm_config.max_retries + 1,
        "tokens_in": tokens_in_total,
        "tokens_out": tokens_out_total,
    }
