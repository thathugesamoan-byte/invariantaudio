# Project Roadmap

## Version 0.1.0-alpha (Current)
- [x] Extraction of proven core architecture into clean `invariantaudio` Python package.
- [x] Full test suite using synthetic audio fixtures.
- [x] Read-only candidate scanning and scoring CLI (`invariant-audio scan`, `verify`, `audit`, `init-db`).
- [x] Transactional batch mutation with payload/PCM verification in programmatic API.
- [x] Quarantine and recovery state machine.

## Version 0.2.0 (Near-Term)
- [ ] Interactive terminal UI (TUI) for human review packet adjudication using Textual/Rich.
- [ ] CLI integration for batch apply, quarantine, and recovery subcommands.
- [ ] Local SQLite caching for offline MusicBrainz lookups.
- [ ] Plugin architecture for alternative media servers (Navidrome, Plex, Emby).

## Version 0.3.0 (Long-Term)
- [ ] Optional integration plugin for Beets (`beet-safewrite`).
- [ ] Multi-platform Windows/macOS file locking adaptation (currently POSIX-only).
- [ ] Extended format support (Opus, Vorbis OGG, DSF/DFF Direct Stream Digital).
