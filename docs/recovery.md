# Crash Recovery (v0.1.0-alpha)

## What exists
`recovery.recover_interrupted_transactions` (also `TransactionEngine.recover()` and the CLI command `invariant-audio --config config.yaml recover`) resolves every in-flight transaction in `production_transactions`. It runs under the mutation lock. Resolution is a function of the journal state and of what is observably on disk; it never re-writes audio or tags.

| Journal state when interrupted | Recovery action | Result state |
|---|---|---|
| `PLANNED`, `STAGED` | remove the staging file (only a plain file inside the staging root); a pre-existing target is left untouched | `ABORTED` |
| `VERIFIED`, `INSTALLED` | remove staging; if the target is provably ours (hard link to the staging file, or SHA-256 equals the journaled staged hash) and the source still exists, remove the target. A target that is not provably ours is left alone | `ROLLED_BACK` / `ABORTED` / `NEEDS_REVIEW` |
| `COMMITTED` | if the target still has the journaled hash: unlink the source only if its SHA-256 equals the journaled source hash (or it is already gone) | `COMPLETED` / `NEEDS_REVIEW` |

Why this is safe: the source file is never removed before the `COMMITTED` state is durable, so every earlier state can be rolled back without data loss, and a `COMMITTED` state can be rolled forward. `NEEDS_REVIEW` is terminal: recovery will not guess; the backup in `backup_root` and the journal `detail` column describe what was found. `recover` exits with status 3 if any transaction needs review.

Backups from aborted or rolled-back transactions are kept (never deleted automatically).

## What does not exist
- No background scanner or automatic recovery on start-up; `apply_batch` refuses to run until recovery has been invoked (`UNRESOLVED_TRANSACTIONS`).
- No journal or recovery for `quarantine.isolate_to_quarantine` (it never overwrites and leaves the original in place on failure, but an interruption between steps needs manual review).
- No automatic restore from backups; backups are plain copies you restore yourself.
- No tool to resolve `NEEDS_REVIEW` entries; that is a manual decision.

## Test evidence
Failure injection at each boundary (before/after staging, after tag write, around install, DB insert failure, DB commit failure), simulated hard stops at every in-flight state, and a real `SIGKILL` of a child process, each followed by recovery, are in `tests/integration/test_engine_failure_and_recovery.py`. Power-loss behavior is not tested.
