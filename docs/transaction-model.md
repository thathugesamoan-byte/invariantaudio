# Transaction Engine Model (v0.1.0-alpha)

This document states exactly what `TransactionEngine` does and does not guarantee.

## Scope
Metadata-only tag writes (`.mp3`, `.m4a`) combined with relocating the file. Any other extension is rejected (`UNSUPPORTED_MEDIA_EXTENSION`), as are unknown tag keys (`UNSUPPORTED_TAG`) and a target extension different from the source's.

## It is not ACID across the file system and SQLite
SQLite and the file system are separate systems; no mechanism makes a file move and a database commit one atomic unit. What the engine provides instead:

- **SQLite:** the `tracks` insert and the journal state change to `COMMITTED` are executed in **one** SQLite transaction (`BEGIN IMMEDIATE` ... `COMMIT`). Either both persist or neither does.
- **File system:** each step is individually atomic (`os.link`, `os.unlink`), and the order of steps is chosen so that the original is the last thing removed.
- **Journal:** every step is recorded in `production_transactions` *before* it is performed. After a crash, [recovery](recovery.md) reads the journal and resolves the transaction deterministically.

## States
`PLANNED` → `STAGED` → `VERIFIED` → `INSTALLED` → `COMMITTED` → `COMPLETED`; failures end in `ABORTED` (nothing installed), `ROLLED_BACK` (installed target removed) or `NEEDS_REVIEW` (human decision required). `PLANNED` through `COMMITTED` are "in flight"; `apply_batch` refuses to start while any in-flight transaction exists (`UNRESOLVED_TRANSACTIONS`) until recovery has run.

## Order of operations
1. **Pre-journal checks (no side effects on failure):** extension/tag validation; media-root containment (if `media_root` is given); source must be a regular, non-symlink file; target classification (below); target not already indexed; staging and target on the same device; source stream health not `UNUSABLE`; source payload and PCM hashes computed.
2. Journal `PLANNED` (paths recorded before any file is created).
3. Backup copy and staging copy, each created with `O_EXCL` (never overwrites) and checked against the source's bound SHA-256. → `STAGED`
4. Write tags in the staging copy only; recompute payload and PCM hashes; both must equal the source's. → `VERIFIED`
5. **Revalidate source continuity**, then install: `os.link(staging, target)`, which fails if the target exists; check the installed bytes; unlink staging. → `INSTALLED`
6. One SQLite transaction inserts the `tracks` row and sets `COMMITTED`.
7. Revalidate source continuity again; if unchanged, unlink the source. → `COMPLETED`. If the source changed or cannot be removed it is **kept** and the result status is `COMMITTED_SOURCE_RETAINED`; recovery completes or flags it later.

A failure in steps 2 to 6 triggers the same rollback code that recovery uses. A database failure (insert or commit) therefore leaves the source untouched, the target removed, and the journal at `ROLLED_BACK`. If `COMMIT` reports an error but the journal shows `COMMITTED`, the engine treats the transaction as committed.

## Target collision policy
The engine never replaces an existing path. `classify_target` distinguishes, and the engine refuses all but `ABSENT`:

| Class | Meaning |
|---|---|
| `ABSENT` | nothing at the path and no Unicode/case-equivalent sibling |
| `IS_SOURCE` | target path equals source path (in-place retagging is not supported in v0.1.0-alpha) |
| `ALIASES_SOURCE` | different path, same inode as the source |
| `EXISTS_IDENTICAL` | different file with the same SHA-256 as the source |
| `EXISTS_DIFFERENT` | different file with different content |
| `EXISTS_NOT_REGULAR` | symlink (including dangling) or directory |
| `NAME_COLLISION` | a sibling that is equivalent under Unicode NFC normalization and case folding (applies to every path component) |

Target paths are NFC-normalized; source paths are never rewritten. Because installation is a hard link, a file that appears at the target after the pre-check still cannot be overwritten (`TARGET_EXISTS_AT_INSTALL`).

## Filesystem boundary
Staging and target must be on the same device. This is checked before anything is created (`CROSS_FILESYSTEM_STAGING`) and again if `os.link` returns `EXDEV`. The file system must support hard links; where it does not (e.g. FAT/exFAT, some network mounts), installation fails closed (`INSTALL_FAILED`). Nothing here depends on `os.replace` being atomic across devices because `os.replace` is not used on the target.

## Locking
`apply_batch` and `recover` hold an exclusive advisory `flock` on the lock file. This coordinates cooperating InvariantAudio processes only; it does not stop other programs from touching your files.

## Batch behavior
At most `batch_size_limit` proposals (default 10) per call; all proposals are validated before the first mutation; processing is sequential and stops at the first failure. Earlier proposals stay committed and are listed in `TransactionError.completed`.

## What is not guaranteed
- **Power-loss durability.** Staged/backup files and directories are `fsync`ed and SQLite uses its default synchronous mode, but durability still depends on hardware and mount options. Process-kill recovery is tested (including a real `SIGKILL`); power-loss recovery is not tested.
- **TOCTOU elimination.** Continuity checks detect changes; they cannot prevent one that happens after the final check and before the source `unlink`. In that narrow window an edit to the source would be lost from the library (the pre-transaction bytes remain in the backup).
- **Protection from a privileged local actor,** another process that writes into the library, or damage to the backup/staging directories.
- **Audio equivalence beyond the hashes.** See [safety-model.md](safety-model.md).
- **Cleanup of directories** created for the target path after a rollback; empty directories may remain.
