# SPDX-License-Identifier: GPL-3.0-or-later
"""
Library accounting: compare indexed track paths with audio files on disk.
"""

import os
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict

from invariantaudio.discovery.scanner import scan_directory_for_audio


def _key(p: str | Path) -> str:
    return unicodedata.normalize("NFC", os.path.abspath(str(p)))


def verify_master_balance(db_conn: sqlite3.Connection, media_root: Path) -> Dict[str, Any]:
    """Path-level comparison (not just counts). ``is_balanced`` is True only if
    every indexed path exists on disk and every audio file on disk is indexed."""
    db_paths = {_key(r[0]) for r in db_conn.execute("SELECT canonical_path FROM tracks;")}
    disk_paths = {_key(p) for p in scan_directory_for_audio(media_root)}
    unindexed = disk_paths - db_paths
    missing = db_paths - disk_paths
    return {
        "db_tracks": len(db_paths),
        "physical_media_files": len(disk_paths),
        "unindexed_files": len(unindexed),
        "missing_files": len(missing),
        "is_balanced": not unindexed and not missing,
    }
