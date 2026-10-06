# SPDX-License-Identifier: GPL-3.0-or-later
"""
Source continuity: physical identity binding for a regular file.

A binding records ``(st_dev, st_ino, st_nlink, st_size, sha256)`` of a regular
file that is not a symlink. ``verify_source_continuity`` re-reads the same path
and returns True only if every element of the tuple is unchanged.

Scope: this detects that the file at a path changed between two points in time
(replacement, modification, hard-link count change). It cannot prevent a change
from happening, and it cannot detect a change that is made and then fully
reverted between two checks. It does not defend against a privileged local
attacker.
"""

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

_CHUNK = 65536


@dataclass(frozen=True)
class SourceBindingTuple:
    path: str
    device: int
    inode: int
    nlink: int
    size: int
    whole_file_sha256: str


def _open_regular_nofollow(path_str: str) -> Tuple[int, os.stat_result]:
    """Open a regular file without following symlinks; return (fd, fstat)."""
    st = os.lstat(path_str)
    if stat.S_ISLNK(st.st_mode):
        raise ValueError(f"SYMLINK_NOT_PERMITTED: {path_str}")
    if not stat.S_ISREG(st.st_mode):
        raise ValueError(f"NOT_A_REGULAR_FILE: {path_str}")
    try:
        fd = os.open(path_str, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as e:
        # O_NOFOLLOW reports ELOOP when the path became a symlink after lstat.
        raise ValueError(f"SYMLINK_NOT_PERMITTED: {path_str}: {e}")
    try:
        fst = os.fstat(fd)
        if not stat.S_ISREG(fst.st_mode):
            raise ValueError(f"NOT_A_REGULAR_FILE: {path_str}")
        return fd, fst
    except BaseException:
        os.close(fd)
        raise


def _hash_fd(fd: int) -> str:
    h = hashlib.sha256()
    while chunk := os.read(fd, _CHUNK):
        h.update(chunk)
    return h.hexdigest()


def capture_source_binding(path: str | Path) -> SourceBindingTuple:
    """Capture the physical tuple of a regular, non-symlink file."""
    path_str = os.path.abspath(str(path))
    fd, fst = _open_regular_nofollow(path_str)
    try:
        sha = _hash_fd(fd)
        end = os.fstat(fd)
    finally:
        os.close(fd)
    if (end.st_size, end.st_mtime_ns) != (fst.st_size, fst.st_mtime_ns):
        raise ValueError(f"SOURCE_CHANGED_DURING_BINDING: {path}")
    return SourceBindingTuple(
        path=path_str,
        device=fst.st_dev,
        inode=fst.st_ino,
        nlink=fst.st_nlink,
        size=fst.st_size,
        whole_file_sha256=sha,
    )


def verify_source_continuity(binding: SourceBindingTuple) -> bool:
    """Return True only if the file at ``binding.path`` still matches every
    element of the recorded tuple. Any error is treated as a mismatch."""
    try:
        fd, fst = _open_regular_nofollow(binding.path)
    except (OSError, ValueError):
        return False
    try:
        if (fst.st_dev, fst.st_ino, fst.st_nlink, fst.st_size) != (
            binding.device, binding.inode, binding.nlink, binding.size
        ):
            return False
        return _hash_fd(fd) == binding.whole_file_sha256
    except OSError:
        return False
    finally:
        os.close(fd)
