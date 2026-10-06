# SPDX-License-Identifier: GPL-3.0-or-later
"""
Quarantine isolation: back up a file, place it in quarantine, remove the original.

Not journaled: unlike TransactionEngine this workflow has no recovery state
machine. It never overwrites an existing backup or quarantine file; on any
collision or failure the original is left in place.
"""

import os
import re
from pathlib import Path

from invariantaudio.fsutil import copy_exclusive as _copy_exclusive
from invariantaudio.integrity.audio_integrity import compute_file_sha256
from invariantaudio.transactions.source_continuity import capture_source_binding, verify_source_continuity

_CATEGORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def isolate_to_quarantine(
    src_file: Path,
    quarantine_root: Path,
    backup_root: Path,
    category: str = "no-usable-audio",
) -> Path:
    """Back up ``src_file``, place a verified copy in quarantine, then remove the original.

    File names are prefixed with the first 12 hex digits of the content SHA-256,
    so different files that share a name never collide. Raises ``FileExistsError``
    if the quarantine destination already exists (it is never overwritten) and
    ``ValueError`` for symlinks, non-regular files or an unsafe category name.
    """
    if not isinstance(category, str) or not _CATEGORY.fullmatch(category) or ".." in category:
        raise ValueError(f"INVALID_QUARANTINE_CATEGORY: {category!r}")
    src = os.path.abspath(str(src_file))
    if not os.path.lexists(src):
        raise FileNotFoundError(f"Source not found: {src}")
    binding = capture_source_binding(src)  # rejects symlinks / non-regular files
    prefix = binding.whole_file_sha256[:12]
    name = os.path.basename(src)

    backup_root = Path(backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / f"{prefix}_{name}"
    if os.path.lexists(backup_path):
        # Reuse only a byte-identical backup (e.g. retry after interruption).
        if compute_file_sha256(backup_path) != binding.whole_file_sha256:
            raise FileExistsError(f"BACKUP_COLLISION: {backup_path}")
    else:
        _copy_exclusive(src, str(backup_path))
        if compute_file_sha256(backup_path) != binding.whole_file_sha256:
            raise RuntimeError("BACKUP_HASH_MISMATCH")

    target_dir = Path(quarantine_root) / category
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{prefix}_{name}"
    if os.path.lexists(target_file):
        raise FileExistsError(f"QUARANTINE_COLLISION: {target_file}")
    tmp = target_dir / f".{prefix}_{os.getpid()}.tmp"
    try:
        _copy_exclusive(src, str(tmp))
        if compute_file_sha256(tmp) != binding.whole_file_sha256:
            raise RuntimeError("QUARANTINE_HASH_MISMATCH")
        os.link(tmp, target_file)  # never replaces an existing file
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)

    if not verify_source_continuity(binding):
        raise RuntimeError("SOURCE_CHANGED: original left in place; quarantine copy kept for review")
    os.unlink(src)
    return target_file
