# SPDX-License-Identifier: GPL-3.0-or-later
"""Small filesystem helpers shared by the mutation workflows."""

import os
import shutil


def fsync_file(path: str) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def fsync_dir(path: str) -> None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def copy_exclusive(src: str, dst: str) -> None:
    """Copy ``src`` to a new file ``dst``; never overwrites (O_EXCL)."""
    fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    with open(src, "rb") as fi, os.fdopen(fd, "wb") as fo:
        shutil.copyfileobj(fi, fo, 1024 * 1024)
        fo.flush()
        os.fsync(fo.fileno())
    shutil.copystat(src, dst)
