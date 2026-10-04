# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from pathlib import Path
from invariantaudio.transactions.lock import MutationLock

def test_lock_acquire_and_release(tmp_path):
    lock_file = tmp_path / "test.lock"
    with MutationLock(lock_file) as lock:
        assert lock_file.exists()
        assert lock._fd is not None

def test_lock_contention(tmp_path):
    lock_file = tmp_path / "test.lock"
    with MutationLock(lock_file):
        with pytest.raises(RuntimeError, match="MUTATION_LOCK_CONTENTION"):
            sec = MutationLock(lock_file)
            sec.acquire()
