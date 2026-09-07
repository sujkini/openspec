"""Non-agentic specs.md generation (Stage 1 — Specification Analyst).

Invoked as: python -m openspec.llm_gen.run --stage specs --change "<name>"
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from openspec.llm_gen import context_pack as ctx
from openspec.llm_gen.config import load_llm_config
from openspec.llm_gen.provider import LLMError, get_provider
from openspec.validators.specs_structural import validate_specs_structural

ARTIFACT_ID = "specs"


def _build_user_message(cdir: Path) -> str:
    inputs = ctx.read_change_inputs(cdir)
    validation_text, _ = ctx.read_or_not_provided(cdir / "validation.json")

    return "\n".join(
        [
            "jira_ticket:",
            inputs.jira_spec_text or "(no jira-spec.md content found)",
            "",
            "validation.json (Stage 0 gaps — address every missing_element/quality_issue as an "
            "assumption or requirement):",
            validation_text,
            "",
            "instructions:",
            "Generate specs.md exactly per the system schema. No implementation details. "
            "Maximum 3 [NEEDS CLARIFICATION] markers — resolve all other gaps as numbered Assumptions.",
        ]
    )


def run(change: str, *, repo_root: Path | None = None, feedback: str | None = None) -> dict[str, Any]:
    repo_root = repo_root or Path(".")
    cdir = ctx.change_dir(change)
    output_path = cdir / "specs.md"

    system = ctx.read_template("spec-template.md")
    user = _build_user_message(cdir)
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

        gate = validate_specs_structural(cdir)
        if gate["ok"]:
            return {
                "ok": True,
                "artifact": str(output_path),
                "story_count": gate.get("story_count"),
                "retries": attempt - 1,
                "tokens_in": tokens_in_total,
                "tokens_out": tokens_out_total,
                "model": model_used,
            }
        last_error = "; ".join(gate["failures"])
        user += (
            f"\n\n(retry {attempt}: structural gate failed — fix these issues and re-emit the FULL corrected "
            f"specs.md: {last_error})"
        )

    return {
        "ok": False,
        "artifact": str(output_path),
        "reason": last_error or "unknown failure",
        "retries": llm_config.max_retries + 1,
        "tokens_in": tokens_in_total,
        "tokens_out": tokens_out_total,
    }
