"""SQLite connection helper for lock registry and ledger."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from quadbalance.paths import default_db_path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS strategy_locks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    locked_at TEXT NOT NULL,
    config_id TEXT NOT NULL,
    run_dir TEXT NOT NULL,
    intended_profile TEXT,
    snapshot_json TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,
    validation_passed INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    symbol TEXT,
    amount REAL,
    shares REAL,
    note TEXT,
    action_kind TEXT,
    effective_date TEXT,
    source TEXT NOT NULL DEFAULT 'user',
    deleted_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ledger_active
    ON ledger_entries(entry_date, id)
    WHERE deleted_at IS NULL;
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    return conn
