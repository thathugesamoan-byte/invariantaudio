# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import sys
import os
import math
import struct
import subprocess
import wave
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures_exist():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    required = [
        "sine_440hz_1s.wav",
        "sine_880hz_2s.wav",
        "silence_1s.wav",
        "synthetic_test_track.mp3",
        "synthetic_test_track.m4a",
        "corrupt_header.mp3"
    ]
    missing = [f for f in required if not (FIXTURES_DIR / f).exists()]
    if missing:
        sample_rate = 44100
        wav1 = FIXTURES_DIR / "sine_440hz_1s.wav"
        if not wav1.exists():
            with wave.open(str(wav1), "wb") as wf:
                wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sample_rate)
                frames = bytearray()
                for i in range(int(sample_rate * 1.0)):
                    t = float(i) / sample_rate
                    val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * 440.0 * t))
                    frames.extend(struct.pack("<hh", val, val))
                wf.writeframes(frames)
        wav2 = FIXTURES_DIR / "sine_880hz_2s.wav"
        if not wav2.exists():
            with wave.open(str(wav2), "wb") as wf:
                wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sample_rate)
                frames = bytearray()
                for i in range(int(sample_rate * 2.0)):
                    t = float(i) / sample_rate
                    val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * 880.0 * t))
                    frames.extend(struct.pack("<hh", val, val))
                wf.writeframes(frames)
        sil = FIXTURES_DIR / "silence_1s.wav"
        if not sil.exists():
            with wave.open(str(sil), "wb") as wf:
                wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sample_rate)
                wf.writeframes(bytearray(int(sample_rate * 1.0) * 4))
        mp3 = FIXTURES_DIR / "synthetic_test_track.mp3"
        if not mp3.exists():
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav1), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)], check=True)
        m4a = FIXTURES_DIR / "synthetic_test_track.m4a"
        if not m4a.exists():
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav1), "-c:a", "aac", "-b:a", "128k", str(m4a)], check=True)
        bad = FIXTURES_DIR / "corrupt_header.mp3"
        if not bad.exists():
            bad.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x10INVALID_CORRUPT_BYTES\x00\x00")
