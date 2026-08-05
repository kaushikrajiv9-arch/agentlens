"""SQLite-backed event store. Zero external dependencies."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import List, Optional

DEFAULT_DB = Path.home() / ".agentlens" / "events.db"

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    event_id      TEXT PRIMARY KEY,
    ts            TEXT NOT NULL,
    agent_id      TEXT NOT NULL,
    action        TEXT NOT NULL,
    status        TEXT NOT NULL,
    latency_ms    REAL,
    token_count   INTEGER,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    cost_usd      REAL,
    model         TEXT,
    run_id        TEXT,
    inputs        TEXT,
    outputs       TEXT,
    error         TEXT,
    tags          TEXT
);
"""

_CREATE_AUTH = """
CREATE TABLE IF NOT EXISTS auth_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    agent_id   TEXT NOT NULL,
    action     TEXT NOT NULL,
    allowed    INTEGER NOT NULL,
    policy     TEXT,
    reason     TEXT
);
"""

_CREATE_ANOMALIES = """
CREATE TABLE IF NOT EXISTS anomalies (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    agent_id   TEXT NOT NULL,
    action     TEXT NOT NULL,
    severity   TEXT NOT NULL,
    reason     TEXT
);
"""

_MIGRATE_V2 = [
    "ALTER TABLE events ADD COLUMN input_tokens  INTEGER",
    "ALTER TABLE events ADD COLUMN output_tokens INTEGER",
    "ALTER TABLE events ADD COLUMN cost_usd      REAL",
    "ALTER TABLE events ADD COLUMN model         TEXT",
    "ALTER TABLE events ADD COLUMN run_id        TEXT",
]


class EventStore:
    def __init__(self, db_path: Path = DEFAULT_DB):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = str(db_path)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(_CREATE_EVENTS)
            conn.execute(_CREATE_AUTH)
            conn.execute(_CREATE_ANOMALIES)
            # Run migrations safely (ignore "duplicate column" errors)
            for stmt in _MIGRATE_V2:
                try:
                    conn.execute(stmt)
                except sqlite3.OperationalError:
                    pass

    def save_event(self, e) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO events
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (e.event_id, e.ts, e.agent_id, e.action, e.status,
                 e.latency_ms, e.token_count, e.input_tokens, e.output_tokens,
                 e.cost_usd, e.model, e.run_id,
                 json.dumps(e.inputs, default=str),
                 json.dumps(e.outputs, default=str),
                 e.error, json.dumps(e.tags)),
            )

    def save_auth(self, a) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO auth_log (ts,agent_id,action,allowed,policy,reason) VALUES (?,?,?,?,?,?)",
                (a.ts, a.agent_id, a.action, int(a.allowed), a.policy, a.reason),
            )

    def save_anomaly(self, a) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO anomalies (ts,agent_id,action,severity,reason) VALUES (?,?,?,?,?)",
                (a.ts, a.agent_id, a.action, a.severity, a.reason),
            )

    def recent_events(self, limit: int = 50, agent_id: Optional[str] = None,
                      run_id: Optional[str] = None) -> List[dict]:
        q, params = "SELECT * FROM events", []
        filters = []
        if agent_id:
            filters.append("agent_id = ?"); params.append(agent_id)
        if run_id:
            filters.append("run_id = ?");   params.append(run_id)
        if filters:
            q += " WHERE " + " AND ".join(filters)
        q += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(q, params).fetchall()]

    def recent_anomalies(self, limit: int = 20) -> List[dict]:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM anomalies ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()]

    def stats(self) -> dict:
        with self._conn() as conn:
            total    = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            errors   = conn.execute("SELECT COUNT(*) FROM events WHERE status='error'").fetchone()[0]
            blocked  = conn.execute("SELECT COUNT(*) FROM events WHERE status='blocked'").fetchone()[0]
            alerts   = conn.execute("SELECT COUNT(*) FROM anomalies").fetchone()[0]
            cost_row = conn.execute("SELECT SUM(cost_usd) FROM events").fetchone()[0]
            tok_row  = conn.execute("SELECT SUM(token_count) FROM events").fetchone()[0]
        return {
            "total_events":    total,
            "errors":          errors,
            "blocked":         blocked,
            "anomaly_alerts":  alerts,
            "total_cost_usd":  round(cost_row or 0, 4),
            "total_tokens":    tok_row or 0,
        }

    def export_jsonl(self, path: str, run_id: Optional[str] = None) -> int:
        events = self.recent_events(limit=100_000, run_id=run_id)
        with open(path, "w") as f:
            for e in events:
                f.write(json.dumps(e, default=str) + "\n")
        return len(events)
