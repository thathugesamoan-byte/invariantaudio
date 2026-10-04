# SPDX-License-Identifier: GPL-3.0-or-later
"""
Crash Recovery and Database State Initialization.
"""

import sqlite3

SCHEMA_V6_DDL = """
CREATE TABLE IF NOT EXISTS tracks (
    track_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_path TEXT UNIQUE NOT NULL,
    original_path TEXT,
    sha256 TEXT NOT NULL,
    compressed_audio_sha256 TEXT NOT NULL,
    duration_seconds REAL,
    codec TEXT,
    recording_mbid TEXT,
    release_mbid TEXT,
    verification_status TEXT NOT NULL DEFAULT 'TRUSTED'
);

CREATE TABLE IF NOT EXISTS production_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    source_path TEXT,
    target_path TEXT,
    source_sha256 TEXT,
    source_payload_sha256 TEXT,
    created_utc DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

def init_database(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_V6_DDL)
    conn.execute("PRAGMA user_version = 6;")
    conn.commit()
