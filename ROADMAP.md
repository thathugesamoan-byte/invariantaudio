# Roadmap

Items are checked only if implemented **and** tested in this repository.

## Version 0.1.0-alpha (current)
- [x] Journaled tag-write + relocate engine for `.mp3`/`.m4a` (no overwrite, same-filesystem staging, payload/PCM verification, source continuity, backup, post-commit source retirement).
- [x] Deterministic recovery of interrupted transactions (`recover`).
- [x] Read-only CLI: `scan`, `verify`, `audit`; `init-db`; `recover`.
- [x] Quarantine with backup and no overwrite (Python API, not journaled).
- [x] Strict configuration parsing.
- [x] Synthetic-fixture test suite.
- [x] Scoring, veto, manifest-hash and synthetic-ID helpers (library functions, not wired into any workflow).

## Version 0.2.0 (planned; not started)
- [ ] CLI subcommands for applying batches and quarantining files.
- [ ] Journaled quarantine.
- [ ] MusicBrainz/AcoustID lookups: opt-in, rate-limited, minimal-field queries, no fingerprint submission, with tests and privacy-doc updates.
- [ ] Candidate identification pipeline using the existing scorer and gates.
- [ ] Approval workflow (auto vs. human review packets) built on manifest hashing.
- [ ] Wire the `scoring:` configuration block into the scorer.

## Later (ideas)
- [ ] Interactive review UI.
- [ ] In-place retagging.
- [ ] Windows/macOS locking and filesystem support.
- [ ] Additional formats (FLAC, Opus, Ogg Vorbis, DSD) for tag writing.
- [ ] Optional integrations with other tagging or media-server tools.
