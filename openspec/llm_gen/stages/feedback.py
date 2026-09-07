"""Non-agentic artifact regeneration on user-rejection feedback
(USER_FEEDBACK_PROMPT.md Steps 3-4) for validation/specs/plan/tasks only.

``repo-assessment`` feedback is NEVER routed here — rejecting it may require
re-verifying against the real repository, which needs tools, so that path
always stays agentic.

Invoked as:
    python -m openspec.llm_gen.run --stage feedback --change "<name>" \\
        --artifact-id plan --feedback-file /tmp/feedback.txt [--phase N]
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_REFINABLE = {"validation", "specs", "plan", "tasks"}


def run(
    change: str,
    artifact_id: str,
    feedback: str,
    *,
    repo_root: Path | None = None,
    phase: int | None = None,
) -> dict[str, Any]:
    if artifact_id not in _REFINABLE:
        return {
            "ok": False,
            "reason": (
                f"artifact '{artifact_id}' feedback must be handled by the agent "
                "(repo discovery / deep reasoning required — never routed through openspec.llm_gen)"
            ),
        }

    if artifact_id == "validation":
        from openspec.llm_gen.stages import validation as mod

        return mod.run(change, repo_root=repo_root, feedback=feedback)
    if artifact_id == "specs":
        from openspec.llm_gen.stages import specs as mod

        return mod.run(change, repo_root=repo_root, feedback=feedback)
    if artifact_id == "plan":
        from openspec.llm_gen.stages import plan as mod

        return mod.run(change, repo_root=repo_root, feedback=feedback)

    from openspec.llm_gen.stages import tasks as mod

    return mod.run(change, repo_root=repo_root, feedback=feedback, phase=phase)
