# Privacy Model (v0.1.0-alpha)

See [PRIVACY.md](../PRIVACY.md) for the policy statement. Summary of what is true of this release:

1. **No network code.** The package imports no networking module and starts no network client. `tests/unit/test_no_network_code.py` fails if one is added without updating this document.
2. **Local processing.** `ffmpeg` (decode/hash) and, if you call it, `fpcalc` (fingerprint) run as local subprocesses. No audio, fingerprint, path or metadata leaves the machine.
3. **No telemetry, no accounts, no API keys.**
4. **Disk writes** are limited to the directories you configure (`backup_root`, `work_root`, `quarantine_root`, `database_path`, the lock file) and the target paths of a batch. The database stores local file paths and hashes.

## Design constraints for future network features (not implemented)
Any future MusicBrainz or AcoustID integration must: be opt-in; send only the minimum fields needed (never file paths, host or user names); honor `musicbrainz.rate_limit_seconds >= 1.0` and send an identified User-Agent; never submit fingerprints (`enable_acoustid_submission` must remain false); and ship with tests and an update of this document. The configuration keys exist and are validated now so that the contract is fixed, but `enable_acoustid_lookup: true` is rejected until the feature exists.

`identification.matcher.sanitize_search_query` only strips bracketed text and a leading track number from a string. It is **not** a privacy filter and is not used for any request.
