# SPDX-License-Identifier: GPL-3.0-or-later
"""The engine must fail closed when the source changes after it was bound."""
import os
import shutil

import pytest

import invariantaudio.transactions.engine as engine_mod
from helpers import journal_states
from invariantaudio.transactions.engine import TransactionError


def mutate(kind, lib, alt_mp3):
    if kind == "replace":  # different file, same path (new inode)
        tmp = lib.media / "swap.tmp"
        shutil.copy2(alt_mp3, tmp)
        os.replace(tmp, lib.src)
    elif kind == "modify":  # same inode, different bytes
        with open(lib.src, "ab") as f:
            f.write(b"\0appended")
    elif kind == "hardlink":  # same inode, same bytes, nlink 1 -> 2
        os.link(lib.src, lib.media / "extra-link.mp3")
    elif kind == "symlink":
        os.unlink(lib.src)
        lib.src.symlink_to(alt_mp3)
    else:
        raise AssertionError(kind)


def hook_after_binding(monkeypatch, src, fn):
    """Run ``fn`` once, right after the source has been bound (first payload hash)."""
    real = engine_mod.compute_compressed_audio_payload_sha256
    done = []

    def wrapper(p, *a, **k):
        if not done and str(p) == str(src):
            done.append(1)
            out = real(p, *a, **k)
            fn()
            return out
        return real(p, *a, **k)

    monkeypatch.setattr(engine_mod, "compute_compressed_audio_payload_sha256", wrapper)


@pytest.mark.parametrize("kind", ["replace", "modify", "hardlink", "symlink"])
@pytest.mark.parametrize("when", ["after_binding", "after_staging"])
def test_source_change_after_binding_fails_closed(lib, alt_mp3, monkeypatch, kind, when):
    if when == "after_binding":
        hook_after_binding(monkeypatch, lib.src, lambda: mutate(kind, lib, alt_mp3))
    else:
        original = lib.engine._write_metadata

        def write_then_mutate(path, tags):
            original(path, tags)
            mutate(kind, lib, alt_mp3)

        monkeypatch.setattr(lib.engine, "_write_metadata", write_then_mutate)

    with pytest.raises(TransactionError) as ei:
        lib.engine.apply_batch([lib.proposal()])
    assert ei.value.code == "SOURCE_CHANGED"
    assert not lib.target.exists()
    assert lib.conn.execute("SELECT count(*) FROM tracks").fetchone()[0] == 0
    assert not any(lib.staging.iterdir())
    assert journal_states(lib.conn) == ["ABORTED"]
    # Whatever the "attacker" left in place is untouched by the engine.
    assert lib.src.exists() or lib.src.is_symlink()


def test_continuity_is_verified_before_install_and_before_retirement(lib, monkeypatch):
    calls = []
    real_verify = engine_mod.verify_source_continuity

    def spy(binding):
        calls.append(binding.path)
        return real_verify(binding)

    monkeypatch.setattr(engine_mod, "verify_source_continuity", spy)
    lib.engine.apply_batch([lib.proposal()])
    assert len(calls) >= 2  # before install and before source retirement


def test_source_changed_between_install_and_retirement_is_not_deleted(lib, monkeypatch):
    original = lib.engine._commit_track

    def commit_then_edit(*a, **k):
        original(*a, **k)
        with open(lib.src, "ab") as f:
            f.write(b"user edit after commit")

    monkeypatch.setattr(lib.engine, "_commit_track", commit_then_edit)
    res = lib.engine.apply_batch([lib.proposal()])
    assert res[0]["status"] == "COMMITTED_SOURCE_RETAINED"
    assert lib.src.read_bytes().endswith(b"user edit after commit")
    assert lib.target.exists()
    assert journal_states(lib.conn) == ["COMMITTED"]
