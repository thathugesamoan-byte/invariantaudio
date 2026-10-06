# Architecture (v0.1.0-alpha)

## Implemented
- **Inspection (read-only):** `discovery.scan_directory_for_audio`, `integrity.inspect_stream_health`, `reporting.verify_master_balance`.
- **Mutation:** `transactions.TransactionEngine` (journaled tag-write + relocate), `recovery` (schema, journal states, recovery), `quarantine.isolate_to_quarantine`.
- **Supporting pieces:** `transactions.source_continuity`, `transactions.lock`, `config`, `fsutil`.

The mutation engine is strictly sequential and single-process, takes an exclusive lock, and follows the order described in [transaction-model.md](transaction-model.md).

## Library building blocks that are not connected to a workflow
`evidence.scorer` (composite score and gates), `duplicates.veto` (title keyword comparison), `approvals.manifests` (canonical-JSON SHA-256 and synthetic-ID rejection), `identification.matcher.sanitize_search_query` (filename cleanup helper), and `discovery.compute_acoustic_fingerprint` (`fpcalc` wrapper). Nothing calls them in v0.1.0-alpha.

## Planned (not present)
Identification against MusicBrainz/AcoustID, candidate decisioning, approval workflows, and CLI commands that drive the engine. See [ROADMAP.md](../ROADMAP.md).
