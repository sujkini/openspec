from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from src.core.config import AppConfig, load_config

logger = logging.getLogger(__name__)


class TelemetryClient:
    """Lightweight SDK for emitting pipeline telemetry events.

    Reads endpoint and settings from config.json so pipeline hooks
    can emit events without hardcoded URLs.

    Usage::

        t = TelemetryClient()
        run_id = t.create_run("CM-830 - JWT Auth", "CM-830", "feature/auth-v2")
        phase_id = t.start_phase(run_id, 1, "spec_understanding", "gemini-2.5-pro")
        t.log_event(run_id, "API_Agent", "tool_call", "Generated file modification...")
        t.end_phase(phase_id, "passed", tokens_in=45000, tokens_out=12000,
                    quality_score=94, quality_label="AC Completeness: 94/100")
        t.end_run(run_id, "completed")
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path:
            self._cfg: AppConfig = load_config(Path(config_path))
        else:
            self._cfg = load_config()
        self._endpoint = self._cfg.telemetry.endpoint.rstrip("/")
        base = self._endpoint.rsplit("/events", 1)[0]
        self._base = base
        self._client = httpx.Client(timeout=10.0)

    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        resp = self._client.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        resp = self._client.patch(url, json=data)
        resp.raise_for_status()
        return resp.json()

    def create_run(self, change_name: str, jira_key: str, branch: str = "") -> str:
        result = self._post("/runs", {
            "change_name": change_name,
            "jira_key": jira_key,
            "branch": branch,
        })
        return result["id"]

    def end_run(self, run_id: str, status: str = "completed") -> None:
        self._patch(f"/runs/{run_id}", {
            "status": status,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

    def start_phase(
        self,
        run_id: str,
        phase_number: int,
        phase_name: str,
        model_id: str = "",
    ) -> str:
        result = self._post("/phases", {
            "run_id": run_id,
            "phase_number": phase_number,
            "phase_name": phase_name,
            "model_id": model_id,
        })
        return result["id"]

    def end_phase(
        self,
        phase_id: str,
        status: str = "passed",
        *,
        tokens_in: int = 0,
        tokens_out: int = 0,
        quality_score: float = 0,
        quality_label: str = "",
        duration_s: float | None = None,
        iteration_count: int = 1,
    ) -> None:
        data: dict[str, Any] = {
            "status": status,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "quality_score": quality_score,
            "quality_label": quality_label,
            "iteration_count": iteration_count,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        if duration_s is not None:
            data["duration_s"] = duration_s
        self._patch(f"/phases/{phase_id}", data)

    def start_task(
        self,
        run_id: str,
        phase_id: str,
        task_id: str,
        task_title: str = "",
        agent_id: str = "",
    ) -> str:
        result = self._post("/tasks", {
            "run_id": run_id,
            "phase_id": phase_id,
            "task_id": task_id,
            "task_title": task_title,
            "agent_id": agent_id,
        })
        return result["id"]

    def end_task(
        self,
        task_pk: str,
        status: str = "passed",
        *,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0,
        self_correction_loops: int = 0,
    ) -> None:
        self._patch(f"/tasks/{task_pk}", {
            "status": status,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "self_correction_loops": self_correction_loops,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

    def log_event(
        self,
        run_id: str,
        agent_id: str,
        event_type: str,
        message: str,
        *,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        result = self._post("/events", {
            "run_id": run_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "event_type": event_type,
            "message": message,
            "metadata_json": metadata,
        })
        return result["id"]

    def close(self) -> None:
        self._client.close()
