# SPDX-License-Identifier: GPL-3.0-or-later
import sqlite3
import shutil
from pathlib import Path
from invariantaudio.transactions.engine import TransactionEngine
from invariantaudio.recovery.recovery_manager import init_database
from invariantaudio.integrity.audio_integrity import (
    compute_compressed_audio_payload_sha256,
    compute_decoded_pcm_sha256
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

def test_transaction_engine_mutation_and_preservation(tmp_path):
    db_file = tmp_path / "catalog.sqlite3"
    conn = sqlite3.connect(db_file)
    init_database(conn)

    backup_root = tmp_path / "backups"
    staging_root = tmp_path / "staging"
    lock_file = tmp_path / "mutation.lock"
    media_dir = tmp_path / "media"
    media_dir.mkdir()

    src_track = media_dir / "raw_track.mp3"
    shutil.copy2(FIXTURES_DIR / "synthetic_test_track.mp3", src_track)

    pre_payload = compute_compressed_audio_payload_sha256(src_track)
    pre_pcm = compute_decoded_pcm_sha256(src_track)

    engine = TransactionEngine(conn, backup_root, staging_root, lock_file, media_root=media_dir)

    target_track = media_dir / "Artist/Album [2026]/01 - Test Song.mp3"

    proposal = {
        "source_path": str(src_track),
        "target_path": str(target_track),
        "tags": {
            "title": "Test Song",
            "artist": "Artist",
            "album": "Album",
            "year": "2026",
            "track_number": "1"
        }
    }

    results = engine.apply_batch([proposal])
    assert len(results) == 1
    assert results[0]["status"] == "COMMITTED"
    assert target_track.exists()

    post_payload = compute_compressed_audio_payload_sha256(target_track)
    post_pcm = compute_decoded_pcm_sha256(target_track)
    assert post_payload == pre_payload
    assert post_pcm == pre_pcm

    cur = conn.cursor()
    row = cur.execute("SELECT track_id, canonical_path, verification_status FROM tracks;").fetchone()
    assert row is not None
    assert row[1] == str(target_track)
    assert row[2] in ("TRUSTED", "DAMAGED_BUT_PLAYABLE")
    conn.close()
