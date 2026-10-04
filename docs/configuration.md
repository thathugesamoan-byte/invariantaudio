# Configuration Guide

Configure paths, thresholds, and safety rules via YAML (e.g. `config.yaml`):

```yaml
media_root: "/path/to/music"
database_path: "/path/to/catalog.sqlite3"
backup_root: "/path/to/backups"
quarantine_root: "/path/to/quarantine"
work_root: "/path/to/staging"
mutation_lock_path: "/path/to/.invariant_audio.lock"
batch_size_limit: 10
enforce_payload_pcm_preservation: true
enforce_source_continuity: true
```
