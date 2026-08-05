"""Authorization engine — define policies, check actions before agents run them."""
from __future__ import annotations
from typing import Callable, Dict, Optional

from .models import AuthDecision
from .store import EventStore, DEFAULT_DB

_policies: Dict[str, Callable[[str, str], AuthDecision]] = {}
_store: Optional[EventStore] = None


def _get_store() -> EventStore:
    global _store
    if _store is None:
        _store = EventStore()
    return _store


# ── Built-in policy helpers ───────────────────────────────────────────────────

def policy_allow_all(agent_id: str, action: str) -> AuthDecision:
    return AuthDecision(agent_id=agent_id, action=action, allowed=True,
                        policy="allow_all", reason="default allow")


def policy_deny_all(agent_id: str, action: str) -> AuthDecision:
    return AuthDecision(agent_id=agent_id, action=action, allowed=False,
                        policy="deny_all", reason="default deny")


def policy_allowlist(allowed_actions: list[str]):
    """Factory: returns a policy that only permits listed actions."""
    def _policy(agent_id: str, action: str) -> AuthDecision:
        ok = action in allowed_actions
        return AuthDecision(
            agent_id=agent_id, action=action, allowed=ok,
            policy="allowlist",
            reason=f"action {'in' if ok else 'not in'} allowlist {allowed_actions}",
        )
    return _policy


# ── Public API ────────────────────────────────────────────────────────────────

def register_policy(agent_id: str, policy_fn: Callable[[str, str], AuthDecision]) -> None:
    """Attach a policy function to an agent_id."""
    _policies[agent_id] = policy_fn


def allow(agent_id: str, action: str, *, log: bool = True) -> bool:
    """
    Check whether agent_id is permitted to take action.
    Returns True/False and logs the decision.

    Usage:
        if not agentlens.allow("email-agent", "send_external_email"):
            raise PermissionError("Action blocked by AgentLens policy")
    """
    policy_fn = _policies.get(agent_id, policy_allow_all)
    decision = policy_fn(agent_id, action)
    if log:
        _get_store().save_auth(decision)
    return decision.allowed


def require(agent_id: str, action: str) -> None:
    """Like allow() but raises AuthorizationError if blocked."""
    if not allow(agent_id, action):
        raise AuthorizationError(f"[AgentLens] {agent_id} is not authorized to: {action}")


class AuthorizationError(PermissionError):
    pass
