"""Direct multi-provider LLM API client for openspec.llm_gen.

This bypasses the Cursor agent loop entirely — it calls the provider's API
directly with the caller's own credentials (billed to the provider account,
not the Cursor/Claude Code subscription). Modeled on
``dashboard/src/services/vertex_ai_service.py`` (already calls Vertex/Gemini
directly and parses a JSON response) but generalized to four providers, each
updated to return real token usage from the API response:

- ``anthropic``        — direct Anthropic API, API-key auth.
- ``openai``            — direct OpenAI API, API-key auth.
- ``vertex``            — Gemini models on Vertex AI, ADC auth (no API key).
- ``anthropic_vertex``  — Claude models on Vertex AI Model Garden, ADC auth
  (no API key) — distinct from both ``anthropic`` (different client/auth) and
  ``vertex`` (different SDK entirely; Gemini's ``vertexai`` package cannot
  serve Claude models).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from openspec.llm_gen.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when the LLM API call fails or the response is unusable.

    Callers implement the fail-closed retry loop (see stage modules) — this
    class never silently swallows a failure into a best-effort result.
    """


@dataclass
class LLMResponse:
    text: str
    tokens_in: int
    tokens_out: int
    model: str


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1 :]
        stripped = text.rstrip()
        if stripped.endswith("```"):
            text = stripped[:-3]
    return text.strip()


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort extraction of a single JSON object from LLM output.

    Handles code-fenced JSON and JSON followed by trailing prose (e.g. the
    validation stage's optional executive-summary bullets). Raises
    ``LLMError`` when no valid JSON object can be found — callers must treat
    this as a failed attempt and retry, never accept partial output.
    """
    candidate = _strip_code_fence(text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    if start == -1:
        raise LLMError("No JSON object found in LLM output")

    depth = 0
    for i in range(start, len(candidate)):
        ch = candidate[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                chunk = candidate[start : i + 1]
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError as exc:
                    raise LLMError(f"Malformed JSON object in LLM output: {exc}") from exc
    raise LLMError("Unbalanced JSON object in LLM output")


class LLMProvider:
    """Dispatches ``complete()`` to the configured provider's SDK."""

    _ADC_PROVIDERS = ("vertex", "anthropic_vertex")

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        if not config.api_key and config.provider not in self._ADC_PROVIDERS:
            raise LLMError(
                f"No API key found in environment variable '{config.api_key_env}'. Set it before "
                "running openspec.llm_gen, or flip flags.generation_runtime.<stage> back to 'agent' "
                "in openspec/config.yaml."
            )
        if config.provider == "anthropic_vertex" and not config.project_id:
            raise LLMError(
                "credentials.llm.project_id is required for provider=anthropic_vertex "
                "(Claude models on Vertex AI authenticate via Application Default Credentials — "
                "run 'gcloud auth application-default login' — but still need a GCP project)."
            )

    def complete(
        self,
        *,
        system: str,
        user: str,
        role: str = "generation",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        model = self.config.model_for(role)
        max_tokens = max_tokens or self.config.max_output_tokens
        temperature = self.config.temperature if temperature is None else temperature

        dispatch = {
            "anthropic": self._complete_anthropic,
            "openai": self._complete_openai,
            "vertex": self._complete_vertex,
            "anthropic_vertex": self._complete_anthropic_vertex,
        }
        fn = dispatch.get(self.config.provider)
        if fn is None:
            raise LLMError(
                f"Unknown LLM provider '{self.config.provider}' "
                "(expected anthropic|openai|vertex|anthropic_vertex)"
            )
        return fn(system=system, user=user, model=model, max_tokens=max_tokens, temperature=temperature)

    def _complete_anthropic(
        self, *, system: str, user: str, model: str, max_tokens: int, temperature: float
    ) -> LLMResponse:
        try:
            import anthropic
        except ImportError as exc:
            raise LLMError(
                "The 'anthropic' package is required for provider=anthropic. "
                "Install it: pip install anthropic (see openspec/llm_gen/requirements.txt)"
            ) from exc

        client = anthropic.Anthropic(api_key=self.config.api_key, base_url=self.config.base_url or None)
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:  # anthropic.APIError and friends
            raise LLMError(f"Anthropic API call failed: {exc}") from exc

        text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
        usage = getattr(resp, "usage", None)
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
        return LLMResponse(text=text, tokens_in=tokens_in, tokens_out=tokens_out, model=model)

    def _complete_openai(
        self, *, system: str, user: str, model: str, max_tokens: int, temperature: float
    ) -> LLMResponse:
        try:
            import openai
        except ImportError as exc:
            raise LLMError(
                "The 'openai' package is required for provider=openai. "
                "Install it: pip install openai (see openspec/llm_gen/requirements.txt)"
            ) from exc

        client = openai.OpenAI(api_key=self.config.api_key, base_url=self.config.base_url or None)
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as exc:  # openai.APIError and friends
            raise LLMError(f"OpenAI API call failed: {exc}") from exc

        text = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
        return LLMResponse(text=text, tokens_in=tokens_in, tokens_out=tokens_out, model=model)

    def _complete_vertex(
        self, *, system: str, user: str, model: str, max_tokens: int, temperature: float
    ) -> LLMResponse:
        try:
            import vertexai
            from vertexai.generative_models import GenerationConfig, GenerativeModel
        except ImportError as exc:
            raise LLMError(
                "The 'google-cloud-aiplatform' package is required for provider=vertex. "
                "Install it: pip install google-cloud-aiplatform (see openspec/llm_gen/requirements.txt)"
            ) from exc

        try:
            vertexai.init(project=self.config.project_id, location=self.config.location)
            gen_model = GenerativeModel(model, system_instruction=system)
            gen_config = GenerationConfig(max_output_tokens=max_tokens, temperature=temperature)
            resp = gen_model.generate_content(user, generation_config=gen_config)
        except Exception as exc:
            raise LLMError(f"Vertex AI call failed: {exc}") from exc

        text = resp.text
        usage = getattr(resp, "usage_metadata", None)
        tokens_in = int(getattr(usage, "prompt_token_count", 0) or 0)
        tokens_out = int(getattr(usage, "candidates_token_count", 0) or 0)
        return LLMResponse(text=text, tokens_in=tokens_in, tokens_out=tokens_out, model=model)

    def _complete_anthropic_vertex(
        self, *, system: str, user: str, model: str, max_tokens: int, temperature: float
    ) -> LLMResponse:
        """Claude models hosted on Vertex AI (Model Garden) — distinct from both
        ``_complete_anthropic`` (direct Anthropic API, api-key auth) and
        ``_complete_vertex`` (Gemini via the ``vertexai`` SDK). Auth is
        Application Default Credentials only (``gcloud auth application-default
        login`` or ``GOOGLE_APPLICATION_CREDENTIALS``) — no API key is used.
        Current-generation Claude models use dateless Vertex model IDs (e.g.
        ``claude-opus-5``, ``claude-sonnet-5``); older models need a dated
        snapshot suffix (e.g. ``claude-3-5-sonnet-v2@20241022``). Set
        ``credentials.llm.model`` / ``judge_model`` explicitly to the exact ID
        enabled in your Vertex Model Garden deployment — there is no safe
        generic default to guess here.
        """
        try:
            from anthropic import AnthropicVertex
        except ImportError as exc:
            raise LLMError(
                "The 'anthropic' package (with Vertex support) is required for "
                "provider=anthropic_vertex. Install it: pip install anthropic "
                "(see openspec/llm_gen/requirements.txt)"
            ) from exc

        if not model:
            raise LLMError(
                "credentials.llm.model (or judge_model) is required for provider=anthropic_vertex — "
                "set it to the exact model ID enabled in your Vertex Model Garden deployment "
                "(e.g. 'claude-opus-5', 'claude-sonnet-5')."
            )

        client = AnthropicVertex(project_id=self.config.project_id, region=self.config.location)
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:  # anthropic.APIError and friends
            raise LLMError(f"Anthropic-on-Vertex API call failed: {exc}") from exc

        text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
        usage = getattr(resp, "usage", None)
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
        return LLMResponse(text=text, tokens_in=tokens_in, tokens_out=tokens_out, model=model)


def get_provider(config: LLMConfig) -> LLMProvider:
    return LLMProvider(config)
