"""
AgentLens + Anthropic — full working example.
Requires: pip install agentlens anthropic
Set ANTHROPIC_API_KEY in environment.

Run: python examples/anthropic_example.py
Then: agentlens logs
"""
import os
import agentlens
from agentlens.integrations.anthropic import TracedAnthropic

# One line change from standard Anthropic client
client = TracedAnthropic(
    agent_id="document-summarizer",
    action="summarize",
    tags={"env": "demo"},
)

# Authorization: this agent may only summarize and read
agentlens.auth.register_policy(
    "document-summarizer",
    agentlens.auth.policy_allowlist(["summarize", "read_document"]),
)

# Anomaly shield: alert if it tries to send or delete anything
agentlens.shield.configure_agent(
    agent_id="document-summarizer",
    baseline_actions=["summarize", "read_document"],
    alert_on=["send_email", "delete_file", "external_post"],
)
agentlens.shield.on_alert(
    lambda a: print(f"🚨 ANOMALY [{a.severity.upper()}]: {a.reason}")
)


def summarize_document(text: str) -> str:
    """Summarize a document using Claude — fully traced."""
    if not agentlens.auth.allow("document-summarizer", "summarize"):
        raise PermissionError("Not authorized to summarize")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": f"Summarize in 2 sentences:\n\n{text}"}],
    )
    return response.content[0].text


if __name__ == "__main__":
    # Group two calls under one session run
    with agentlens.Session("demo-run") as session:
        doc1 = "AgentLens is an open-source Python SDK that gives every AI agent an audit trail, authorization engine, and anomaly detection layer. It stores events in SQLite locally with zero configuration required."
        doc2 = "The EU AI Act requires high-risk AI systems to maintain comprehensive audit logs of all automated decisions. Non-compliance fines can reach €30 million or 6% of global annual revenue."

        print("Summarizing doc 1...")
        s1 = summarize_document(doc1)
        print(f"  → {s1}\n")

        print("Summarizing doc 2...")
        s2 = summarize_document(doc2)
        print(f"  → {s2}\n")

    # Show what was logged
    events = session.events()
    total_tokens = sum(e.get("token_count") or 0 for e in events)
    total_cost   = sum(e.get("cost_usd") or 0 for e in events)

    print(f"✅ Session: {session.run_id}")
    print(f"   Events  : {len(events)}")
    print(f"   Tokens  : {total_tokens:,}")
    print(f"   Cost    : ${total_cost:.4f}")
    print(f"\nRun `agentlens logs --run {session.run_id}` to see full audit trail.")
