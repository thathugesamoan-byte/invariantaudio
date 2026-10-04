# SPDX-License-Identifier: GPL-3.0-or-later
"""
Example usage of InvariantAudio programmatically.
"""

from pathlib import Path
from invariantaudio.config import AppConfig

def main():
    print("InvariantAudio — Example Script")
    cfg = AppConfig(
        media_root=Path("/path/to/music"),
        database_path=Path("/tmp/example_catalog.sqlite3"),
        backup_root=Path("/tmp/example_backups"),
        quarantine_root=Path("/tmp/example_quarantine"),
        work_root=Path("/tmp/example_staging"),
        mutation_lock_path=Path("/tmp/example.lock")
    )
    print(f"Configured Media Root: {cfg.media_root}")
    print("InvariantAudio initialized successfully.")

if __name__ == "__main__":
    main()
