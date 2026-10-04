# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from pathlib import Path
from invariantaudio.integrity.audio_integrity import (
    compute_file_sha256,
    compute_compressed_audio_payload_sha256,
    compute_decoded_pcm_sha256,
    inspect_stream_health
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

def test_file_sha256():
    wav = FIXTURES_DIR / "sine_440hz_1s.wav"
    sha = compute_file_sha256(wav)
    assert len(sha) == 64
    assert isinstance(sha, str)

def test_payload_and_pcm_extraction():
    mp3 = FIXTURES_DIR / "synthetic_test_track.mp3"
    payload_sha = compute_compressed_audio_payload_sha256(mp3)
    pcm_sha = compute_decoded_pcm_sha256(mp3)
    assert len(payload_sha) == 64
    assert len(pcm_sha) == 64

def test_stream_health_inspection():
    mp3 = FIXTURES_DIR / "synthetic_test_track.mp3"
    status, details = inspect_stream_health(mp3)
    assert status in ("TRUSTED", "DAMAGED_BUT_PLAYABLE")

def test_corrupt_file_inspection():
    corrupt = FIXTURES_DIR / "corrupt_header.mp3"
    status, _ = inspect_stream_health(corrupt)
    assert status in ("UNUSABLE", "INTEGRITY_EXCEPTION", "DAMAGED_BUT_PLAYABLE")
