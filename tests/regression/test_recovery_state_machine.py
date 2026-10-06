# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import sqlite3
from invariantaudio.recovery.recovery_manager import init_database

def test_database_initialization_schema_version_and_tables(tmp_path):
    db_file = tmp_path / "test.sqlite3"
    conn = sqlite3.connect(db_file)
    init_database(conn)

    cur = conn.cursor()
    user_ver = cur.execute("PRAGMA user_version;").fetchone()[0]
    assert user_ver == 7

    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()}
    assert "tracks" in tables
    assert "production_transactions" in tables
    conn.close()


def test_init_is_idempotent_and_refuses_foreign_schema_versions(tmp_path):
    conn = sqlite3.connect(tmp_path / "t.sqlite3")
    init_database(conn)
    init_database(conn)
    conn.execute("PRAGMA user_version = 6")
    with pytest.raises(RuntimeError, match="UNSUPPORTED_SCHEMA_VERSION"):
        init_database(conn)


def test_engine_refuses_uninitialised_database(tmp_path):
    from invariantaudio.transactions.engine import TransactionEngine
    conn = sqlite3.connect(tmp_path / "blank.sqlite3")
    eng = TransactionEngine(conn, tmp_path / "b", tmp_path / "s", tmp_path / "l")
    with pytest.raises(RuntimeError, match="UNSUPPORTED_SCHEMA_VERSION"):
        eng.apply_batch([])
