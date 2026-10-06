# SPDX-License-Identifier: GPL-3.0-or-later
"""Failure injection at every transaction boundary, and recovery from hard stops."""
import errno
import os
import sqlite3

import pytest

import invariantaudio.transactions.engine as engine_mod
from helpers import FaultyConnection, assert_library_untouched, journal_states, sha256_of
from invariantaudio.recovery.recovery_manager import recover_interrupted_transactions, unresolved_transactions
from invariantaudio.transactions.engine import TransactionEngine, TransactionError


class Boom(Exception):
    """Ordinary failure: the engine must clean up after itself."""


class Crash(BaseException):
    """Simulates SIGKILL: no handler may run; recovery must cope."""


def fail_after(monkeypatch, obj, name, exc):
    original = getattr(obj, name)

    def wrapper(*a, **k):
        original(*a, **k)
        raise exc

    monkeypatch.setattr(obj, name, wrapper)


def fail_before(monkeypatch, obj, name, exc):
    def wrapper(*a, **k):
        raise exc

    monkeypatch.setattr(obj, name, wrapper)


# --------------------------------------------------------------- happy path
def test_success_leaves_consistent_committed_state(lib):
    res = lib.engine.apply_batch([lib.proposal()])
    assert res[0]["status"] == "COMMITTED" and res[0]["source_retired"] is True
    assert lib.target.exists() and not lib.src.exists()
    assert journal_states(lib.conn) == ["COMPLETED"]
    row = lib.conn.execute("SELECT canonical_path, original_path, sha256 FROM tracks").fetchone()
    assert row == (str(lib.target), str(lib.src), sha256_of(lib.target))
    assert (lib.backup / f"{res[0]['transaction_id']}_{lib.src_sha[:12]}_raw_track.mp3").exists()
    assert not any(lib.staging.iterdir())
    assert unresolved_transactions(lib.conn) == []


# ------------------------------------------------- failures: engine cleans up
@pytest.mark.parametrize(
    "point, expected_state",
    [
        ("before_staging", "ABORTED"),
        ("after_staging", "ABORTED"),
        ("after_metadata", "ABORTED"),
        ("before_install", "ABORTED"),
        ("after_install", "ROLLED_BACK"),
        ("after_installed_journal", "ROLLED_BACK"),
    ],
)
def test_failure_at_each_boundary_restores_library(lib, monkeypatch, point, expected_state):
    e = lib.engine
    if point == "before_staging":
        fail_before(monkeypatch, e, "_backup_and_stage", Boom())
    elif point == "after_staging":
        fail_after(monkeypatch, e, "_backup_and_stage", Boom())
    elif point == "after_metadata":
        fail_after(monkeypatch, e, "_write_metadata", Boom())
    elif point == "before_install":
        fail_before(monkeypatch, e, "_install", Boom())
    elif point == "after_install":
        fail_after(monkeypatch, e, "_install", Boom())
    elif point == "after_installed_journal":
        fail_before(monkeypatch, e, "_commit_track", Boom())
    with pytest.raises(TransactionError):
        e.apply_batch([lib.proposal()])
    assert_library_untouched(lib)
    assert journal_states(lib.conn) == [expected_state]
    assert unresolved_transactions(lib.conn) == []
    backups = list(lib.backup.iterdir()) if lib.backup.exists() else []
    assert all(sha256_of(b) == lib.src_sha for b in backups)
    # The engine is usable again afterwards.
    monkeypatch.undo()
    assert e.apply_batch([lib.proposal()])[0]["status"] == "COMMITTED"


def test_database_insert_failure_never_costs_the_original(lib):
    faulty = FaultyConnection(lib.conn)
    faulty.fail_on_insert_tracks = True
    eng = TransactionEngine(faulty, lib.backup, lib.staging, lib.lock, media_root=lib.media)
    with pytest.raises(TransactionError):
        eng.apply_batch([lib.proposal()])
    assert_library_untouched(lib)
    assert journal_states(lib.conn) == ["ROLLED_BACK"]


def test_database_commit_failure_never_costs_the_original(lib):
    faulty = FaultyConnection(lib.conn)
    faulty.fail_on_commit_after_insert = True
    eng = TransactionEngine(faulty, lib.backup, lib.staging, lib.lock, media_root=lib.media)
    with pytest.raises(TransactionError) as ei:
        eng.apply_batch([lib.proposal()])
    assert ei.value.code == "DATABASE_COMMIT_FAILED"
    assert_library_untouched(lib)
    assert journal_states(lib.conn) == ["ROLLED_BACK"]


def test_commit_that_succeeded_but_reported_failure_is_treated_as_committed(lib):
    faulty = FaultyConnection(lib.conn)
    faulty.commit_succeeds_then_raises = True
    eng = TransactionEngine(faulty, lib.backup, lib.staging, lib.lock, media_root=lib.media)
    res = eng.apply_batch([lib.proposal()])
    assert res[0]["status"] == "COMMITTED"
    assert lib.target.exists() and not lib.src.exists()
    assert lib.conn.execute("SELECT count(*) FROM tracks").fetchone()[0] == 1
    assert journal_states(lib.conn) == ["COMPLETED"]


def test_track_row_and_journal_state_commit_together(lib, monkeypatch):
    """If the journal update inside the commit transaction fails, the track row must not survive."""
    real = lib.conn

    class FailJournalUpdate(FaultyConnection):
        def execute(self, sql, params=()):
            if "SET state = 'COMMITTED'" in sql:
                raise sqlite3.OperationalError("injected")
            return super().execute(sql, params)

    eng = TransactionEngine(FailJournalUpdate(real), lib.backup, lib.staging, lib.lock, media_root=lib.media)
    with pytest.raises(TransactionError):
        eng.apply_batch([lib.proposal()])
    assert_library_untouched(lib)


# ------------------------------------------------ integrity verification gates
def test_payload_hash_mismatch_aborts(lib, monkeypatch):
    real = engine_mod.compute_compressed_audio_payload_sha256
    monkeypatch.setattr(engine_mod, "compute_compressed_audio_payload_sha256",
                        lambda p: "f" * 64 if "staging_" in str(p) else real(p))
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal()])
    assert ei.value.code == "PAYLOAD_MISMATCH"
    assert_library_untouched(lib)
    assert journal_states(lib.conn) == ["ABORTED"]


def test_pcm_hash_mismatch_aborts(lib, monkeypatch):
    real = engine_mod.compute_decoded_pcm_sha256
    monkeypatch.setattr(engine_mod, "compute_decoded_pcm_sha256",
                        lambda p: "e" * 64 if "staging_" in str(p) else real(p))
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal()])
    assert ei.value.code == "PCM_MISMATCH"
    assert_library_untouched(lib)


def test_tag_writer_that_damages_audio_is_caught_by_real_hashes(lib, monkeypatch):
    original = lib.engine._write_metadata

    def damaging(path, tags):
        original(path, tags)
        data = bytearray(path.read_bytes())
        mid = len(data) // 2
        data[mid:mid + 64] = bytes(b ^ 0xFF for b in data[mid:mid + 64])
        path.write_bytes(bytes(data))

    monkeypatch.setattr(lib.engine, "_write_metadata", damaging)
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal()])
    assert ei.value.code in ("PAYLOAD_MISMATCH", "PCM_MISMATCH")
    assert_library_untouched(lib)


# --------------------------------------------------- filesystem boundary
def test_cross_filesystem_staging_is_refused_before_anything_is_created(lib, monkeypatch):
    real = engine_mod._device
    monkeypatch.setattr(engine_mod, "_device", lambda p: 1 if str(lib.staging) in str(p) else real(p))
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal()])
    assert ei.value.code == "CROSS_FILESYSTEM_STAGING"
    assert journal_states(lib.conn) == []
    assert not lib.backup.exists()
    assert lib.src.exists()


def test_exdev_at_install_is_rolled_back(lib, monkeypatch):
    def exdev(a, b, **k):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(engine_mod.os, "link", exdev)
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal()])
    assert ei.value.code == "CROSS_FILESYSTEM_STAGING"
    assert_library_untouched(lib)
    assert journal_states(lib.conn) == ["ABORTED"]


@pytest.mark.skipif(
    not os.path.isdir("/dev/shm") or os.stat("/dev/shm").st_dev == os.stat("/tmp").st_dev,
    reason="/dev/shm is not a distinct filesystem on this host (the simulated cross-device tests above still run)",
)
def test_real_distinct_filesystem_staging_is_refused(lib):
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(dir="/dev/shm") as shm:
        eng = TransactionEngine(lib.conn, lib.backup, Path(shm) / "stg", lib.lock, media_root=lib.media)
        with pytest.raises(TransactionError) as ei:
            eng.apply_batch([lib.proposal()])
        assert ei.value.code == "CROSS_FILESYSTEM_STAGING"
    assert lib.src.exists() and not lib.target.exists()


# ------------------------------------------------ input validation (mutation API)
@pytest.mark.parametrize("name", ["track.flac", "track.wav", "track.ogg", "track", "track.aac"])
def test_unsupported_media_extension_is_rejected(lib, name):
    bad = lib.media / name
    bad.write_bytes(b"not really audio")
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal(src=bad, tgt=lib.media / "out" / name)])
    assert ei.value.code == "UNSUPPORTED_MEDIA_EXTENSION"
    assert bad.read_bytes() == b"not really audio"
    assert journal_states(lib.conn) == []


def test_extension_change_is_rejected(lib):
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal(tgt=lib.media / "x.m4a")])
    assert ei.value.code == "UNSUPPORTED_MEDIA_EXTENSION"


def test_unknown_tag_is_rejected_instead_of_silently_dropped(lib):
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal(tags={"genre": "x"})])
    assert ei.value.code == "UNSUPPORTED_TAG"


def test_symlink_source_is_rejected(lib):
    link = lib.media / "link.mp3"
    link.symlink_to(lib.src)
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal(src=link, tgt=lib.media / "o.mp3")])
    assert ei.value.code == "SOURCE_REJECTED"
    assert lib.src.exists() and journal_states(lib.conn) == []


def test_corrupt_source_is_refused(lib):
    from pathlib import Path
    bad = lib.media / "bad.mp3"
    bad.write_bytes((Path(__file__).parent.parent / "fixtures" / "corrupt_header.mp3").read_bytes())
    with pytest.raises(TransactionError):
        lib.engine.apply_batch([lib.proposal(src=bad, tgt=lib.media / "o.mp3")])
    assert bad.exists() and not (lib.media / "o.mp3").exists()


def test_m4a_tags_roundtrip_and_payload_preserved(lib):
    from pathlib import Path
    from mutagen.mp4 import MP4
    from invariantaudio.integrity.audio_integrity import compute_compressed_audio_payload_sha256 as payload
    m4a = lib.media / "t.m4a"
    m4a.write_bytes((Path(__file__).parent.parent / "fixtures" / "synthetic_test_track.m4a").read_bytes())
    pre = payload(m4a)
    tgt = lib.media / "A" / "t.m4a"
    lib.engine.apply_batch([lib.proposal(src=m4a, tgt=tgt, tags={"title": "T", "year": "1999", "track_number": "3/12"})])
    tags = MP4(tgt)
    assert tags["\xa9nam"] == ["T"] and tags["\xa9day"] == ["1999"] and tags["trkn"] == [(3, 12)]
    assert payload(tgt) == pre


# -------------------------------------------------------- hard-stop recovery
CRASH_POINTS = [
    ("after_staging", "_backup_and_stage", "PLANNED", "ABORTED"),
    ("after_metadata", "_write_metadata", "STAGED", "ABORTED"),
    ("after_install", "_install", "VERIFIED", "ROLLED_BACK"),
    ("before_commit", "_commit_track", "INSTALLED", "ROLLED_BACK"),
]


@pytest.mark.parametrize("point, method, crashed_state, recovered_state", CRASH_POINTS)
def test_recovery_rolls_back_hard_stop_before_commit(lib, monkeypatch, point, method, crashed_state, recovered_state):
    if point == "before_commit":
        fail_before(monkeypatch, lib.engine, method, Crash())
    else:
        fail_after(monkeypatch, lib.engine, method, Crash())
    with pytest.raises(Crash):
        lib.engine.apply_batch([lib.proposal()])
    monkeypatch.undo()
    assert journal_states(lib.conn) == [crashed_state]

    # New work is refused until the interrupted transaction is resolved.
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal()])
    assert ei.value.code == "UNRESOLVED_TRANSACTIONS"

    out = lib.engine.recover()
    assert [r["state"] for r in out] == [recovered_state]
    assert_library_untouched(lib)
    assert lib.engine.recover() == []  # idempotent
    assert lib.engine.apply_batch([lib.proposal()])[0]["status"] == "COMMITTED"


def test_recovery_after_link_before_staging_unlink(lib, monkeypatch):
    """Hard stop between os.link and the staging unlink: target and staging are one inode."""
    real_link = os.link

    def link_then_crash(a, b, **k):
        real_link(a, b, **k)
        raise Crash()

    monkeypatch.setattr(engine_mod.os, "link", link_then_crash)
    with pytest.raises(Crash):
        lib.engine.apply_batch([lib.proposal()])
    monkeypatch.undo()
    assert lib.target.exists() and any(lib.staging.iterdir())
    assert [r["state"] for r in lib.engine.recover()] == ["ROLLED_BACK"]
    assert_library_untouched(lib)


def test_recovery_rolls_forward_hard_stop_after_commit(lib, monkeypatch):
    fail_after(monkeypatch, lib.engine, "_commit_track", Crash())
    with pytest.raises(Crash):
        lib.engine.apply_batch([lib.proposal()])
    monkeypatch.undo()
    assert journal_states(lib.conn) == ["COMMITTED"]
    assert lib.src.exists() and lib.target.exists()  # nothing lost: both copies exist
    assert [r["state"] for r in lib.engine.recover()] == ["COMPLETED"]
    assert lib.target.exists() and not lib.src.exists()
    assert lib.conn.execute("SELECT count(*) FROM tracks").fetchone()[0] == 1


def test_recovery_never_retires_a_changed_source(lib, monkeypatch):
    fail_after(monkeypatch, lib.engine, "_commit_track", Crash())
    with pytest.raises(Crash):
        lib.engine.apply_batch([lib.proposal()])
    monkeypatch.undo()
    lib.src.write_bytes(lib.src.read_bytes() + b"edited later")
    assert [r["state"] for r in lib.engine.recover()] == ["NEEDS_REVIEW"]
    assert lib.src.exists()


def test_recovery_leaves_foreign_file_at_target_alone(lib, monkeypatch):
    fail_after(monkeypatch, lib.engine, "_install", Crash())
    with pytest.raises(Crash):
        lib.engine.apply_batch([lib.proposal()])
    monkeypatch.undo()
    lib.target.unlink()
    lib.target.write_bytes(b"foreign file written after the crash")
    assert [r["state"] for r in lib.engine.recover()] == ["NEEDS_REVIEW"]
    assert lib.target.read_bytes() == b"foreign file written after the crash"
    assert lib.src.exists()


def test_source_retirement_failure_after_commit_is_reported_not_hidden(lib, monkeypatch):
    real_unlink = os.unlink

    def no_unlink_source(p, *a, **k):
        if str(p) == str(lib.src):
            raise PermissionError("injected")
        return real_unlink(p, *a, **k)

    monkeypatch.setattr(engine_mod.os, "unlink", no_unlink_source)
    res = lib.engine.apply_batch([lib.proposal()])
    assert res[0]["status"] == "COMMITTED_SOURCE_RETAINED" and res[0]["source_retired"] is False
    monkeypatch.undo()
    assert journal_states(lib.conn) == ["COMMITTED"]
    assert [r["state"] for r in lib.engine.recover()] == ["COMPLETED"]
    assert not lib.src.exists()


def test_recovery_refuses_unsupported_schema(tmp_path):
    conn = sqlite3.connect(tmp_path / "old.sqlite3")
    conn.execute("PRAGMA user_version = 6")
    with pytest.raises(RuntimeError, match="UNSUPPORTED_SCHEMA_VERSION"):
        recover_interrupted_transactions(conn, tmp_path)


# ------------------------------------------------------------ real SIGKILL
_KILL_SCRIPT = """
import os, signal, sqlite3, sys
from pathlib import Path
from invariantaudio.transactions.engine import TransactionEngine

root, point = Path(sys.argv[1]), sys.argv[2]
conn = sqlite3.connect(root / "catalog.sqlite3")
eng = TransactionEngine(conn, root / "backups", root / "staging", root / "mutation.lock", media_root=root / "media")

def kill(*a, **k):
    os.kill(os.getpid(), signal.SIGKILL)

if point == "before_commit":
    eng._commit_track = kill
else:
    orig = eng._commit_track
    def after(*a, **k):
        orig(*a, **k)
        kill()
    eng._commit_track = after
eng.apply_batch([{"source_path": str(root / "media" / "raw_track.mp3"),
                  "target_path": str(root / "media" / "Artist" / "Album" / "01 - Song.mp3"),
                  "tags": {"title": "Song"}}])
"""


@pytest.mark.parametrize("point, expected", [("before_commit", "ROLLED_BACK"), ("after_commit", "COMPLETED")])
def test_recovery_after_real_sigkill(lib, point, expected):
    import signal
    import subprocess
    import sys
    proc = subprocess.run([sys.executable, "-c", _KILL_SCRIPT, str(lib.tmp), point], capture_output=True, text=True)
    assert proc.returncode == -signal.SIGKILL, proc.stderr
    # The killed process held the flock; the kernel released it with the process.
    states = journal_states(sqlite3.connect(lib.tmp / "catalog.sqlite3"))
    assert states == ["INSTALLED" if point == "before_commit" else "COMMITTED"]
    assert [r["state"] for r in lib.engine.recover()] == [expected]
    if expected == "ROLLED_BACK":
        assert_library_untouched(lib)
    else:
        assert lib.target.exists() and not lib.src.exists()
        assert lib.conn.execute("SELECT count(*) FROM tracks").fetchone()[0] == 1
