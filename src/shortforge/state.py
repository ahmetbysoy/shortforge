"""SQLite durum deposu: is kayitlari + kota defteri tablolari."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS quota_usage (
    date_pt  TEXT    NOT NULL,
    provider TEXT    NOT NULL,
    action   TEXT    NOT NULL DEFAULT 'generic',
    units    INTEGER NOT NULL,
    PRIMARY KEY (date_pt, provider, action)
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


SCHEMA_VERSION = 2


def _migrate(conn: sqlite3.Connection) -> None:
    """P0 on-surum defterini (action kolonu yok) yerinde yeniden kurar.

    Kota defteri uretim verisi tasimaz; en guvenli migrasyon tabloyu yeniden
    olusturmaktir. Veri kaybi bilincli ve loglanir.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(quota_usage)")}
    if columns and "action" not in columns:
        conn.execute("DROP TABLE quota_usage")


def connect(db_path: Path) -> sqlite3.Connection:
    """Baglanti acar ve semayi idempotent sekilde kurar."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _migrate(conn)
    conn.executescript(SCHEMA)
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    return conn
