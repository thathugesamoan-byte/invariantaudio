# SPDX-License-Identifier: GPL-3.0-or-later
"""
Source Continuity & Anti-TOCTOU Physical Inode Binding.
"""

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from invariantaudio.integrity.audio_integrity import compute_file_sha256

@dataclass(frozen=True)
class SourceBindingTuple:
    path: str
    device: int
    inode: int
    nlink: int
    size: int
    whole_file_sha256: str

def capture_source_binding(path: str | Path) -> SourceBindingTuple:
    """Capture the immutable physical tuple of a regular file."""
    path_str = os.path.abspath(str(path))
    st = os.lstat(path_str)
    
    if stat.S_ISLNK(st.st_mode):
        raise ValueError(f"SYMLINK_NOT_PERMITTED: {path}")
    if not stat.S_ISREG(st.st_mode):
        raise ValueError(f"NOT_A_REGULAR_FILE: {path}")
        
    sha = compute_file_sha256(path_str)
    return SourceBindingTuple(
        path=path_str,
        device=st.st_dev,
        inode=st.st_ino,
        nlink=st.st_nlink,
        size=st.st_size,
        whole_file_sha256=sha
    )

def verify_source_continuity(binding: SourceBindingTuple) -> bool:
    """Verify that the on-disk file currently matches its recorded physical tuple."""
    if not os.path.exists(binding.path):
        return False
    st = os.lstat(binding.path)
    if (st.st_dev, st.st_ino, st.st_size) != (binding.device, binding.inode, binding.size):
        return False
    current_sha = compute_file_sha256(binding.path)
    return current_sha == binding.whole_file_sha256
