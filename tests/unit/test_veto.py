# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from invariantaudio.duplicates.veto import check_version_veto

def test_veto_live_vs_studio():
    assert check_version_veto("Hotel California (Live)", "Hotel California") is True
    assert check_version_veto("Hotel California (Live at The Forum)", "Hotel California (Live)") is False
    assert check_version_veto("Hotel California", "Hotel California") is False

def test_veto_remix_and_acoustic():
    assert check_version_veto("Song Title (Club Remix)", "Song Title") is True
    assert check_version_veto("Song Title", "Song Title (Acoustic Version)") is True
    assert check_version_veto("Song Title (Cover)", "Song Title") is True
