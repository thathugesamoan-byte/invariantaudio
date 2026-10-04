# Damaged-Media Forensics & Stream Classification

## Status Hierarchy
- **`TRUSTED`**: 100% pristine, loss-free recording with zero decode warnings.
- **`DAMAGED_BUT_PLAYABLE`**: Structurally complete audio with minor bit-reservoir/sync warnings that decodes to complete, audible PCM streams. Native bitstreams are 100% preserved on disk.
- **`INTEGRITY_EXCEPTION`**: Audio with pre-existing dropped frames deferred for future replacement without destructive clipping.
- **`quarantine/`**: Severely damaged or unplayable files isolated into cold storage with dual backups.
