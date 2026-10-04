# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import shutil
from pathlib import Path
from invariantaudio.integrity.audio_integrity import (
    compute_compressed_audio_payload_sha256,
    compute_decoded_pcm_sha256
)
from mutagen.id3 import ID3, TIT2, TPE1, TALB

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

def test_id3_tag_write_preserves_payload_and_pcm(tmp_path):
    src = tmp_path / "track.mp3"
    shutil.copy2(FIXTURES_DIR / "synthetic_test_track.mp3", src)

    pre_payload = compute_compressed_audio_payload_sha256(src)
    pre_pcm = compute_decoded_pcm_sha256(src)

    audio = ID3(src)
    audio["TIT2"] = TIT2(encoding=3, text=["New Title"])
    audio["TPE1"] = TPE1(encoding=3, text=["New Artist"])
    audio["TALB"] = TALB(encoding=3, text=["New Album"])
    audio.save(src, v2_version=4)

    post_payload = compute_compressed_audio_payload_sha256(src)
    post_pcm = compute_decoded_pcm_sha256(src)

    assert post_payload == pre_payload
    assert post_pcm == pre_pcm
