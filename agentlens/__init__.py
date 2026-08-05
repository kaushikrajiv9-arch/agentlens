"""
AgentLens — Audit trail, authorization, and anomaly detection for AI agents.

Quick start:
    import agentlens

    @agentlens.trace(agent_id="my-agent", action="summarize")
    def call_llm(prompt: str) -> str:
        ...

    agentlens.configure_agent("my-agent", baseline_actions=["summarize", "read"])
    agentlens.auth.register_policy("my-agent", agentlens.auth.policy_allowlist(["summarize"]))
"""

from .tracer import trace, log_event, configure
from . import auth
from . import shield
from .store import EventStore

__version__ = "0.1.0"
__all__ = ["trace", "log_event", "configure", "auth", "shield", "EventStore"]
