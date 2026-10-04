# Local-First Privacy & Controlled Egress Architecture

1. **Local Audio Processing**: Acoustic fingerprinting (`fpcalc`) and stream decoding (`ffmpeg`) run 100% locally.
2. **Sanitized Query Egress**: External MusicBrainz HTTP GET requests contain only sanitized search tokens; local file paths, hostnames, usernames, and IP addresses are stripped.
3. **Prohibited Submissions**: AcoustID fingerprint submissions and cloud audio uploads are strictly disabled.
4. **No Telemetry**: Zero background tracking daemons or analytics beacons.
