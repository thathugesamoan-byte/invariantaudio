# Known Limitations (v0.1.0-alpha)

1. **Linux/POSIX only.** Locking uses `fcntl.flock`; only Linux (Ubuntu 24.04 in CI) is tested.
2. **Hard links required.** The target is installed with `os.link`; filesystems without hard-link support fail closed.
3. **Supported media for mutation: `.mp3` and `.m4a` only.** Other extensions are rejected. Scanning lists additional extensions but they cannot be mutated.
4. **No in-place retagging.** Source and target must differ.
5. **Not ACID across file system + SQLite**; crash safety comes from the journal and `recover` ([transaction-model.md](transaction-model.md)). No power-loss testing.
6. **No identification, network, or approval features** ([ROADMAP.md](../ROADMAP.md)).
7. **No CLI for applying batches or quarantining**; Python API only.
8. **Quarantine is not journaled** and does not overwrite; an interrupted run needs manual review.
9. **Hash scope.** Only the first audio stream is hashed; PCM is hashed after normalization to 16-bit/44.1 kHz/stereo.
10. **Stream-health classes are string-matches** on `ffmpeg` output and vary by `ffmpeg` version.
11. **No lossy repair.** Damaged files are classified, never repaired.
12. **Rollback does not remove directories** created for a target path.
13. **Backups accumulate**; none are deleted automatically.
14. **Dependencies are lower-bounded, not pinned** (`mutagen>=1.45`, `pyyaml>=6`).
