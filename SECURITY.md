# Security Policy

## Reporting a vulnerability
Report suspected vulnerabilities, data-loss bugs, or race conditions privately through GitHub Security Advisories on this repository. Do not open a public issue for them.

## Status
InvariantAudio is **alpha** software. Test it on copies. It has not had an independent security review.

## What the code enforces (tested)
- Existing destination files are never overwritten by the mutation engine or quarantine.
- The original file is removed only after the database commit and only if it is unchanged since it was bound (`st_dev`, `st_ino`, `st_nlink`, size, SHA-256; symlinks rejected).
- Tag writes are accepted only if compressed-payload and normalized decoded-PCM hashes are unchanged (scope and limits in [docs/safety-model.md](docs/safety-model.md)).
- Every transaction step is journaled; interrupted transactions are resolved deterministically by `recover` ([docs/recovery.md](docs/recovery.md)).
- Configuration is strictly typed; invalid or safety-disabling values abort.
- The package has no network code.

## What it does not protect against
- A privileged local attacker, other processes writing into the library, or a compromised `ffmpeg`.
- Advisory-lock bypass by programs that do not take the lock.
- Changes made in the short interval between the last continuity check and the source removal (the original bytes remain in the backup).
- Power-loss corruption (durability depends on hardware and mount options; not tested).
- Anything about the privacy or security of services not yet integrated (MusicBrainz/AcoustID are planned, not implemented).
