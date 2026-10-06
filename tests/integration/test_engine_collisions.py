# SPDX-License-Identifier: GPL-3.0-or-later
"""The engine must never overwrite or alias an existing destination."""
import os
import shutil
import unicodedata

import pytest

from helpers import assert_library_untouched, journal_states, sha256_of
from invariantaudio.transactions.engine import (
    TransactionError,
    classify_target,
)


def _refused(lib, code, **kw):
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal(**kw)])
    assert ei.value.code == code
    return ei.value


def test_absent_target_is_classified_absent(lib):
    assert classify_target(lib.src, lib.target) == "ABSENT"


def test_existing_unrelated_target_is_never_overwritten(lib):
    lib.target.parent.mkdir(parents=True)
    lib.target.write_bytes(b"someone else's file")
    before = (sha256_of(lib.target), lib.target.stat().st_ino)
    _refused(lib, "TARGET_EXISTS_DIFFERENT")
    assert (sha256_of(lib.target), lib.target.stat().st_ino) == before
    assert sha256_of(lib.src) == lib.src_sha
    assert journal_states(lib.conn) == []  # refused before any journaling or staging
    assert not lib.staging.exists() or not any(lib.staging.iterdir())


def test_existing_identical_target_is_not_replaced(lib):
    lib.target.parent.mkdir(parents=True)
    shutil.copy2(lib.src, lib.target)
    ino = lib.target.stat().st_ino
    _refused(lib, "TARGET_EXISTS_IDENTICAL")
    assert lib.target.stat().st_ino == ino
    assert lib.src.exists()


def test_target_equal_to_source_path_is_refused(lib):
    _refused(lib, "TARGET_IS_SOURCE", tgt=lib.src)
    assert sha256_of(lib.src) == lib.src_sha


def test_hardlink_alias_of_source_is_refused(lib):
    alias = lib.media / "alias.mp3"
    os.link(lib.src, alias)
    _refused(lib, "TARGET_ALIASES_SOURCE", tgt=alias)
    assert alias.exists() and lib.src.exists()


def test_symlink_at_target_is_refused_even_if_dangling(lib):
    lib.target.parent.mkdir(parents=True)
    lib.target.symlink_to(lib.tmp / "nowhere.mp3")
    _refused(lib, "TARGET_EXISTS_NOT_REGULAR")
    assert lib.target.is_symlink()


def test_directory_at_target_is_refused(lib):
    lib.target.mkdir(parents=True)
    _refused(lib, "TARGET_EXISTS_NOT_REGULAR")


def test_unicode_normalization_collision_is_refused(lib):
    nfd = unicodedata.normalize("NFD", "Café.mp3")
    nfc = unicodedata.normalize("NFC", "Café.mp3")
    assert nfd != nfc
    d = lib.media / "A"
    d.mkdir()
    (d / nfd).write_bytes(b"existing decomposed name")
    err = _refused(lib, "TARGET_NAME_COLLISION", tgt=d / nfc)
    assert (d / nfd).read_bytes() == b"existing decomposed name"
    assert not (d / nfc).exists()
    assert err.completed == []


def test_unicode_collision_in_directory_component_is_refused(lib):
    nfd_dir = lib.media / unicodedata.normalize("NFD", "Björk")
    nfd_dir.mkdir()
    tgt = lib.media / unicodedata.normalize("NFC", "Björk") / "song.mp3"
    _refused(lib, "TARGET_NAME_COLLISION", tgt=tgt)
    assert not tgt.parent.exists()


def test_case_equivalent_collision_is_refused(lib):
    (lib.media / "Artist").mkdir()
    (lib.media / "Artist" / "SONG.mp3").write_bytes(b"x")
    _refused(lib, "TARGET_NAME_COLLISION", tgt=lib.media / "Artist" / "song.mp3")


def test_nfd_source_name_is_still_usable(lib):
    """The source path is never normalised, only the target."""
    nfd_src = lib.media / (unicodedata.normalize("NFD", "Café") + ".mp3")
    os.rename(lib.src, nfd_src)
    res = lib.engine.apply_batch([lib.proposal(src=nfd_src)])
    assert res[0]["status"] == "COMMITTED"


def test_target_appearing_during_transaction_is_not_overwritten(lib, monkeypatch):
    """Race: someone creates the target after the pre-check but before install."""
    original = lib.engine._backup_and_stage

    def stage_then_race(*a, **k):
        original(*a, **k)
        lib.target.parent.mkdir(parents=True, exist_ok=True)
        lib.target.write_bytes(b"raced in")

    monkeypatch.setattr(lib.engine, "_backup_and_stage", stage_then_race)
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal()])
    assert ei.value.code == "TARGET_EXISTS_AT_INSTALL"
    assert lib.target.read_bytes() == b"raced in"
    assert sha256_of(lib.src) == lib.src_sha
    assert journal_states(lib.conn) == ["ABORTED"]
    assert not any(lib.staging.iterdir())


def test_target_already_indexed_is_refused(lib):
    lib.conn.execute(
        "INSERT INTO tracks (canonical_path, original_path, sha256, compressed_audio_sha256) VALUES (?, ?, 'a', 'b')",
        (str(lib.target), "x"),
    )
    lib.conn.commit()
    _refused(lib, "TARGET_ALREADY_INDEXED")


def test_target_outside_media_root_is_refused(lib):
    _refused(lib, "TARGET_OUTSIDE_MEDIA_ROOT", tgt=lib.media / ".." / "escaped" / "x.mp3")
    assert not (lib.tmp / "escaped").exists()


def test_duplicate_targets_in_batch_are_refused_before_any_mutation(lib):
    other = lib.media / "second.mp3"
    shutil.copy2(lib.src, other)
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal(), lib.proposal(src=other)])
    assert ei.value.code == "DUPLICATE_TARGET_IN_BATCH"
    assert lib.src.exists() and other.exists() and not lib.target.exists()
    assert journal_states(lib.conn) == []


def test_oversized_batch_is_refused(lib):
    lib.engine.batch_size_limit = 1
    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal(), lib.proposal(tgt=lib.media / "b.mp3")])
    assert ei.value.code == "BATCH_TOO_LARGE"


def test_same_name_sources_get_distinct_backups(lib, alt_mp3):
    """Duplicate backup filenames: two sources named identically must both be preserved."""
    d2 = lib.media / "other"
    d2.mkdir()
    src2 = d2 / "raw_track.mp3"
    shutil.copy2(alt_mp3, src2)
    sha2 = sha256_of(src2)
    res = lib.engine.apply_batch([lib.proposal(), lib.proposal(src=src2, tgt=lib.media / "B" / "02 - Other.mp3")])
    assert [r["status"] for r in res] == ["COMMITTED", "COMMITTED"]
    backups = sorted(p for p in lib.backup.iterdir())
    assert len(backups) == 2
    assert {sha256_of(p) for p in backups} == {lib.src_sha, sha2}


def test_preexisting_file_at_backup_path_is_not_overwritten(lib):
    lib.backup.mkdir()
    victim = lib.backup / f"1_{lib.src_sha[:12]}_raw_track.mp3"
    victim.write_bytes(b"older backup that must survive")
    with pytest.raises(TransactionError):
        lib.engine.apply_batch([lib.proposal()])
    assert victim.read_bytes() == b"older backup that must survive"
    assert_library_untouched(lib)
    assert journal_states(lib.conn) == ["ABORTED"]
