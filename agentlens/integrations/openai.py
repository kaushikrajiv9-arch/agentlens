"""
Drop-in OpenAI wrapper — one line change, full audit trail.

Before:
    from openai import OpenAI
    client = OpenAI()

After:
    from agentlens.integrations.openai import TracedOpenAI
    client = TracedOpenAI(agent_id="my-agent")
"""
from __future__ import annotations
import time
from typing import Any


class TracedOpenAI:
    """
    Wraps openai.OpenAI and traces every chat.completions.create() call.
    Requires: pip install openai
    """

    def __init__(
        self,
        agent_id: str,
        action: str = "llm_call",
        tags: dict | None = None,
        db_path: str | None = None,
        **openai_kwargs,
    ):
        try:
            import openai as _openai
        except ImportError:
            raise ImportError("pip install openai")

        self._agent_id = agent_id
        self._client   = _openai.OpenAI(**openai_kwargs)

        from agentlens.tracer import _get_store, configure
        if db_path:
            configure(db_path)

        self.chat = _TracedChat(
            self._client.chat, agent_id, action, tags or {}, _get_store
        )

    def __getattr__(self, name: str):
        return getattr(self._client, name)


class _TracedChat:
    def __init__(self, chat, agent_id, action, tags, get_store):
        self._chat      = chat
        self.completions = _TracedCompletions(
            chat.completions, agent_id, action, tags, get_store
        )

    def __getattr__(self, name):
        return getattr(self._chat, name)


class _TracedCompletions:
    def __init__(self, completions, agent_id, action, tags, get_store):
        self._c         = completions
        self._agent_id  = agent_id
        self._action    = action
        self._tags      = tags
        self._get_store = get_store

    def create(self, **kwargs) -> Any:
        from agentlens.models import TraceEvent
        from agentlens.costs import calculate_cost
        from agentlens.session import current_run_id

        inputs = {
            "model":    kwargs.get("model"),
            "messages": kwargs.get("messages"),
        }
        t0 = time.perf_counter()
        status, response, error = "ok", None, None
        try:
            response = self._c.create(**kwargs)
            return response
        except Exception as exc:
            status = "error"
            error  = str(exc)
            raise
        finally:
            latency_ms = (time.perf_counter() - t0) * 1000
            model = kwargs.get("model", "")

            input_tokens = output_tokens = token_count = None
            cost_usd = outputs = None

            if response is not None:
                try:
                    input_tokens  = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    token_count   = input_tokens + output_tokens
                    cost_usd      = calculate_cost(model, input_tokens, output_tokens, provider="openai")
                    outputs = {
                        "content":      response.choices[0].message.content,
                        "finish_reason": response.choices[0].finish_reason,
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

    def __getattr__(self, name):
        return getattr(self._c, name)
