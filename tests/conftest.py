# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import math
import struct
import subprocess
import wave
from pathlib import Path

# The package must be installed (``pip install -e .`` or a built wheel); tests never
# import it from the source tree implicitly.
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


# --------------------------------------------------------------------------
# Shared helpers for transaction tests
# --------------------------------------------------------------------------
import shutil
import sqlite3
from types import SimpleNamespace

from helpers import sha256_of
from invariantaudio.recovery.recovery_manager import init_database
from invariantaudio.transactions.engine import TransactionEngine


@pytest.fixture(scope="session")
def alt_mp3(tmp_path_factory):
    """A second, different, valid mp3 (used to simulate source replacement)."""
    out = tmp_path_factory.mktemp("alt") / "alt.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(FIXTURES_DIR / "sine_880hz_2s.wav"),
         "-c:a", "libmp3lame", "-b:a", "128k", str(out)],
        check=True,
    )
    return out


@pytest.fixture
def lib(tmp_path):
    """A scratch library: media dir, db, roots, one mp3 source, an engine."""
    conn = sqlite3.connect(tmp_path / "catalog.sqlite3")
    init_database(conn)
    media = tmp_path / "media"
    media.mkdir()
    src = media / "raw_track.mp3"
    shutil.copy2(FIXTURES_DIR / "synthetic_test_track.mp3", src)
    ns = SimpleNamespace(
        tmp=tmp_path, conn=conn, media=media, src=src,
        backup=tmp_path / "backups", staging=tmp_path / "staging", lock=tmp_path / "mutation.lock",
        src_sha=sha256_of(src),
        target=media / "Artist" / "Album" / "01 - Song.mp3",
    )
    ns.engine = TransactionEngine(conn, ns.backup, ns.staging, ns.lock, media_root=media)
    ns.proposal = lambda **kw: {"source_path": str(kw.get("src", ns.src)), "target_path": str(kw.get("tgt", ns.target)),
                                "tags": kw.get("tags", {"title": "Song", "artist": "Artist", "album": "Album"})}
    yield ns
    conn.close()
