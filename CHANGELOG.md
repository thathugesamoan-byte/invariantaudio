# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-alpha] - 2026-08-16
### Added
- Initial public open-source release candidate of **InvariantAudio**.
- Modular Python architecture (`invariantaudio` package).
- Read-only default execution mode with CLI entrypoint `invariant-audio`.
- Single-process POSIX `flock` mutation lock manager (`MutationLock`).
- Source continuity verification tuple (`st_dev`, `st_ino`, `st_nlink`, size, SHA-256) and symlink rejection.
- Bit-exact audio payload and decoded PCM sample stream verification invariants.
- Multi-vector candidate identification scorer (Acoustic, Title, Artist, Album, Duration).
- Dual-approval decision governance (`AUTO_HIGH` and `HUMAN_V6` cryptographic manifests).
- Three-tier status classification (`TRUSTED`, `DAMAGED_BUT_PLAYABLE`, `INTEGRITY_EXCEPTION`).
- Safe quarantine isolation workflow with dual-copy backups.
- Comprehensive synthetic test fixture generator and regression suite.
- Generic YAML configuration system.
- Released under GNU General Public License v3.0 or later (GPL-3.0-or-later).
