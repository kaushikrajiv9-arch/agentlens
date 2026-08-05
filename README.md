# AgentLens

**Audit trail, authorization, and anomaly detection for AI agents.**

Every AI agent your company runs takes actions — reads files, sends emails, calls APIs, moves money. AgentLens makes every action observable, authorized, and auditable. One decorator. Zero infrastructure required to start.

```bash
pip install agentlens
```

---

## Quickstart

```python
import agentlens

@agentlens.trace(agent_id="invoice-agent", action="process_invoice")
def process_invoice(data: dict) -> dict:
    # your LLM call here
    return result
```

That's it. Every call is now logged to `~/.agentlens/events.db`.

```bash
agentlens logs       # view audit trail in terminal
agentlens alerts     # view anomaly alerts
agentlens stats      # summary statistics
```

---

## Three Modules

### 1. Audit Trail (`agentlens.trace`)

Wrap any function. Every call is recorded with timestamp, inputs, outputs, latency, token count, and status.

```python
@agentlens.trace(
    agent_id="email-drafter",
    action="draft_reply",
    tags={"customer_id": "acme-corp"},
)
def draft_reply(thread: str) -> str:
    ...
```

Or log manually without the decorator:

```python
agentlens.log_event(
    agent_id="pipeline-runner",
    action="batch_classify",
    inputs={"docs": 142},
    outputs={"processed": 142},
    latency_ms=4210,
)
```

---

### 2. Authorization Engine (`agentlens.auth`)

Define what each agent is allowed to do. Check before it acts.

```python
# Register a policy
agentlens.auth.register_policy(
    "email-drafter",
    agentlens.auth.policy_allowlist(["draft_reply", "read_thread"]),
)

# Check inline
if not agentlens.auth.allow("email-drafter", "send_external_email"):
    raise PermissionError("Not authorized")

# Or raise automatically
agentlens.auth.require("email-drafter", "send_external_email")  # raises AuthorizationError
```

Built-in policies: `policy_allow_all`, `policy_deny_all`, `policy_allowlist(actions)`. Custom policies are just functions: `(agent_id, action) -> AuthDecision`.

---

### 3. Anomaly Shield (`agentlens.shield`)

Define an agent's normal behavior. Get alerted when it deviates.

```python
agentlens.shield.configure_agent(
    agent_id="email-drafter",
    baseline_actions=["read_thread", "draft_reply"],
    alert_on=["send_external_email", "delete_thread", "forward_all"],
)

# Register an alert handler (Slack, PagerDuty, Discord, etc.)
agentlens.shield.on_alert(lambda a: slack.send(f"🚨 {a.severity}: {a.reason}"))

# Check before the agent acts
agentlens.shield.scan_and_block("email-drafter", "delete_thread")  # raises AnomalyBlockedError
```

---

## CLI Reference

```
agentlens logs [--agent AGENT_ID] [--limit N] [--json]
agentlens alerts [--limit N]
agentlens stats
```

---

## Custom DB Path

```python
agentlens.configure(db_path="/var/log/myapp/agentlens.db")
```

---

## Roadmap

- [ ] Web dashboard (v0.2)
- [ ] EU AI Act compliance PDF export
- [ ] OpenTelemetry exporter
- [ ] Cloud sync (AgentLens Cloud)
- [ ] Slack / PagerDuty / Discord integrations
- [ ] Multi-agent session tracking

---

## License

MIT — see [LICENSE](LICENSE)

---

Built by [AgentLens](https://agentlens.dev) · Questions? hello@agentlens.dev
