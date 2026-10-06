# SPDX-License-Identifier: GPL-3.0-or-later
import sqlite3

from invariantaudio.recovery.recovery_manager import init_database
from invariantaudio.reporting.audit import verify_master_balance


def _db(tmp_path, paths):
    conn = sqlite3.connect(tmp_path / "c.sqlite3")
    init_database(conn)
    for p in paths:
        conn.execute("INSERT INTO tracks (canonical_path, original_path, sha256, compressed_audio_sha256) VALUES (?,?,?,?)",
                     (str(p), "o", "a", "b"))
    conn.commit()
    return conn


def test_balanced(tmp_path):
    m = tmp_path / "m"
    m.mkdir()
    (m / "a.mp3").write_bytes(b"x")
    r = verify_master_balance(_db(tmp_path, [m / "a.mp3"]), m)
    assert r["is_balanced"] and r["unindexed_files"] == 0 and r["missing_files"] == 0


def test_equal_counts_with_different_paths_is_not_balanced(tmp_path):
    m = tmp_path / "m"
    m.mkdir()
    (m / "on_disk.mp3").write_bytes(b"x")
    r = verify_master_balance(_db(tmp_path, [m / "indexed_but_gone.mp3"]), m)
    assert r["db_tracks"] == r["physical_media_files"] == 1
    assert not r["is_balanced"] and r["unindexed_files"] == 1 and r["missing_files"] == 1
