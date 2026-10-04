# Command-Line Interface Reference (v0.1.0-alpha)

## Implemented CLI Commands
```bash
# Initialize SQLite database schema v6
invariant-audio init-db --config config.yaml

# Read-only scan of media library
invariant-audio scan --config config.yaml

# Verify individual audio stream integrity
invariant-audio verify /path/to/track.mp3

# Run full library inventory balance audit
invariant-audio audit --config config.yaml
```

## Programmatic APIs (Roadmap CLI Subcommands in v0.2.0)
The following capabilities are implemented and tested in the `invariantaudio` Python API:
- **`TransactionEngine.apply_batch()`**: Staged tag writing with payload and PCM verification.
- **`quarantine.isolate_to_quarantine()`**: Safe quarantine isolation with dual backups.
- **`recovery.init_database()`**: Schema v6 migration and state reconciliation.
