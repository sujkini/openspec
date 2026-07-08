from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from src.core.config import AppConfig, load_config

logger = logging.getLogger(__name__)

CHANGES_DIR = Path("openspec/changes")


class TelemetryClient:
    """Dual-mode telemetry client: writes NDJSON to disk (always) + HTTP (best-effort).

    Disk writes work in any sandbox (Cursor, CI, containers).
    HTTP is attempted as a fast-path but silently skipped on failure.
    """

    def __init__(
        self,
        config_path: str | Path | None = None,
        change: str | None = None,
    ) -> None:
        if config_path:
            self._cfg: AppConfig = load_config(Path(config_path))
        else:
            self._cfg = load_config()
        self._endpoint = self._cfg.telemetry.endpoint.rstrip("/")
        base = self._endpoint.rsplit("/events", 1)[0]
        self._base = base
        self._change = change
        self._http: httpx.Client | None = None

    def _get_http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=10.0)
        return self._http

    def _write_event(self, event: dict[str, Any]) -> None:
        """Append an NDJSON event line to the change's telemetry directory."""
        change = event.get("change") or self._change
        if not change:
            return
        telemetry_dir = CHANGES_DIR / change / "telemetry"
        try:
            telemetry_dir.mkdir(parents=True, exist_ok=True)
            event_line = json.dumps(event, default=str) + "\n"
            with open(telemetry_dir / "events.jsonl", "a") as f:
                f.write(event_line)
        except OSError as exc:
            logger.debug("Failed to write telemetry event to disk: %s", exc)

    def _try_post(self, path: str, data: dict[str, Any]) -> dict[str, Any] | None:
        try:
            resp = self._get_http().post(f"{self._base}{path}", json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def _try_patch(self, path: str, data: dict[str, Any]) -> dict[str, Any] | None:
        try:
            resp = self._get_http().patch(f"{self._base}{path}", json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def create_run(self, change_name: str, jira_key: str, branch: str = "") -> str:
        local_id = str(uuid.uuid4())
        self._write_event({
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "run_create",
            "change": self._change or "",
            "id": local_id,
            "change_name": change_name,
            "jira_key": jira_key,
            "branch": branch,
        })
        result = self._try_post("/runs", {
            "change_name": change_name,
            "jira_key": jira_key,
            "branch": branch,
        })
        if result:
            return result["id"]
        return local_id

    def end_run(self, run_id: str, status: str = "completed") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._write_event({
            "ts": now,
            "type": "run_end",
            "change": self._change or "",
            "run_id": run_id,
            "status": status,
        })
        self._try_patch(f"/runs/{run_id}", {
            "status": status,
            "completed_at": now,
        })

    def start_phase(
        self,
        run_id: str,
        phase_number: int,
        phase_name: str,
        model_id: str = "",
    ) -> str:
        local_id = str(uuid.uuid4())
        self._write_event({
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "phase_start",
            "change": self._change or "",
            "id": local_id,
            "run_id": run_id,
            "phase_number": phase_number,
            "phase_name": phase_name,
            "model_id": model_id,
        })
        result = self._try_post("/phases", {
            "run_id": run_id,
            "phase_number": phase_number,
            "phase_name": phase_name,
            "model_id": model_id,
        })
        if result:
            return result["id"]
        return local_id

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
        now = datetime.now(timezone.utc).isoformat()
        event: dict[str, Any] = {
            "ts": now,
            "type": "phase_end",
            "change": self._change or "",
            "phase_id": phase_id,
            "status": status,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "quality_score": quality_score,
            "quality_label": quality_label,
            "iteration_count": iteration_count,
        }
        if duration_s is not None:
            event["duration_s"] = duration_s
        self._write_event(event)

        data: dict[str, Any] = {
            "status": status,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "quality_score": quality_score,
            "quality_label": quality_label,
            "iteration_count": iteration_count,
            "completed_at": now,
        }
        if duration_s is not None:
            data["duration_s"] = duration_s
        self._try_patch(f"/phases/{phase_id}", data)

    def update_phase(
        self,
        phase_id: str,
        *,
        tokens_in: int = 0,
        tokens_out: int = 0,
        quality_score: float = 0,
        quality_label: str = "",
        iteration_count: int = 1,
        duration_s: float | None = None,
    ) -> None:
        """Push incremental phase metrics without closing the phase."""
        event: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "phase_progress",
            "change": self._change or "",
            "phase_id": phase_id,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "quality_score": quality_score,
            "quality_label": quality_label,
            "iteration_count": iteration_count,
        }
        if duration_s is not None:
            event["duration_s"] = duration_s
        self._write_event(event)

        data: dict[str, Any] = {
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "quality_score": quality_score,
            "quality_label": quality_label,
            "iteration_count": iteration_count,
        }
        if duration_s is not None:
            data["duration_s"] = duration_s
        self._try_patch(f"/phases/{phase_id}", data)

    def start_task(
        self,
        run_id: str,
        phase_id: str,
        task_id: str,
        task_title: str = "",
        agent_id: str = "",
    ) -> str:
        local_id = str(uuid.uuid4())
        self._write_event({
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "task_start",
            "change": self._change or "",
            "id": local_id,
            "run_id": run_id,
            "phase_id": phase_id,
            "task_id": task_id,
            "task_title": task_title,
            "agent_id": agent_id,
        })
        result = self._try_post("/tasks", {
            "run_id": run_id,
            "phase_id": phase_id,
            "task_id": task_id,
            "task_title": task_title,
            "agent_id": agent_id,
        })
        if result:
            return result["id"]
        return local_id

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
        now = datetime.now(timezone.utc).isoformat()
        self._write_event({
            "ts": now,
            "type": "task_end",
            "change": self._change or "",
            "task_pk": task_pk,
            "status": status,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "self_correction_loops": self_correction_loops,
        })
        self._try_patch(f"/tasks/{task_pk}", {
            "status": status,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "self_correction_loops": self_correction_loops,
            "completed_at": now,
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
        local_id = str(uuid.uuid4())
        self._write_event({
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "log_event",
            "change": self._change or "",
            "id": local_id,
            "run_id": run_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "event_type": event_type,
            "message": message,
            "metadata_json": metadata,
        })
        result = self._try_post("/events", {
            "run_id": run_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "event_type": event_type,
            "message": message,
            "metadata_json": metadata,
        })
        if result:
            return result["id"]
        return local_id

    def close(self) -> None:
        if self._http:
            self._http.close()
