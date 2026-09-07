"""Individual non-agentic stage implementations for openspec.llm_gen.

Each module exposes a ``run(...)`` function returning a small JSON-able dict
with at least an ``ok: bool`` key. None of these modules use tools or grep the
repo — they read only their declared dependency files (see
``openspec.llm_gen.context_pack``) and call the configured LLM API directly.
"""
