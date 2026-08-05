import pytest
import agentlens
from agentlens.store import EventStore
from pathlib import Path
import tempfile


@pytest.fixture(autouse=True)
def tmp_store(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    yield
    agentlens.configure()  # reset


def test_trace_decorator_logs_event(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    store = EventStore(tmp_path / "test.db")

    @agentlens.trace(agent_id="test-agent", action="greet")
    def greet(name: str) -> str:
        return f"Hello, {name}"

    result = greet("world")
    assert result == "Hello, world"

    events = store.recent_events()
    assert len(events) == 1
    assert events[0]["agent_id"] == "test-agent"
    assert events[0]["action"] == "greet"
    assert events[0]["status"] == "ok"


def test_trace_captures_error(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    store = EventStore(tmp_path / "test.db")

    @agentlens.trace(agent_id="test-agent", action="fail")
    def broken():
        raise ValueError("oops")

    with pytest.raises(ValueError):
        broken()

    events = store.recent_events()
    assert events[0]["status"] == "error"
    assert "oops" in events[0]["error"]


def test_auth_allowlist(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    agentlens.auth.register_policy(
        "agent-a",
        agentlens.auth.policy_allowlist(["read", "summarize"]),
    )
    assert agentlens.auth.allow("agent-a", "read", log=False) is True
    assert agentlens.auth.allow("agent-a", "delete", log=False) is False


def test_shield_detects_alert_action(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    agentlens.shield.configure_agent(
        "agent-b",
        baseline_actions=["read"],
        alert_on=["delete"],
    )
    alert = agentlens.shield.check("agent-b", "delete")
    assert alert is not None
    assert alert.severity == "critical"


def test_shield_clean_action(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    agentlens.shield.configure_agent("agent-c", baseline_actions=["read"])
    alert = agentlens.shield.check("agent-c", "read")
    assert alert is None
