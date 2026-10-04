# Safety Model & Architectural Invariants

## The Four Core Safety Invariants
1. **Parent-Only Mutation Invariant**: Consequential file and database writes are executed directly by the supervisor process holding `.invariant_audio.lock`. Child worker subprocesses are restricted to read-only queries.
2. **Source Continuity Invariant**: Physical file identity `(st_dev, st_ino, st_nlink, size, sha256)` is validated immediately before mutation and retirement, eliminating TOCTOU races.
3. **Payload & Decoded PCM Invariant**: Compressed audio frames and decoded 16-bit 44.1kHz PCM samples must match bit-for-bit before and after tagging.
4. **Fail-Closed Rollback Invariant**: Any unhandled error or discrepancy halts execution and restores pre-move backups.
