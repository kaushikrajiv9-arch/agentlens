"""
Drop-in Anthropic wrapper — one line change, full audit trail.

Before:
    from anthropic import Anthropic
    client = Anthropic()

After:
    from agentlens.integrations.anthropic import TracedAnthropic
    client = TracedAnthropic(agent_id="my-agent")

All client.messages.create() calls are automatically traced.
"""
from __future__ import annotations
import time
from typing import Any, Optional


class TracedAnthropic:
    """
    Wraps anthropic.Anthropic and traces every messages.create() call.
    Requires: pip install anthropic
    """

    def __init__(
        self,
        agent_id: str,
        action: str = "llm_call",
        tags: dict | None = None,
        db_path: str | None = None,
        **anthropic_kwargs,
    ):
        try:
            import anthropic as _anthropic
        except ImportError:
            raise ImportError("pip install anthropic")

        self._agent_id = agent_id
        self._action   = action
        self._tags     = tags or {}
        self._client   = _anthropic.Anthropic(**anthropic_kwargs)

        from agentlens.tracer import _get_store, configure
        if db_path:
            configure(db_path)
        self._get_store = _get_store

        # Proxy all other attributes (e.g. client.beta, client.completions)
        self.messages = _TracedMessages(
            self._client.messages, agent_id, action, tags or {}, _get_store
        )

    def __getattr__(self, name: str):
        return getattr(self._client, name)


class _TracedMessages:
    def __init__(self, messages, agent_id, action, tags, get_store):
        self._m         = messages
        self._agent_id  = agent_id
        self._action    = action
        self._tags      = tags
        self._get_store = get_store

    def create(self, **kwargs) -> Any:
        from agentlens.models import TraceEvent
        from agentlens.costs import calculate_cost
        from agentlens.session import current_run_id

        inputs = {
            "model":      kwargs.get("model"),
            "messages":   kwargs.get("messages"),
            "max_tokens": kwargs.get("max_tokens"),
            "system":     kwargs.get("system"),
        }
        t0 = time.perf_counter()
        status, response, error = "ok", None, None
        try:
            response = self._m.create(**kwargs)
            return response
        except Exception as exc:
            status = "error"
            error  = str(exc)
            raise
        finally:
            latency_ms = (time.perf_counter() - t0) * 1000
            model = kwargs.get("model", "")

            input_tokens = output_tokens = token_count = None
            cost_usd = None
            outputs  = None

            if response is not None:
                try:
                    input_tokens  = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    token_count   = input_tokens + output_tokens
                    cost_usd      = calculate_cost(model, input_tokens, output_tokens)
                    outputs = {
                        "content": [b.text for b in response.content if hasattr(b, "text")],
                        "stop_reason": response.stop_reason,
                    }
                except Exception:
                    pass

            event = TraceEvent(
                agent_id=self._agent_id,
                action=self._action,
                inputs=inputs,
                outputs=outputs,
                status=status,
                latency_ms=round(latency_ms, 2),
                token_count=token_count,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                model=model,
                run_id=current_run_id(),
                error=error,
                tags=self._tags,
            )
            self._get_store().save_event(event)

    def __getattr__(self, name: str):
        return getattr(self._m, name)
