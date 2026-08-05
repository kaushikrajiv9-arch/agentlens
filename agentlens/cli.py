"""agentlens CLI — view audit logs and anomaly alerts from the terminal."""
from __future__ import annotations
import click
import json
from .store import EventStore
from .costs import format_cost


@click.group()
def main():
    """AgentLens — AI agent audit trail and governance."""
    pass


@main.command()
@click.option("--agent",  "-a", default=None, help="Filter by agent_id")
@click.option("--run",    "-r", default=None, help="Filter by run_id")
@click.option("--limit",  "-n", default=20, show_default=True)
@click.option("--json",   "as_json", is_flag=True, help="Output raw JSON")
def logs(agent, run, limit, as_json):
    """Show recent audit events."""
    store  = EventStore()
    events = store.recent_events(limit=limit, agent_id=agent, run_id=run)
    if not events:
        click.echo("No events found.")
        return
    if as_json:
        click.echo(json.dumps(events, indent=2, default=str))
        return
    click.echo(f"\n{'TS':<20} {'AGENT':<18} {'ACTION':<22} {'STATUS':<8} {'TOKENS':>7} {'COST':>10} {'MS':>7}")
    click.echo("─" * 100)
    for e in events:
        ts     = e["ts"][:19].replace("T", " ")
        status = e["status"]
        color  = "green" if status == "ok" else ("red" if status == "error" else "yellow")
        tokens = str(e["token_count"] or "—")
        cost   = format_cost(e.get("cost_usd"))
        click.echo(
            f"{ts:<20} {e['agent_id']:<18} {e['action']:<22} "
            + click.style(f"{status:<8}", fg=color)
            + f" {tokens:>7} {cost:>10} {(e['latency_ms'] or 0):>7.1f}ms"
        )
    click.echo()


@main.command()
@click.option("--limit", "-n", default=10, show_default=True)
def alerts(limit):
    """Show recent anomaly alerts."""
    store     = EventStore()
    anomalies = store.recent_anomalies(limit=limit)
    if not anomalies:
        click.echo("No anomaly alerts.")
        return
    click.echo(f"\n{'TS':<20} {'AGENT':<18} {'ACTION':<22} {'SEVERITY':<10} REASON")
    click.echo("─" * 100)
    sev_colors = {"critical": "red", "high": "red", "medium": "yellow", "low": "cyan"}
    for a in anomalies:
        ts    = a["ts"][:19].replace("T", " ")
        color = sev_colors.get(a["severity"], "white")
        click.echo(
            f"{ts:<20} {a['agent_id']:<18} {a['action']:<22} "
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
    click.echo(f"  Total tokens   : {s['total_tokens']:,}")
    click.echo(f"  Total cost     : {format_cost(s['total_cost_usd'])}")
    click.echo()


@main.command()
@click.option("--port", "-p", default=7755, show_default=True, help="Port to listen on")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--db",   default=None, help="Path to events.db (default: ~/.agentlens/events.db)")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
def serve(port, host, db, no_browser):
    """Start the AgentLens web dashboard."""
    from pathlib import Path
    from .server import serve as _serve
    _serve(host=host, port=port,
           db_path=Path(db) if db else None,
           open_browser=not no_browser)


@main.command()
@click.argument("output", default="agentlens_export.jsonl")
@click.option("--run", "-r", default=None, help="Export a specific run_id only")
def export(output, run):
    """Export audit trail to a JSONL file."""
    n = EventStore().export_jsonl(output, run_id=run)
    click.echo(f"Exported {n} events to {output}")
