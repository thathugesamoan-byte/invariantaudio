# SPDX-License-Identifier: GPL-3.0-or-later
"""
Transaction journal schema and deterministic recovery.

Filesystem operations and SQLite are two separate systems; this module does not
make them one atomic unit. Instead every mutation is journaled in
``production_transactions`` *before* the filesystem step it describes, and the
only step that changes the media library irreversibly (retiring the source
file) happens strictly after the SQLite commit that records the new track.

States
------
PLANNED     journal row written; no file created yet
STAGED      backup copy and staging copy exist and match the bound source
VERIFIED    tags written in staging; payload and PCM hashes match the source
INSTALLED   staged file hard-linked into the target path (source untouched)
COMMITTED   ``tracks`` row and this state committed in ONE SQLite transaction;
            the source file may still exist (retirement pending)
COMPLETED   source retired (terminal)
ABORTED     failed before the target was installed; staging cleaned (terminal)
ROLLED_BACK failed after install, before commit; installed target removed (terminal)
NEEDS_REVIEW  recovery found a state it will not resolve automatically (terminal;
            a human decides)

Recovery rule: the source file is never removed before COMMITTED, therefore any
transaction not yet COMMITTED is rolled back by removing only files the journal
proves belong to it, and a COMMITTED transaction is rolled forward by retiring
the source only if it still has the journaled SHA-256.
"""

import hashlib
import os
import sqlite3
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 7

SCHEMA_DDL = """
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
    source_pcm_sha256 TEXT,
    staged_sha256 TEXT,
    staging_path TEXT,
    backup_path TEXT,
    verification_status TEXT,
    detail TEXT,
    created_utc DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_utc DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

IN_FLIGHT_STATES = ("PLANNED", "STAGED", "VERIFIED", "INSTALLED", "COMMITTED")
TERMINAL_STATES = ("COMPLETED", "ABORTED", "ROLLED_BACK", "NEEDS_REVIEW")


def init_database(conn: sqlite3.Connection) -> None:
    """Create the schema in an empty database. Refuse any other schema version."""
    version = conn.execute("PRAGMA user_version;").fetchone()[0]
    if version not in (0, SCHEMA_VERSION):
        raise RuntimeError(
            f"UNSUPPORTED_SCHEMA_VERSION: database is v{version}, this release uses v{SCHEMA_VERSION}"
        )
    conn.executescript(SCHEMA_DDL)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
    conn.commit()


def require_schema(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version;").fetchone()[0]
    if version != SCHEMA_VERSION:
        raise RuntimeError(
            f"UNSUPPORTED_SCHEMA_VERSION: database is v{version}, expected v{SCHEMA_VERSION}; run init-db on a new database"
        )


def unresolved_transactions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    marks = ",".join("?" for _ in IN_FLIGHT_STATES)
    cur = conn.execute(
        f"SELECT transaction_id, state, source_path, target_path FROM production_transactions "
        f"WHERE state IN ({marks}) ORDER BY transaction_id",
        IN_FLIGHT_STATES,
    )
    return [
        {"transaction_id": r[0], "state": r[1], "source_path": r[2], "target_path": r[3]}
        for r in cur.fetchall()
    ]


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _is_plain_file(path: Optional[str]) -> bool:
    if not path:
        return False
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISREG(st.st_mode)


def _exists(path: Optional[str]) -> bool:
    return path is not None and os.path.lexists(path)


def _inside(path: str, root: Path) -> bool:
    real_root = os.path.realpath(root)
    real_parent = os.path.realpath(os.path.dirname(path))
    return real_parent == real_root or real_parent.startswith(real_root + os.sep)


def _set_state(conn: sqlite3.Connection, tid: int, state: str, note: str) -> None:
    conn.execute(
        "UPDATE production_transactions SET state = ?, "
        "detail = CASE WHEN detail IS NULL OR detail = '' THEN ? ELSE detail || ' | ' || ? END, "
        "updated_utc = CURRENT_TIMESTAMP WHERE transaction_id = ?",
        (state, note, note, tid),
    )
    conn.commit()


def recover_transaction(conn: sqlite3.Connection, tid: int, staging_root: str | Path) -> str:
    """Deterministically resolve one in-flight transaction. Returns the new state."""
    staging_root = Path(staging_root)
    row = conn.execute(
        "SELECT state, source_path, target_path, source_sha256, staged_sha256, staging_path "
        "FROM production_transactions WHERE transaction_id = ?",
        (tid,),
    ).fetchone()
    if row is None:
        raise KeyError(f"UNKNOWN_TRANSACTION: {tid}")
    state, src, tgt, src_sha, staged_sha, staging = row
    if state not in IN_FLIGHT_STATES:
        return state

    notes: List[str] = []
    review = False

    # The staged file is unlinked only after a successful hard link, so while it
    # still exists it proves whether the target is that link or a foreign file.
    staging_present = _is_plain_file(staging)
    linked_to_staging = False
    if staging_present and _is_plain_file(tgt):
        try:
            linked_to_staging = os.path.samefile(staging, tgt)
        except OSError:
            linked_to_staging = False

    # Staging leftovers: only ever delete a regular file inside the staging root.
    if _exists(staging):
        if _is_plain_file(staging) and _inside(staging, staging_root):
            os.unlink(staging)
            notes.append("staging file removed")
        else:
            review = True
            notes.append("staging path is not a plain file inside the staging root; left in place")

    if state == "COMMITTED":
        if not (_is_plain_file(tgt) and staged_sha and _sha256(tgt) == staged_sha):
            return _finish(conn, tid, "NEEDS_REVIEW", notes + ["committed target missing or changed; source not retired"])
        if not _exists(src):
            notes.append("source already absent")
        elif _is_plain_file(src) and src_sha and _sha256(src) == src_sha:
            os.unlink(src)
            notes.append("source retired")
        else:
            return _finish(conn, tid, "NEEDS_REVIEW", notes + ["source changed since journaling; not retired"])
        return _finish(conn, tid, "COMPLETED", notes)

    # Pre-commit states: the source was never removed, so roll back.
    installed = state in ("VERIFIED", "INSTALLED") and _exists(tgt)
    removed_target = False
    if installed and staging_present and not linked_to_staging:
        notes.append("install never happened; pre-existing target left untouched")
    elif installed:
        ours = linked_to_staging or (_is_plain_file(tgt) and bool(staged_sha) and _sha256(tgt) == staged_sha)
        if not ours:
            review = True
            notes.append("target exists but does not match the journaled staged hash; left in place")
        elif not _is_plain_file(src):
            review = True
            notes.append("source is missing; installed target is the only live copy and was kept")
        else:
            os.unlink(tgt)
            removed_target = True
            notes.append("installed target removed")
    if review:
        return _finish(conn, tid, "NEEDS_REVIEW", notes)
    return _finish(conn, tid, "ROLLED_BACK" if removed_target else "ABORTED", notes or ["nothing to clean"])


def _finish(conn: sqlite3.Connection, tid: int, state: str, notes: List[str]) -> str:
    _set_state(conn, tid, state, "recovery: " + "; ".join(notes))
    return state


def recover_interrupted_transactions(conn: sqlite3.Connection, staging_root: str | Path) -> List[Dict[str, Any]]:
    """Resolve every in-flight transaction. Caller must hold the mutation lock."""
    require_schema(conn)
    results = []
    for t in unresolved_transactions(conn):
        new_state = recover_transaction(conn, t["transaction_id"], staging_root)
        results.append({**t, "previous_state": t["state"], "state": new_state})
    return results
