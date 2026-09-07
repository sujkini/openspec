"""Non-agentic plan.md generation (Planning stage).

Invoked as: python -m openspec.llm_gen.run --stage plan --change "<name>"

Safe to run without tools once specs.md, repo-assessment.md, and
harness-evals/constitution.md already exist as frozen files on disk — no more
repository discovery is required at this point in the pipeline. If
constitution.md is missing, this fails closed rather than guessing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from openspec.llm_gen import context_pack as ctx
from openspec.llm_gen.config import load_llm_config
from openspec.llm_gen.provider import LLMError, get_provider
from openspec.validators.plan_structural import validate_plan_structural

ARTIFACT_ID = "plan"


def _provided(flag: bool) -> str:
    return "PROVIDED" if flag else "NOT_PROVIDED"


def _build_user_message(cdir: Path, repo_root: Path, constitution_text: str) -> str:
    specs_text, _ = ctx.read_or_not_provided(cdir / "specs.md")
    assessment_text, assessment_ok = ctx.read_or_not_provided(cdir / "repo-assessment.md")
    agents_text, agents_ok = ctx.read_agents_md(repo_root)
    validation_text, validation_ok = ctx.read_or_not_provided(cdir / "validation.json")

    return "\n".join(
        [
            "metadata:",
            f'  feature_name: "{cdir.name}"',
            "  inputs:",
            "    constitution: PROVIDED",
            "    validated_specs: PROVIDED",
            f"    repo_assessment: {_provided(assessment_ok)}",
            f"    agents_md: {_provided(agents_ok)}",
            f"    spec_validator_json: {_provided(validation_ok)}",
            "",
            "constitution.md (INPUT — pre-approved; read ALL principles before planning):",
            constitution_text,
            "",
            "validated_specs.md:",
            specs_text,
            "",
            "repo_assessment.md:",
            assessment_text,
            "",
            "agents.md (INPUT — pre-approved; OR NOT_PROVIDED):",
            agents_text,
            "",
            "spec_validator_results.json:",
            validation_text,
            "",
            "instructions:",
            "Generate technical_plan.md content per the system schema. Output ALL sections §0-§8 in "
            "full. 1:1 user story to phase mapping; number of phases equals number of user stories in "
            "specs.md.",
        ]
    )


def run(change: str, *, repo_root: Path | None = None, feedback: str | None = None) -> dict[str, Any]:
    repo_root = repo_root or Path(".")
    cdir = ctx.change_dir(change)
    output_path = cdir / "plan.md"

    constitution_text, constitution_ok = ctx.read_constitution_md(repo_root)
    if not constitution_ok:
        return {
            "ok": False,
            "reason": (
                "constitution.md is required but not found (or is empty) at "
                "harness-evals/constitution.md. Run /opsx-constitute or place it manually."
            ),
        }

    specs_path = cdir / "specs.md"
    if not specs_path.exists() or not specs_path.read_text(encoding="utf-8").strip():
        return {"ok": False, "reason": f"{specs_path} not found — specs.md must be approved before planning"}

    system = ctx.read_template("plan-template.md")
    user = _build_user_message(cdir, repo_root, constitution_text)
    if feedback:
        user += f"\n\nrevision_feedback (address every point; do not regress passing sections):\n{feedback}"

    llm_config = load_llm_config(repo_root)
    provider = get_provider(llm_config)

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
        output_path.write_text(text + "\n", encoding="utf-8")

        gate = validate_plan_structural(cdir)
        if gate["ok"]:
            return {
                "ok": True,
                "artifact": str(output_path),
                "phase_count": gate.get("phase_count"),
                "retries": attempt - 1,
                "tokens_in": tokens_in_total,
                "tokens_out": tokens_out_total,
                "model": model_used,
            }
        last_error = "; ".join(gate["failures"])
        user += (
            f"\n\n(retry {attempt}: structural gate failed — fix these issues and re-emit the FULL corrected "
            f"plan.md: {last_error})"
        )

    return {
        "ok": False,
        "artifact": str(output_path),
        "reason": last_error or "unknown failure",
        "retries": llm_config.max_retries + 1,
        "tokens_in": tokens_in_total,
        "tokens_out": tokens_out_total,
    }
