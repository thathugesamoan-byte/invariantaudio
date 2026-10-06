# Safety Model (v0.1.0-alpha)

Each statement below is either enforced by code and covered by tests, or is explicitly marked as a limit.

## Enforced invariants
1. **No overwrite of an existing destination.** Installation uses `os.link`; backups and staging files are created with `O_EXCL`; quarantine uses a hard link. Policy and error codes: [transaction-model.md](transaction-model.md).
2. **Original removed last.** The source file is unlinked only after the SQLite commit that records the new track, and only if source continuity still holds.
3. **Source continuity.** A binding records `(st_dev, st_ino, st_nlink, st_size, SHA-256)` of a regular, non-symlink file (opened with `O_NOFOLLOW`). It is re-verified immediately before the target is installed and again before the source is removed. A change to any element (replacement, modification, hard-link count, swap to a symlink) fails the transaction closed. Backup and staging copies are also checked against the bound SHA-256.
4. **Payload and decoded-PCM equality.** Before and after the tag write, two SHA-256 hashes must be identical:
   - *compressed payload:* `ffmpeg -map 0:a:0 -c copy -f hash` (first audio stream's packets, container metadata excluded);
   - *decoded PCM:* `ffmpeg -map 0:a:0 -f s16le -ac 2 -ar 44100` (the decode is **normalized** to 16-bit, 44.1 kHz, stereo before hashing).
   Scope limits: only the first audio stream is hashed; non-audio streams (e.g. embedded artwork) and container structure are not compared; the PCM hash is of the normalized decode, not the native sample format.
5. **Journal-before-action and deterministic recovery.** See [recovery.md](recovery.md).
6. **Single mutator at a time.** An exclusive advisory `flock` is held for `apply_batch` and `recover`. It is advisory and covers cooperating InvariantAudio processes only.
7. **Same-filesystem staging** (device check plus `EXDEV` handling).
8. **Fail-closed configuration.** Invalid, mistyped, unknown or safety-disabling settings abort; there are no silent fallbacks. See [configuration.md](configuration.md).
9. **No network code** in the package (asserted by a test). See [privacy-model.md](privacy-model.md).

## Design constraint (not a test-verified property of all code)
- **Parent-only mutation.** All mutation happens in the single process holding the lock. The package spawns `ffmpeg`/`fpcalc` only for read-only hashing, decoding and fingerprinting.

## Explicit non-guarantees
- No protection from a privileged local attacker, malicious `ffmpeg`, or other programs modifying the library.
- No guarantee of durability across power loss.
- A change made to the source in the interval between the final continuity check and the source `unlink` is not detected (the pre-transaction content remains in the backup).
- `flock` does not protect against processes that do not take the lock.
- Bit-exactness claims apply to the hashes and scope described in item 4, for the supported operation (tag write on `.mp3`/`.m4a`).
