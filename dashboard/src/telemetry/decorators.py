from __future__ import annotations

import functools
import time
from typing import Any, Callable

from src.telemetry.client import TelemetryClient


def track_phase(
    client: TelemetryClient,
    run_id: str,
    phase_number: int,
    phase_name: str,
    model_id: str = "",
) -> Callable:
    """Decorator that wraps a function as a tracked pipeline phase.

    The decorated function receives ``phase_id`` as a keyword argument.
    On success, the phase is marked as passed; on exception, as failed.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            phase_id = client.start_phase(run_id, phase_number, phase_name, model_id)
            start = time.time()
            try:
                result = fn(*args, phase_id=phase_id, **kwargs)
                elapsed = time.time() - start
                client.end_phase(phase_id, "passed", duration_s=elapsed)
                return result
            except Exception:
                elapsed = time.time() - start
                client.end_phase(phase_id, "failed", duration_s=elapsed)
                raise

        return wrapper

    return decorator


def track_task(
    client: TelemetryClient,
    run_id: str,
    phase_id: str,
    task_id: str,
    task_title: str = "",
    agent_id: str = "",
) -> Callable:
    """Decorator that wraps a function as a tracked task execution."""

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            task_pk = client.start_task(run_id, phase_id, task_id, task_title, agent_id)
            try:
                result = fn(*args, task_pk=task_pk, **kwargs)
                client.end_task(task_pk, "passed")
                return result
            except Exception:
                client.end_task(task_pk, "failed")
                raise

        return wrapper

    return decorator
