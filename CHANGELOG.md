# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html); the Python package version `0.1.0a1` is the PEP 440 form of `0.1.0-alpha`.

## [0.1.0-alpha] - 2026-10-05
### Added
- `invariantaudio` package and `invariant-audio` CLI: `init-db`, `scan`, `verify`, `audit`, `recover`.
- `TransactionEngine`: journaled tag-write + relocate for `.mp3`/`.m4a` with payload and decoded-PCM verification, source-continuity revalidation, pre-move backups, same-filesystem staging and post-commit source retirement.
- Transaction journal (`production_transactions`, schema v7) and deterministic recovery of interrupted transactions.
- Target collision policy (`classify_target`): refuses existing different, identical, aliased, symlinked and Unicode/case-equivalent destinations.
- Source-continuity binding over `(st_dev, st_ino, st_nlink, size, SHA-256)`, opened with `O_NOFOLLOW`.
- Quarantine with collision-safe backup and quarantine names (Python API).
- Strict configuration parser (no type coercion, unknown keys rejected, safety flags cannot be disabled).
- Path-level library audit.
- Scoring, version-keyword veto, manifest-hash and synthetic-ID helper functions (not wired into a workflow).
- Complete GNU GPL v3 text in `LICENSE`; `GPL-3.0-or-later` as the license expression.
- CI: tests on Python 3.10–3.12, `pyflakes`-class lint, `mypy`, and a full-history `gitleaks` scan.

### Not included (planned)
MusicBrainz/AcoustID access, the identification pipeline, approval workflows, CLI commands for applying batches or quarantining, deduplication. See [ROADMAP.md](ROADMAP.md).
