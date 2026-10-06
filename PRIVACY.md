# Privacy

InvariantAudio v0.1.0-alpha is local-only software.

- **No network access.** The package contains no network client code; a test asserts it imports no networking modules. It does not contact MusicBrainz, AcoustID, or any other service.
- **No telemetry, analytics, accounts, API keys or tokens.**
- **No audio, fingerprint or metadata leaves your machine.** `ffmpeg` and (optionally) `fpcalc` run locally.
- **What is stored locally:** a SQLite catalog containing local file paths, SHA-256 hashes, verification status and a transaction journal; backup copies of files the engine modifies; and staging copies while a transaction runs. Treat the database and backup directory as sensitive as the library itself.
- **Not covered:** the operating system, your filesystem and backup tooling, and the third-party programs you install (`ffmpeg`, `fpcalc`) are outside this project's control.

External metadata lookups are **planned, not implemented**. The constraints any future lookup must satisfy are listed in [docs/privacy-model.md](docs/privacy-model.md).
