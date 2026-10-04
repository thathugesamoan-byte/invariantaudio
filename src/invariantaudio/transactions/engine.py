# SPDX-License-Identifier: GPL-3.0-or-later
"""
Transactional Mutation Engine with Bit-Exact Invariant Verification.
"""

import os
import shutil
import sqlite3
import unicodedata
from pathlib import Path
from typing import Dict, Any, List
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TPOS
from mutagen.mp4 import MP4
from invariantaudio.integrity.audio_integrity import (
    compute_compressed_audio_payload_sha256,
    compute_decoded_pcm_sha256,
    compute_file_sha256
)
from invariantaudio.transactions.source_continuity import capture_source_binding, verify_source_continuity
from invariantaudio.transactions.lock import MutationLock

def normalize_path_unicode(p: str | Path) -> Path:
    norm_str = unicodedata.normalize("NFC", str(p))
    return Path(norm_str)

class TransactionEngine:
    def __init__(self, db_conn: sqlite3.Connection, backup_root: Path, staging_root: Path, lock_path: Path):
        self.conn = db_conn
        self.backup_root = backup_root
        self.staging_root = staging_root
        self.lock_path = lock_path

    def apply_batch(self, proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply a batch of proposals under exclusive lock with bit-exact verification."""
        results = []
        with MutationLock(self.lock_path):
            for prop in proposals:
                res = self._apply_single_proposal(prop)
                results.append(res)
        return results

    def _apply_single_proposal(self, prop: Dict[str, Any]) -> Dict[str, Any]:
        src_path = normalize_path_unicode(prop["source_path"])
        tgt_path = normalize_path_unicode(prop["target_path"])

        # 1. Source continuity binding
        binding = capture_source_binding(src_path)

        # 2. Pre-mutation audio payload and PCM hash extraction
        pre_payload_sha = compute_compressed_audio_payload_sha256(src_path)
        pre_pcm_sha = compute_decoded_pcm_sha256(src_path)

        # 3. Create pre-move backup
        self.backup_root.mkdir(parents=True, exist_ok=True)
        backup_file = self.backup_root / f"{binding.inode}_{src_path.name}"
        shutil.copy2(src_path, backup_file)

        # 4. Copy to SSD staging for mutation
        self.staging_root.mkdir(parents=True, exist_ok=True)
        staging_file = self.staging_root / f"staging_{binding.inode}_{src_path.name}"
        shutil.copy2(src_path, staging_file)

        try:
            # 5. Write Tags in Staging
            self._write_metadata(staging_file, prop.get("tags", {}))

            # 6. Post-mutation bit-exact verification
            post_payload_sha = compute_compressed_audio_payload_sha256(staging_file)
            post_pcm_sha = compute_decoded_pcm_sha256(staging_file)

            if post_payload_sha != pre_payload_sha:
                raise RuntimeError(f"PAYLOAD_MISMATCH: {post_payload_sha} vs {pre_payload_sha}")
            if post_pcm_sha != pre_pcm_sha:
                raise RuntimeError(f"PCM_MISMATCH: {post_pcm_sha} vs {pre_pcm_sha}")

            # 7. Atomic move to target
            tgt_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging_file, tgt_path)

            # If src_path != tgt_path and src_path still exists, remove src
            if src_path.resolve() != tgt_path.resolve() and src_path.exists():
                src_path.unlink()

            post_file_sha = compute_file_sha256(tgt_path)

            # 8. Commit to SQLite
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO tracks (canonical_path, original_path, sha256, compressed_audio_sha256, verification_status)
                VALUES (?, ?, ?, ?, 'TRUSTED')
            """, (str(tgt_path), str(src_path), post_file_sha, post_payload_sha))
            self.conn.commit()

            return {
                "status": "COMMITTED",
                "source_path": str(src_path),
                "target_path": str(tgt_path),
                "file_sha256": post_file_sha,
                "payload_sha256": post_payload_sha
            }

        except Exception as e:
            if staging_file.exists():
                staging_file.unlink()
            raise RuntimeError(f"MUTATION_FAILED for {src_path}: {e}")

    def _write_metadata(self, path: Path, tags: Dict[str, Any]) -> None:
        ext = path.suffix.lower()
        if ext == ".mp3":
            try:
                audio = ID3(path)
            except Exception:
                audio = ID3()
            if "title" in tags:
                audio["TIT2"] = TIT2(encoding=3, text=[tags["title"]])
            if "artist" in tags:
                audio["TPE1"] = TPE1(encoding=3, text=[tags["artist"]])
            if "album" in tags:
                audio["TALB"] = TALB(encoding=3, text=[tags["album"]])
            if "year" in tags:
                audio["TDRC"] = TDRC(encoding=3, text=[str(tags["year"])])
            if "track_number" in tags:
                audio["TRCK"] = TRCK(encoding=3, text=[str(tags["track_number"])])
            audio.save(path, v2_version=4)
        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(path)
            if "title" in tags:
                audio["\xa9nam"] = [tags["title"]]
            if "artist" in tags:
                audio["\xa9ART"] = [tags["artist"]]
            if "album" in tags:
                audio["\xa9alb"] = [tags["album"]]
            audio.save()
