# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import sqlite3
from invariantaudio.recovery.recovery_manager import init_database

def test_database_initialization_pragmas(tmp_path):
    db_file = tmp_path / "test.sqlite3"
    conn = sqlite3.connect(db_file)
    init_database(conn)

    cur = conn.cursor()
    user_ver = cur.execute("PRAGMA user_version;").fetchone()[0]
    assert user_ver == 6

    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()}
    assert "tracks" in tables
    assert "production_transactions" in tables
    conn.close()
