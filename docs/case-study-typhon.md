# Historical Deployment Record (Typhon)

> **Provenance and scope — read first.**
> The figures below come from the operator's own records of a deployment of an **earlier, private implementation** of this approach on a personal music library. They are reported as **historical evidence only**.
> - They are **not reproduced by this repository** and cannot be re-derived from it: the library, its database and its logs are private and are not published, and this release ships synthetic test fixtures only.
> - The earlier implementation had an identification pipeline (fingerprint lookup, scoring, automatic and human approval phases) that **does not exist in v0.1.0-alpha** (see the README table and [ROADMAP.md](../ROADMAP.md)).
> - No claim is made that v0.1.0-alpha would have produced these results, or that it is "production-proven". What the public suite demonstrates is limited to the synthetic tests in `tests/`.

## 1. Context
A personal collection of roughly 2,000 audio files (MP3, M4A, FLAC) on a dedicated Linux server, with inconsistent tags, fragmented folders, duplicates and unindexed files.

## 2. Phases as reported by the operator (earlier tooling)
1. **Automatic phase:** 688 tracks that met the score gates (top ≥ 0.80, runner-up ≤ 0.20, margin ≥ 0.60) were applied in 69 small batches; the operator reports no false positives.
2. **Human adjudication and duplicates:** 424 tracks reviewed across 8 review sets; 50 duplicate/version cases resolved (3 bit-identical duplicates removed, 46 legitimate versions tagged).
3. **Holdouts:** 225 tracks resolved through further review packets.
4. **Census:** a final `ffmpeg` decode census of 190 files classified 159 as `DAMAGED_BUT_PLAYABLE`, deferred 1 exception, and isolated 30 non-canonical files with backups.

Duplicate deletion, review packets and the automatic/human phases above are **not** features of this release.

## 3. Reported historical metrics (operator records, unverified here)

| Category | Count |
|---|---:|
| Tracks in the final catalog | 2,003 |
| `TRUSTED` | 1,843 |
| `DAMAGED_BUT_PLAYABLE` | 159 |
| `INTEGRITY_EXCEPTION` (deferred) | 1 |
| Unindexed files on disk at end | 0 |
| Committed transactions | 1,952 |
| — human-approved | 1,243 |
| — automatically approved | 688 |
| Quarantined files / backups | 30 / 30 |

The operator reports that payload and PCM hashes matched in every committed transaction. In this repository the equivalent check is an enforced precondition of each transaction ([safety-model.md](safety-model.md)), tested on synthetic files.
