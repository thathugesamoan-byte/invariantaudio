# Approval Governance (planned; not implemented in v0.1.0-alpha)

No approval workflow exists in this release: nothing produces proposals automatically, there is no `AUTO`/`HUMAN` queue, no review-sheet generation, and no replay or staleness protection for approval files. `TransactionEngine.apply_batch` simply executes the proposals its caller passes in.

What exists as building blocks:
- `approvals.compute_manifest_hash(data)`: SHA-256 of canonical JSON (sorted keys, compact separators). It is an integrity digest, **not** a signature; it has no key and authenticates nothing by itself.
- `approvals.validate_synthetic_id_rejection(mbid)`: raises on placeholder UUID patterns (prefix `b1b1c1d1` or a run of ten zeros).

The intended design (planned): proposals that clear strict score/margin gates could be auto-approved; everything else would require a human to review a generated packet bound to a manifest hash. Treat this as a design direction only.
