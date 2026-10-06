# Configuration (v0.1.0-alpha)

`config.yaml` (copy of `config.example.yaml`; git-ignored). Parsing is strict: types are checked **without coercion** (the string `"false"` is an error, not `False`), unknown keys are errors, and missing path keys are errors (there are no default paths).

| Key | Type | Notes |
|---|---|---|
| `media_root`, `database_path`, `backup_root`, `quarantine_root`, `work_root`, `mutation_lock_path` | non-empty string | all required. `work_root` (staging) must be on the same filesystem as the files it will be installed beside |
| `batch_size_limit` | integer ≥ 1 | default 10; enforced by `TransactionEngine` |
| `enforce_payload_pcm_preservation` | boolean | must be `true`; `false` is rejected |
| `enforce_source_continuity` | boolean | must be `true`; `false` is rejected |
| `musicbrainz.rate_limit_seconds` | number ≥ 1.0 | reserved (no network code) |
| `musicbrainz.user_agent` | non-empty string | reserved |
| `musicbrainz.enable_acoustid_lookup` | boolean | reserved; `true` is rejected until the feature exists |
| `musicbrainz.enable_acoustid_submission` | boolean | `true` is rejected (prohibited) |
| `scoring.*` | numbers in range | validated but **not yet consumed** by the scorer |

Errors exit the CLI with status 2.
