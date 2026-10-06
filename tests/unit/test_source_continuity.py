# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import os
from pathlib import Path
from invariantaudio.transactions.source_continuity import (
    capture_source_binding,
    verify_source_continuity
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

def test_capture_and_verify_continuity():
    wav = FIXTURES_DIR / "sine_440hz_1s.wav"
    binding = capture_source_binding(wav)
    assert binding.size > 0
    assert binding.nlink >= 1
    assert verify_source_continuity(binding) is True

def test_reject_symlink(tmp_path):
    real_file = tmp_path / "real.txt"
    real_file.write_text("hello")
    sym = tmp_path / "symlink.txt"
    sym.symlink_to(real_file)

    with pytest.raises(ValueError, match="SYMLINK_NOT_PERMITTED"):
        capture_source_binding(sym)


def _bound(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"0123456789" * 100)
    return f, capture_source_binding(f)


def test_modification_is_detected(tmp_path):
    f, b = _bound(tmp_path)
    with open(f, "ab") as fh:
        fh.write(b"x")
    assert verify_source_continuity(b) is False


def test_same_size_content_change_is_detected(tmp_path):
    f, b = _bound(tmp_path)
    data = bytearray(f.read_bytes())
    data[0] ^= 1
    f.write_bytes(bytes(data))
    assert verify_source_continuity(b) is False


def test_replacement_by_new_inode_is_detected(tmp_path):
    f, b = _bound(tmp_path)
    other = tmp_path / "b.bin"
    other.write_bytes(f.read_bytes())  # identical bytes, different inode
    os.replace(other, f)
    assert verify_source_continuity(b) is False


def test_hard_link_count_change_is_detected(tmp_path):
    f, b = _bound(tmp_path)
    assert b.nlink == 1
    os.link(f, tmp_path / "second-name")
    assert verify_source_continuity(b) is False


def test_swap_to_symlink_is_detected(tmp_path):
    f, b = _bound(tmp_path)
    target = tmp_path / "real"
    target.write_bytes(f.read_bytes())
    f.unlink()
    f.symlink_to(target)
    assert verify_source_continuity(b) is False


def test_missing_file_is_a_mismatch(tmp_path):
    f, b = _bound(tmp_path)
    f.unlink()
    assert verify_source_continuity(b) is False


def test_directory_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="NOT_A_REGULAR_FILE"):
        capture_source_binding(tmp_path)


def test_unchanged_file_verifies_repeatedly(tmp_path):
    f, b = _bound(tmp_path)
    assert verify_source_continuity(b) and verify_source_continuity(b)
