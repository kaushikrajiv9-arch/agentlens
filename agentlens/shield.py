"""Anomaly Shield — detect when agents take unexpected actions."""
from __future__ import annotations
from typing import Callable, Dict, List, Optional, Set

from .models import AnomalyAlert
from .store import EventStore

_baselines: Dict[str, Set[str]] = {}
_alert_actions: Dict[str, Set[str]] = {}
_handlers: List[Callable[[AnomalyAlert], None]] = []
_store: Optional[EventStore] = None


def _get_store() -> EventStore:
    global _store
    if _store is None:
        _store = EventStore()
    return _store


def configure_agent(
    agent_id: str,
    baseline_actions: list[str],
    alert_on: list[str] | None = None,
) -> None:
    """
    Define what an agent normally does and what should trigger an alert.

    Usage:
        agentlens.configure_agent(
            agent_id="email-drafter",
            baseline_actions=["read_inbox", "draft_reply"],
            alert_on=["send_external", "delete_thread", "forward_all"],
        )
    """
    _baselines[agent_id] = set(baseline_actions)
    _alert_actions[agent_id] = set(alert_on or [])


def on_alert(handler: Callable[[AnomalyAlert], None]) -> None:
    """Register a callback that fires when an anomaly is detected."""
    _handlers.append(handler)


def check(agent_id: str, action: str) -> Optional[AnomalyAlert]:
    """
    Call before an agent takes an action.
    Returns an AnomalyAlert if suspicious, None if clean.

    Usage:
        alert = agentlens.shield.check("email-drafter", "send_external")
        if alert:
            notify_security_team(alert)
    """
    alert_set    = _alert_actions.get(agent_id, set())
    baseline_set = _baselines.get(agent_id, set())

    severity, reason = None, None

    if action in alert_set:
        severity = "critical"
        reason   = f"action '{action}' is on the alert list for agent '{agent_id}'"
    elif baseline_set and action not in baseline_set:
        severity = "medium"
        reason   = f"action '{action}' is outside baseline for agent '{agent_id}'"

    if severity:
        alert = AnomalyAlert(agent_id=agent_id, action=action,
                             severity=severity, reason=reason)
        _get_store().save_anomaly(alert)
        for handler in _handlers:
            try:
                handler(alert)
            except Exception:
                pass
        return alert
    return None


def scan_and_block(agent_id: str, action: str) -> None:
    """Like check() but raises AnomalyBlockedError on critical severity."""
    alert = check(agent_id, action)
    if alert and alert.severity == "critical":
        raise AnomalyBlockedError(
            f"[AgentLens] Blocked {agent_id}::{action} — {alert.reason}"
        )


class AnomalyBlockedError(RuntimeError):
    pass
