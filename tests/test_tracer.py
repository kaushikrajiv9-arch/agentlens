import pytest
import agentlens
from agentlens.store import EventStore
from agentlens.costs import calculate_cost
from agentlens.session import Session


@pytest.fixture(autouse=True)
def tmp_store(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    yield
    agentlens.configure()


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


def test_session_groups_events(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    store = EventStore(tmp_path / "test.db")

    @agentlens.trace(agent_id="agent-s", action="step")
    def step(x):
        return x * 2

    with Session("test-pipeline") as session:
        step(1)
        step(2)

    events = store.recent_events(run_id=session.run_id)
    assert len(events) == 2
    assert all(e["run_id"] == session.run_id for e in events)


def test_session_events_method(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))

    @agentlens.trace(agent_id="agent-x", action="work")
    def work():
        return "done"

    with Session("pipeline-x") as session:
        work()

    assert len(session.events()) == 1


def test_auth_allowlist(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    agentlens.auth.register_policy(
        "agent-a", agentlens.auth.policy_allowlist(["read", "summarize"])
    )
    assert agentlens.auth.allow("agent-a", "read",   log=False) is True
    assert agentlens.auth.allow("agent-a", "delete", log=False) is False


def test_shield_detects_alert_action(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    agentlens.shield.configure_agent("agent-b", baseline_actions=["read"], alert_on=["delete"])
    alert = agentlens.shield.check("agent-b", "delete")
    assert alert is not None
    assert alert.severity == "critical"


def test_shield_clean_action(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    agentlens.shield.configure_agent("agent-c", baseline_actions=["read"])
    assert agentlens.shield.check("agent-c", "read") is None


def test_cost_calculation():
    cost = calculate_cost("claude-sonnet-4-6", input_tokens=1000, output_tokens=500)
    assert cost is not None
    assert cost > 0
    # $3/MTok in + $15/MTok out → (0.003 + 0.0075) = $0.0105 ... wait
    # 1000 * 3/1M + 500 * 15/1M = 0.003 + 0.0075 = 0.0105 ... actually
    # 1000/1_000_000 * 3 + 500/1_000_000 * 15 = 0.003 + 0.0075 = 0.0105
    assert abs(cost - 0.0105) < 0.0001


def test_stats_includes_cost(tmp_path):
    agentlens.configure(db_path=str(tmp_path / "test.db"))
    agentlens.log_event("a", "b", cost_usd=0.005, token_count=100,
                        input_tokens=80, output_tokens=20)
    s = EventStore(tmp_path / "test.db").stats()
    assert s["total_cost_usd"] == 0.005
    assert s["total_tokens"] == 100
