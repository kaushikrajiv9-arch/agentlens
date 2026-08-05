from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
import json
import uuid


@dataclass
class TraceEvent:
    agent_id: str
    action: str
    inputs: Any
    outputs: Any
    status: str                  # "ok" | "error" | "blocked"
    latency_ms: float
    token_count: Optional[int]   = None
    error: Optional[str]         = None
    tags: dict                   = field(default_factory=dict)
    event_id: str                = field(default_factory=lambda: str(uuid.uuid4()))
    ts: str                      = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


@dataclass
class AuthDecision:
    agent_id: str
    action: str
    allowed: bool
    policy: str
    reason: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AnomalyAlert:
    agent_id: str
    action: str
    severity: str     # "low" | "medium" | "high" | "critical"
    reason: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
