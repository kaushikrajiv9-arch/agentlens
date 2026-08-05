"""@agentlens.trace — wraps any function and logs it as an audit event."""
from __future__ import annotations
import functools
import time
from typing import Any, Callable, Optional

from .models import TraceEvent
from .store import EventStore

_store: Optional[EventStore] = None


def _get_store() -> EventStore:
    global _store
    if _store is None:
        _store = EventStore()
    return _store


def configure(db_path: str | None = None) -> None:
    """Call once at startup to set a custom DB path."""
    global _store
    from pathlib import Path
    _store = EventStore(Path(db_path)) if db_path else EventStore()


def trace(
    agent_id: str,
    action: str,
    token_counter: Optional[Callable] = None,
    tags: dict | None = None,
):
    """
    Decorator that records every call as an audit event.

    Usage:
        @agentlens.trace(agent_id="summarizer", action="summarize_doc")
        def summarize(text: str) -> str:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            from .session import current_run_id
            inputs = {"args": args, "kwargs": kwargs}
            t0 = time.perf_counter()
            status, outputs, error = "ok", None, None
            try:
                outputs = fn(*args, **kwargs)
                return outputs
            except Exception as exc:
                status = "error"
                error  = str(exc)
                raise
            finally:
                latency_ms = (time.perf_counter() - t0) * 1000
                tc = token_counter(inputs, outputs) if token_counter and outputs is not None else None
                event = TraceEvent(
                    agent_id=agent_id,
                    action=action,
                    inputs=inputs,
                    outputs=outputs,
                    status=status,
                    latency_ms=round(latency_ms, 2),
                    token_count=tc,
                    run_id=current_run_id(),
                    error=error,
                    tags=tags or {},
                )
                _get_store().save_event(event)
        return wrapper
    return decorator


def log_event(
    agent_id: str,
    action: str,
    inputs: Any = None,
    outputs: Any = None,
    status: str = "ok",
    latency_ms: float = 0.0,
    token_count: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost_usd: float | None = None,
    model: str | None = None,
    run_id: str | None = None,
    tags: dict | None = None,
) -> TraceEvent:
    """Manually log an event without using the decorator."""
    from .session import current_run_id
    event = TraceEvent(
        agent_id=agent_id, action=action, inputs=inputs, outputs=outputs,
        status=status, latency_ms=latency_ms, token_count=token_count,
        input_tokens=input_tokens, output_tokens=output_tokens,
        cost_usd=cost_usd, model=model,
        run_id=run_id or current_run_id(),
        tags=tags or {},
    )
    _get_store().save_event(event)
    return event
