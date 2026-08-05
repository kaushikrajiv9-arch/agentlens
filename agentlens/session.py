"""Session context manager — groups multiple trace events under one run_id."""
from __future__ import annotations
import uuid
from contextvars import ContextVar
from typing import Optional

# Thread/async-safe current run_id
_current_run_id: ContextVar[Optional[str]] = ContextVar("_current_run_id", default=None)


def current_run_id() -> Optional[str]:
    return _current_run_id.get()


class Session:
    """
    Groups all agentlens.trace events fired inside this block under a shared run_id.

    Usage:
        with agentlens.Session("invoice-pipeline") as session:
            extract(doc)      # logged with run_id
            validate(data)    # same run_id
            summarize(data)   # same run_id

        print(session.run_id)   # query all events for this run
    """

    def __init__(self, name: str, run_id: Optional[str] = None):
        self.name   = name
        self.run_id = run_id or f"{name}-{uuid.uuid4().hex[:8]}"
        self._token = None

    def __enter__(self) -> "Session":
        self._token = _current_run_id.set(self.run_id)
        return self

    def __exit__(self, *_) -> None:
        if self._token is not None:
            _current_run_id.reset(self._token)

    def events(self, limit: int = 100):
        from .tracer import _get_store
        return _get_store().recent_events(limit=limit, run_id=self.run_id)
