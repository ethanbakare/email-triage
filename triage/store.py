"""Small local SQLite store: run history, sent digests, and per-email metadata.

Raw email bodies are never written here. The metadata (sender, category,
whether it needed action) is what a later "learn your habits" phase will use.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .models import TriagedEmail

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    window_since TEXT NOT NULL,
    window_until TEXT NOT NULL,
    status TEXT NOT NULL,          -- 'ok' or 'failed'
    emails INTEGER,
    error TEXT
);
CREATE TABLE IF NOT EXISTS digests (
    run_id INTEGER PRIMARY KEY REFERENCES runs(id),
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS email_meta (
    email_id TEXT PRIMARY KEY,
    run_id INTEGER REFERENCES runs(id),
    received_at TEXT,
    sender_address TEXT,
    category TEXT,
    needs_action INTEGER,
    urgency TEXT,
    has_unsubscribe INTEGER
);
"""


class Store:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def last_successful_until(self) -> datetime | None:
        row = self.db.execute("SELECT window_until FROM runs WHERE status='ok' ORDER BY id DESC LIMIT 1").fetchone()
        return datetime.fromisoformat(row[0]) if row else None

    def record_run(
        self,
        started_at: datetime,
        since: datetime,
        until: datetime,
        status: str,
        emails: int | None = None,
        error: str | None = None,
        digest: str | None = None,
        triaged: list[TriagedEmail] | None = None,
    ) -> int:
        cur = self.db.execute(
            "INSERT INTO runs (started_at, window_since, window_until, status, emails, error) VALUES (?,?,?,?,?,?)",
            (started_at.isoformat(), since.isoformat(), until.isoformat(), status, emails, error),
        )
        run_id = cur.lastrowid
        if digest is not None:
            self.db.execute("INSERT INTO digests (run_id, text) VALUES (?,?)", (run_id, digest))
        for t in triaged or []:
            self.db.execute(
                "INSERT OR REPLACE INTO email_meta VALUES (?,?,?,?,?,?,?,?)",
                (
                    t.email.id,
                    run_id,
                    t.email.date.isoformat(),
                    t.email.sender_address,
                    t.category,
                    int(t.needs_action),
                    t.urgency,
                    int(t.email.list_unsubscribe),
                ),
            )
        self.db.commit()
        return run_id
