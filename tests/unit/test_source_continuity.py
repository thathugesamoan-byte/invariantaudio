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
