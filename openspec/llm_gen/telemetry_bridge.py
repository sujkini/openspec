"""Writes real LLM token usage from direct API calls to
``openspec/changes/<name>/telemetry/llm-usage/<usage_id>.json`` so
``openspec.telemetry.tokens`` can use exact counts instead of a tiktoken
estimate for any artifact generated via ``openspec.llm_gen``.

Called once per ``openspec.llm_gen.run`` invocation (see ``run.py``) — never
by the stage modules themselves, so token accounting stays in one place.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from openspec.llm_gen import context_pack as ctx

USAGE_SUBDIR = Path("telemetry") / "llm-usage"


def usage_path(change: str, usage_id: str) -> Path:
    return ctx.change_dir(change) / USAGE_SUBDIR / f"{usage_id}.json"


def record_usage(
    change: str,
    usage_id: str,
    *,
    tokens_in: int,
    tokens_out: int,
    model: str = "",
    retries: int = 0,
    extra: dict[str, Any] | None = None,
) -> None:
    """Accumulate real token usage for one artifact/task across its lifetime
    (initial generation + any feedback-driven regenerations), so the final
    file reflects the true total cost of producing that artifact."""
    if tokens_in <= 0 and tokens_out <= 0:
        return

    import json

    path = usage_path(change, usage_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    runs = existing.get("runs", [])
    runs.append({"tokens_in": tokens_in, "tokens_out": tokens_out, "model": model, "retries": retries})

    payload = {
        "usage_id": usage_id,
        "source": "openspec.llm_gen",
        "model": model or existing.get("model", ""),
        "tokens_in": sum(r["tokens_in"] for r in runs),
        "tokens_out": sum(r["tokens_out"] for r in runs),
        "run_count": len(runs),
        "runs": runs,
    }
    if extra:
        payload.update(extra)

    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
