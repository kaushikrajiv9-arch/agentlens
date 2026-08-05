"""agentlens CLI — view audit logs and anomaly alerts from the terminal."""
from __future__ import annotations
import click
import json
from .store import EventStore


@click.group()
def main():
    """AgentLens — AI agent audit trail and governance."""
    pass


@main.command()
@click.option("--agent", "-a", default=None, help="Filter by agent_id")
@click.option("--limit", "-n", default=20, show_default=True, help="Number of events")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def logs(agent, limit, as_json):
    """Show recent audit events."""
    store  = EventStore()
    events = store.recent_events(limit=limit, agent_id=agent)
    if not events:
        click.echo("No events found.")
        return
    if as_json:
        click.echo(json.dumps(events, indent=2, default=str))
        return
    click.echo(f"\n{'TS':<26} {'AGENT':<20} {'ACTION':<24} {'STATUS':<8} {'MS':>7}")
    click.echo("─" * 90)
    for e in events:
        ts      = e["ts"][:19].replace("T", " ")
        status  = e["status"]
        color   = "green" if status == "ok" else ("red" if status == "error" else "yellow")
        click.echo(
            f"{ts:<26} {e['agent_id']:<20} {e['action']:<24} "
            + click.style(f"{status:<8}", fg=color)
            + f" {e['latency_ms'] or 0:>7.1f}ms"
        )
    click.echo()


@main.command()
@click.option("--limit", "-n", default=10, show_default=True)
def alerts(limit):
    """Show recent anomaly alerts."""
    store    = EventStore()
    anomalies = store.recent_anomalies(limit=limit)
    if not anomalies:
        click.echo("No anomaly alerts.")
        return
    click.echo(f"\n{'TS':<26} {'AGENT':<20} {'ACTION':<24} {'SEVERITY':<10} REASON")
    click.echo("─" * 100)
    sev_colors = {"critical": "red", "high": "red", "medium": "yellow", "low": "cyan"}
    for a in anomalies:
        ts    = a["ts"][:19].replace("T", " ")
        color = sev_colors.get(a["severity"], "white")
        click.echo(
            f"{ts:<26} {a['agent_id']:<20} {a['action']:<24} "
            + click.style(f"{a['severity']:<10}", fg=color)
            + f" {a['reason']}"
        )
    click.echo()


@main.command()
def stats():
    """Show summary statistics."""
    s = EventStore().stats()
    click.echo("\nAgentLens Stats")
    click.echo("─" * 30)
    click.echo(f"  Total events   : {s['total_events']}")
    click.echo(f"  Errors         : {s['errors']}")
    click.echo(f"  Blocked        : {s['blocked']}")
    click.echo(f"  Anomaly alerts : {s['anomaly_alerts']}")
    click.echo()
