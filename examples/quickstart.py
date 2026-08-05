"""
AgentLens quickstart — 15 lines to full audit coverage.
Run: python examples/quickstart.py
Then: agentlens logs
"""
import agentlens

# 1. Trace any function — every call is logged automatically
@agentlens.trace(agent_id="demo-agent", action="process_document")
def process_document(doc: str) -> str:
    return f"Summary of: {doc[:40]}..."


# 2. Define what this agent is allowed to do
agentlens.auth.register_policy(
    "demo-agent",
    agentlens.auth.policy_allowlist(["process_document", "read_file"]),
)

# 3. Set its behavioral baseline — alert if it does anything unexpected
agentlens.shield.configure_agent(
    agent_id="demo-agent",
    baseline_actions=["process_document", "read_file"],
    alert_on=["send_email", "delete_file", "external_post"],
)

# 4. Alert handler — hook this to Slack/PagerDuty/Discord in production
agentlens.shield.on_alert(lambda a: print(f"🚨 ALERT [{a.severity}] {a.agent_id}::{a.action} — {a.reason}"))


if __name__ == "__main__":
    # Normal call — logged, authorized, no anomaly
    result = process_document("Q3 earnings report with revenue projections...")
    print(f"✅ Result: {result}")

    # Check authorization manually
    if agentlens.auth.allow("demo-agent", "process_document"):
        print("✅ Action authorized")

    # Trigger an anomaly alert
    alert = agentlens.shield.check("demo-agent", "send_email")
    if alert:
        print(f"🚨 Anomaly detected: {alert.severity} — {alert.reason}")

    # View stats
    stats = agentlens.EventStore().stats()
    print(f"\n📊 Stats: {stats}")
    print("\nRun `agentlens logs` to see the full audit trail.")
