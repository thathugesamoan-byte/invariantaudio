# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared test helpers."""
import hashlib
import sqlite3
from pathlib import Path


def sha256_of(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class FaultyConnection:
    """Wraps a sqlite3 connection to inject failures at chosen statements."""

    def __init__(self, conn):
        self._conn = conn
        self.fail_on_insert_tracks = False
        self.fail_on_commit_after_insert = False
        self.commit_succeeds_then_raises = False
        self._insert_seen = False

    def execute(self, sql, params=()):
        if "INSERT INTO tracks" in sql:
            if self.fail_on_insert_tracks:
                raise sqlite3.OperationalError("injected INSERT failure")
            self._insert_seen = True
        return self._conn.execute(sql, params)

    def commit(self):
        if self._insert_seen and (self.fail_on_commit_after_insert or self.commit_succeeds_then_raises):
            self._insert_seen = False
            if self.commit_succeeds_then_raises:
                self._conn.commit()
            raise sqlite3.OperationalError("injected COMMIT failure")
        return self._conn.commit()

    def rollback(self):
        self._insert_seen = False
        return self._conn.rollback()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def journal_states(conn):
    return [r[0] for r in conn.execute("SELECT state FROM production_transactions ORDER BY transaction_id")]


def assert_library_untouched(lib, *, source_sha=None):
    """Invariants after any failed/rolled-back transaction."""
    assert lib.src.exists() and sha256_of(lib.src) == (source_sha or lib.src_sha)
    assert not lib.target.exists()
    assert lib.conn.execute("SELECT count(*) FROM tracks").fetchone()[0] == 0
    assert not (lib.staging.exists() and any(lib.staging.iterdir()))
