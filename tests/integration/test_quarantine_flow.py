# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import shutil
from pathlib import Path
from invariantaudio.quarantine.manager import isolate_to_quarantine

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

def test_quarantine_isolation_workflow(tmp_path):
    media_root = tmp_path / "media"
    media_root.mkdir()
    quarantine_root = tmp_path / "quarantine"
    backup_root = tmp_path / "backups"

    corrupt_file = media_root / "bad_track.mp3"
    shutil.copy2(FIXTURES_DIR / "corrupt_header.mp3", corrupt_file)

    q_file = isolate_to_quarantine(corrupt_file, quarantine_root, backup_root, category="severe-damage")
    
    assert q_file.exists()
    assert not corrupt_file.exists()
    assert (backup_root / "bad_track.mp3").exists()
