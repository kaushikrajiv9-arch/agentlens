"""
AgentLens v0.2 — Audit trail, authorization, and anomaly detection for AI agents.

Quick start (decorator):
    import agentlens

    @agentlens.trace(agent_id="my-agent", action="summarize")
    def call_llm(prompt: str) -> str:
        ...

Quick start (Anthropic drop-in):
    from agentlens.integrations.anthropic import TracedAnthropic
    client = TracedAnthropic(agent_id="my-agent")
    response = client.messages.create(...)   # auto-traced

Quick start (OpenAI drop-in):
    from agentlens.integrations.openai import TracedOpenAI
    client = TracedOpenAI(agent_id="my-agent")
    response = client.chat.completions.create(...)   # auto-traced

Session grouping:
    with agentlens.Session("my-pipeline") as session:
        step1(...)
        step2(...)
    print(session.run_id)
"""

from .tracer  import trace, log_event, configure
from .session import Session
from . import auth
from . import shield
from .store import EventStore

__version__ = "0.2.0"
__all__ = ["trace", "log_event", "configure", "Session", "auth", "shield", "EventStore"]
