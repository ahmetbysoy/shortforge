"""SQLite durum deposu: is kayitlari + kota defteri tablolari."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS quota_usage (
    date_pt  TEXT    NOT NULL,
    provider TEXT    NOT NULL,
    units    INTEGER NOT NULL,
    PRIMARY KEY (date_pt, provider)
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id     TEXT PRIMARY KEY,
    topic      TEXT NOT NULL,
    status     TEXT NOT NULL,
    privacy    TEXT NOT NULL DEFAULT 'private',
    script_json TEXT,
    mp4_path   TEXT,
    video_id   TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """Baglanti acar ve semayi idempotent sekilde kurar."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn
