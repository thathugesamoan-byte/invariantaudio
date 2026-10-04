# Security Policy

## Reporting a Vulnerability
We take the security, privacy, and integrity of media libraries very seriously. If you discover a security vulnerability, Time-Of-Check to Time-Of-Use (TOCTOU) race condition, or potential data corruption bug, please report it responsibly.

Please DO NOT create a public issue for sensitive security vulnerabilities. Instead, report security advisories privately via GitHub Security Advisories.

## Security Architecture & Implemented Invariants
InvariantAudio is engineered around a **fail-closed, transactional safety model**:
1. **Advisory File Locking (`flock`)**: All mutating operations acquire an exclusive lock on `.invariant_audio.lock` to prevent concurrency races.
2. **Parent-Only Mutation Invariant**: Child worker subprocesses are restricted to read-only inspection; all file writes and database updates are performed directly by the parent process.
3. **Source Continuity Tuple Verification**: Files are bound to their device (`st_dev`), inode (`st_ino`), link count (`st_nlink`), size, and SHA-256 hash to prevent symlink or hardlink substitution attacks.
4. **Bit-Exact Audio Preservation**: Audio payloads and decoded PCM sample streams must match bit-for-bit before and after metadata writes.
5. **Fail-Closed Execution**: Any discrepancy, unhandled exception, or hash mismatch halts execution immediately and rolls back staged files.
