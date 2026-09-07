"""Non-agentic validation.json generation (Stage 0 — Spec Understanding).

Invoked as: python -m openspec.llm_gen.run --stage validation --change "<name>"

This is the lowest-risk cut in the rollout plan: validation is already
``rubric_only`` (scored inline during generation, no separate stage-eval
gate) and has no repository dependency — only the Jira ticket text.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openspec.llm_gen import context_pack as ctx
from openspec.llm_gen.config import load_llm_config
from openspec.llm_gen.provider import LLMError, extract_json, get_provider
from openspec.validators.validation_schema import validate_validation_schema

ARTIFACT_ID = "validation"


def _build_user_message(cdir: Path, repo_root: Path) -> str:
    inputs = ctx.read_change_inputs(cdir)
    agents_text, agents_provided = ctx.read_agents_md(repo_root)

    lines = [
        "metadata:",
        f"  ticket_id: {inputs.jira_key or 'null'}",
        "  doc_type: jira",
        "  pass_threshold: 80",
        "  output_mode: json_only",
        "",
        "specification:",
        inputs.jira_spec_text or "(no jira-spec.md content found — treat all elements as missing)",
    ]
    if agents_provided:
        lines += ["", "AGENTS.md (optional — apply its Validation Stage Hints section if present):", agents_text]
    return "\n".join(lines)


def run(change: str, *, repo_root: Path | None = None, feedback: str | None = None) -> dict[str, Any]:
    repo_root = repo_root or Path(".")
    cdir = ctx.change_dir(change)
    output_path = cdir / "validation.json"

    system = ctx.read_template("validation-template.md")
    user = _build_user_message(cdir, repo_root)
    if feedback:
        user += f"\n\nrevision_feedback (address every point; do not regress passing dimensions):\n{feedback}"

    llm_config = load_llm_config(repo_root)
    provider = get_provider(llm_config)

    last_error = ""
    tokens_in_total = 0
    tokens_out_total = 0
    for attempt in range(1, llm_config.max_retries + 2):
        try:
            resp = provider.complete(system=system, user=user, role="generation")
            tokens_in_total += resp.tokens_in
            tokens_out_total += resp.tokens_out
            payload = extract_json(resp.text)
        except LLMError as exc:
            last_error = str(exc)
            user += f"\n\n(retry {attempt}: previous attempt failed — {last_error}. Emit ONLY the corrected JSON object.)"
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        gate = validate_validation_schema(output_path)
        if gate["ok"]:
            results = payload.get("validation_results", {})
            return {
                "ok": True,
                "artifact": str(output_path),
                "score": results.get("overall_score"),
                "status": results.get("overall_status"),
                "retries": attempt - 1,
                "tokens_in": tokens_in_total,
                "tokens_out": tokens_out_total,
                "model": resp.model,
            }
        last_error = "; ".join(gate["failures"])
        user += (
            f"\n\n(retry {attempt}: structural gate failed — fix these issues and re-emit the FULL corrected "
            f"JSON object: {last_error})"
        )

    return {
        "ok": False,
        "artifact": str(output_path),
        "reason": last_error or "unknown failure",
        "retries": llm_config.max_retries + 1,
        "tokens_in": tokens_in_total,
        "tokens_out": tokens_out_total,
    }
