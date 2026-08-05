"""
AgentLens dashboard server — zero external dependencies.
Start with: agentlens serve
"""
from __future__ import annotations
import json
import sqlite3
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

from .store import EventStore, DEFAULT_DB


class _API(BaseHTTPRequestHandler):
    store: EventStore  # set by factory

    def log_message(self, *_):
        pass  # suppress default access log

    def _json(self, data, status: int = 200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs     = parse_qs(parsed.query)
        path   = parsed.path.rstrip("/") or "/"

        if path == "/":
            html_file = Path(__file__).parent / "dashboard" / "index.html"
            self._html(html_file.read_bytes())

        elif path == "/api/stats":
            self._json(self.store.stats())

        elif path == "/api/events":
            limit    = int(qs.get("limit", [50])[0])
            agent_id = qs.get("agent", [None])[0]
            run_id   = qs.get("run",   [None])[0]
            self._json(self.store.recent_events(limit=limit, agent_id=agent_id, run_id=run_id))

        elif path == "/api/anomalies":
            limit = int(qs.get("limit", [20])[0])
            self._json(self.store.recent_anomalies(limit=limit))

        elif path == "/api/agents":
            self._json(_agent_summary(self.store))

        elif path == "/api/runs":
            self._json(_run_summary(self.store))

        else:
            self.send_response(404)
            self.end_headers()


def _agent_summary(store: EventStore) -> list:
    with store._conn() as conn:
        rows = conn.execute("""
            SELECT agent_id,
                   COUNT(*)           AS total,
                   SUM(status='error') AS errors,
                   SUM(cost_usd)      AS cost,
                   SUM(token_count)   AS tokens,
                   MAX(ts)            AS last_seen
            FROM events
            GROUP BY agent_id
            ORDER BY total DESC
        """).fetchall()
    return [dict(r) for r in rows]


def _run_summary(store: EventStore) -> list:
    with store._conn() as conn:
        rows = conn.execute("""
            SELECT run_id,
                   COUNT(*)            AS events,
                   SUM(status='error') AS errors,
                   SUM(cost_usd)       AS cost,
                   SUM(token_count)    AS tokens,
                   MIN(ts)             AS started,
                   MAX(ts)             AS ended
            FROM events
            WHERE run_id IS NOT NULL
            GROUP BY run_id
            ORDER BY started DESC
            LIMIT 20
        """).fetchall()
    return [dict(r) for r in rows]


def make_server(host: str, port: int, db_path: Path) -> HTTPServer:
    store = EventStore(db_path)

    class Handler(_API):
        pass
    Handler.store = store

    return HTTPServer((host, port), Handler)


def serve(host: str = "127.0.0.1", port: int = 7755,
          db_path: Optional[Path] = None, open_browser: bool = True):
    db_path = db_path or DEFAULT_DB
    httpd   = make_server(host, port, db_path)
    url     = f"http://{host}:{port}"
    print(f"AgentLens dashboard → {url}")
    print(f"Database            → {db_path}")
    print("Press Ctrl+C to stop.\n")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
