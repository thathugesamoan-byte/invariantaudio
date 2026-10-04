# Transaction Engine & Locking Model

- **Advisory POSIX Locking (`flock`)**: Exclusive lock acquired on `.invariant_audio.lock` before touching media.
- **Staged Staging Directory**: File copied to isolated SSD staging folder; tags written and verified in staging before touching production target.
- **Atomic Swap**: Verified file moved to destination using atomic `os.replace`.
- **ACID Database Commit**: SQLite transaction commits `tracks` and `production_transactions` atomically.
