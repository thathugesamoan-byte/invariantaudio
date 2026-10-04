# SPDX-License-Identifier: GPL-3.0-or-later
"""
Safe Quarantine Isolation Workflow with Dual Backups.
"""

import os
import shutil
from pathlib import Path
from invariantaudio.integrity.audio_integrity import compute_file_sha256

def isolate_to_quarantine(
    src_file: Path,
    quarantine_root: Path,
    backup_root: Path,
    category: str = "no-usable-audio"
) -> Path:
    """Safely isolate an unplayable or non-canonical file."""
    src = Path(src_file).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")

    # 1. Authoritative pre-move backup
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / src.name
    shutil.copy2(src, backup_path)
    
    # 2. Copy to quarantine
    target_dir = quarantine_root / category
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / src.name
    shutil.copy2(src, target_file)

    # 3. Verify hashes
    src_sha = compute_file_sha256(src)
    q_sha = compute_file_sha256(target_file)
    if src_sha != q_sha:
        target_file.unlink()
        raise RuntimeError("QUARANTINE_HASH_MISMATCH")

    # 4. Remove original from media tree
    src.unlink()
    return target_file
