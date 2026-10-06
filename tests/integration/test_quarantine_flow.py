# SPDX-License-Identifier: GPL-3.0-or-later
import shutil
from pathlib import Path

import pytest

from helpers import sha256_of
from invariantaudio.quarantine.manager import isolate_to_quarantine

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def q(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    return media, tmp_path / "quarantine", tmp_path / "backups"


def make(media, name, content_from, sub=""):
    d = media / sub
    d.mkdir(parents=True, exist_ok=True)
    f = d / name
    shutil.copy2(content_from, f)
    return f


def test_quarantine_isolation_workflow(q):
    media, qroot, broot = q
    f = make(media, "bad_track.mp3", FIXTURES_DIR / "corrupt_header.mp3")
    sha = sha256_of(f)
    q_file = isolate_to_quarantine(f, qroot, broot, category="severe-damage")
    assert q_file.exists() and sha256_of(q_file) == sha
    assert not f.exists()
    backups = list(broot.iterdir())
    assert len(backups) == 1 and sha256_of(backups[0]) == sha


def test_same_name_different_content_never_overwrites(q):
    media, qroot, broot = q
    a = make(media, "dup.mp3", FIXTURES_DIR / "corrupt_header.mp3", "one")
    b = make(media, "dup.mp3", FIXTURES_DIR / "synthetic_test_track.mp3", "two")
    sa, sb = sha256_of(a), sha256_of(b)
    qa = isolate_to_quarantine(a, qroot, broot)
    qb = isolate_to_quarantine(b, qroot, broot)
    assert qa != qb
    assert {sha256_of(qa), sha256_of(qb)} == {sa, sb}
    assert {sha256_of(p) for p in broot.iterdir()} == {sa, sb}


def test_quarantine_destination_collision_keeps_original(q):
    media, qroot, broot = q
    a = make(media, "x.mp3", FIXTURES_DIR / "corrupt_header.mp3", "one")
    isolate_to_quarantine(a, qroot, broot)
    again = make(media, "x.mp3", FIXTURES_DIR / "corrupt_header.mp3", "two")  # identical name + bytes
    existing = next((qroot / "no-usable-audio").iterdir())
    before = existing.stat().st_ino
    with pytest.raises(FileExistsError, match="QUARANTINE_COLLISION"):
        isolate_to_quarantine(again, qroot, broot)
    assert again.exists()
    assert existing.stat().st_ino == before
    assert not [p for p in (qroot / "no-usable-audio").iterdir() if p.name.endswith(".tmp")]


def test_backup_destination_collision_keeps_original(q):
    media, qroot, broot = q
    a = make(media, "x.mp3", FIXTURES_DIR / "corrupt_header.mp3")
    broot.mkdir()
    (broot / f"{sha256_of(a)[:12]}_x.mp3").write_bytes(b"different bytes squatting on the backup name")
    with pytest.raises(FileExistsError, match="BACKUP_COLLISION"):
        isolate_to_quarantine(a, qroot, broot)
    assert a.exists()
    assert not qroot.exists() or not any(qroot.rglob("*.mp3"))
    assert (broot / f"{sha256_of(a)[:12]}_x.mp3").read_bytes().startswith(b"different")


@pytest.mark.parametrize("bad", ["../escape", "a/b", "/abs", "", ".hidden", "x..y"])
def test_unsafe_category_is_rejected(q, bad):
    media, qroot, broot = q
    a = make(media, "x.mp3", FIXTURES_DIR / "corrupt_header.mp3")
    with pytest.raises(ValueError, match="INVALID_QUARANTINE_CATEGORY"):
        isolate_to_quarantine(a, qroot, broot, category=bad)
    assert a.exists() and not broot.exists()


def test_symlink_source_is_rejected(q):
    media, qroot, broot = q
    real = make(media, "real.mp3", FIXTURES_DIR / "corrupt_header.mp3")
    link = media / "link.mp3"
    link.symlink_to(real)
    with pytest.raises(ValueError, match="SYMLINK_NOT_PERMITTED"):
        isolate_to_quarantine(link, qroot, broot)
    assert real.exists() and link.is_symlink()


def test_missing_source(q):
    media, qroot, broot = q
    with pytest.raises(FileNotFoundError):
        isolate_to_quarantine(media / "nope.mp3", qroot, broot)
