# Command-Line Interface (v0.1.0-alpha)

`--config` is a global option and must precede the subcommand.

```bash
invariant-audio --config config.yaml init-db   # create the schema (v7) in database_path; refuses other versions
invariant-audio --config config.yaml scan      # list audio files (read-only)
invariant-audio --config config.yaml audit     # compare indexed paths with files on disk (read-only)
invariant-audio verify /path/to/track.mp3      # stream-health classification; needs no config
invariant-audio --config config.yaml recover   # resolve interrupted transactions (modifies files; exit 3 if review needed)
```

Exit codes: 0 success; 1 operational failure; 2 missing or invalid configuration; 3 `recover` left transactions needing review.

## Python API only (no CLI in this release)
- `TransactionEngine(conn, backup_root, staging_root, lock_path, media_root=None, batch_size_limit=10).apply_batch(proposals)`; each proposal is `{"source_path", "target_path", "tags": {title, artist, album, year, track_number}}`.
- `quarantine.isolate_to_quarantine(src, quarantine_root, backup_root, category)`.
- `evidence`, `duplicates`, `approvals`, `identification` helpers (see [identification.md](identification.md)).
