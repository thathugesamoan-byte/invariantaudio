# InvariantAudio: System Architecture & Component Model

The system follows an asymmetric pipeline design:
- **Upstream (Discovery & Identification)**: Read-only, highly parallelizable, local-first. Extracts acoustic fingerprints via `fpcalc`, parses container tags via `mutagen`, queries MusicBrainz, and scores candidates.
- **Midstream (Veto & Decision Gateway)**: Evaluates candidates against duration gates, score margins, and live-veto rules. Partitions candidates into `AUTO_HIGH` or `HUMAN_V6`.
- **Downstream (Transactional Mutation Engine)**: Strictly sequential, single-process, fail-closed. Acquires exclusive `flock`, verifies source continuity, creates pre-move backups, writes tags in staging, validates bit-exact payload/PCM hashes, performs atomic `os.replace`, and commits SQLite transactions.
