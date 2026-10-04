# Known Limitations & Alpha Scope Boundaries

1. **POSIX File Locking**: Advisory `flock` locking is designed for Linux/POSIX environments.
2. **Network Egress Limits**: Synchronous 1.0s sleep interval between MusicBrainz queries ensures rate-limit compliance.
3. **No Lossy Repair**: Does not attempt to repair unparseable MP3 frames by clipping; damaged files are classified as `DAMAGED_BUT_PLAYABLE` or `quarantine/`.
