"""Loads openspec/config.yaml credentials.llm and flags.generation_runtime.

Both are read fresh on every invocation (scripts are short-lived processes) —
no caching layer is needed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_RELATIVE_PATH = Path("openspec/config.yaml")

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4.1",
    "vertex": "gemini-2.5-pro",
}

_DEFAULT_GENERATION_RUNTIME = {
    "validation": "script",
    "specs": "script",
    "plan": "script",
    "tasks": "script",
    "stage_eval": "script",
    "code_eval_score": "script",
    "reports": "script",
    "feedback": "script",
}


@dataclass
class LLMConfig:
    provider: str = "anthropic"
    model: str = ""
    judge_model: str = ""
    api_key_env: str = "OPENSPEC_LLM_API_KEY"
    api_key: str = ""
    base_url: str = ""
    project_id: str = ""
    location: str = "us-central1"
    max_output_tokens: int = 8000
    temperature: float = 0.2
    max_retries: int = 2

    def model_for(self, role: str) -> str:
        """``role`` is 'generation' (validation/specs/plan/tasks/feedback) or
        'judge' (stage_eval/code_eval_score/reports)."""
        if role == "judge" and self.judge_model:
            return self.judge_model
        return self.model or self.judge_model or _DEFAULT_MODELS.get(self.provider, "")


def _config_path(repo_root: Path | None) -> Path:
    return (repo_root or Path(".")) / CONFIG_RELATIVE_PATH


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def load_generation_runtime(repo_root: Path | None = None) -> dict[str, str]:
    """Read flags.generation_runtime from config.yaml. Every key defaults to
    'script' — non-agentic execution is the default; set a stage to 'agent' in
    config.yaml to opt that one stage back into the Cursor agent session."""
    cfg = _load_yaml(_config_path(repo_root))
    flags = cfg.get("flags", {}) or {}
    raw = flags.get("generation_runtime", {}) or {}
    resolved = dict(_DEFAULT_GENERATION_RUNTIME)
    for key, value in raw.items():
        if key in resolved and value in ("agent", "script"):
            resolved[key] = value
    return resolved


def is_script_stage(stage: str, repo_root: Path | None = None) -> bool:
    return load_generation_runtime(repo_root).get(stage) == "script"


def load_llm_config(repo_root: Path | None = None) -> LLMConfig:
    cfg = _load_yaml(_config_path(repo_root))
    raw = (cfg.get("credentials", {}) or {}).get("llm", {}) or {}
    api_key_env = raw.get("api_key_env") or "OPENSPEC_LLM_API_KEY"
    temperature_raw = raw.get("temperature")
    max_retries_raw = raw.get("max_retries")
    return LLMConfig(
        provider=(raw.get("provider") or "anthropic").lower(),
        model=raw.get("model") or "",
        judge_model=raw.get("judge_model") or "",
        api_key_env=api_key_env,
        api_key=os.environ.get(api_key_env, ""),
        base_url=raw.get("base_url") or "",
        project_id=raw.get("project_id") or "",
        location=raw.get("location") or "us-central1",
        max_output_tokens=int(raw.get("max_output_tokens") or 8000),
        temperature=float(temperature_raw) if temperature_raw is not None else 0.2,
        max_retries=int(max_retries_raw) if max_retries_raw is not None else 2,
    )
