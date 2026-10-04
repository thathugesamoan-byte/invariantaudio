# SPDX-License-Identifier: GPL-3.0-or-later
"""
Master Library Accounting & Census Verification.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any

def verify_master_balance(db_conn: sqlite3.Connection, media_root: Path) -> Dict[str, Any]:
    cur = db_conn.cursor()
    db_tracks = cur.execute("SELECT count(*) FROM tracks;").fetchone()[0]
    
    # Count physical files on disk
    from invariantaudio.discovery.scanner import scan_directory_for_audio
    disk_files = len(scan_directory_for_audio(media_root))
    
    unindexed = max(0, disk_files - db_tracks)
    is_balanced = (db_tracks == disk_files and unindexed == 0)
    
    return {
        "db_tracks": db_tracks,
        "physical_media_files": disk_files,
        "unindexed_files": unindexed,
        "is_balanced": is_balanced
    }
