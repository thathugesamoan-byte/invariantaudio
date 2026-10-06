# SPDX-License-Identifier: GPL-3.0-or-later
"""
Advisory POSIX file lock (flock). Coordinates cooperating InvariantAudio
processes only; other programs are not prevented from touching files.
"""

import os
import fcntl
from pathlib import Path
from types import TracebackType
from typing import Optional

class MutationLock:
    """Context manager acquiring an exclusive POSIX advisory lock via flock."""
    def __init__(self, lock_path: str | Path):
        self.lock_path = Path(lock_path)
        self._fd: Optional[int] = None

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC, 0o600)
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(self._fd, f"PID={os.getpid()}\n".encode("utf-8"))
        except (BlockingIOError, OSError) as e:
            os.close(self._fd)
            self._fd = None
            raise RuntimeError(f"MUTATION_LOCK_CONTENTION: Lock held by another process: {e}")

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass
            finally:
                os.close(self._fd)
                self._fd = None

    def __enter__(self) -> "MutationLock":
        self.acquire()
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]) -> None:
        self.release()
