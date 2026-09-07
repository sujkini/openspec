"""Non-agentic OpenSpec stage execution — direct LLM API calls instead of the
Cursor agent loop.

Invoked by the Cursor agent as a plain tool call, exactly like
``openspec.telemetry.auto`` and ``openspec.validators.tasks_structural``:

    python -m openspec.llm_gen.run --stage validation --change "<name>"

Only stages that do not require repo discovery or tool use are handled here
(validation, specs, plan, tasks, stage-eval scoring, code-eval scoring,
reports, feedback regeneration). ``repo-assessment`` and ``implementation``
are never routed through this package — they stay fully agentic.
"""
