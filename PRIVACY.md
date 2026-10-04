# Local-First Privacy & Controlled Egress Architecture

## 1. Core Privacy Principles
1. **Local-First Processing**: 100% of audio decoding, acoustic fingerprinting (`fpcalc`), tag parsing (`mutagen`), and stream verification (`ffmpeg`) execute locally on your machine.
2. **Zero Raw Audio Egress**: Under no circumstances does InvariantAudio upload raw audio files, audio samples, or decoded PCM streams to any remote service.
3. **No Mandatory Accounts**: No registration, cloud accounts, API keys, or OAuth authentication tokens are required for core local operations.
4. **No Telemetry**: InvariantAudio contains zero analytics, tracking beacons, or telemetry daemons.

## 2. Controlled External Metadata Lookups
When external identification is enabled, InvariantAudio performs strictly controlled, read-only queries:
- **MusicBrainz**: Used for read-only metadata lookups via public HTTPS GET requests. Queries are sanitized to remove local file paths, hostnames, usernames, and IP addresses. Synchronous 1.0s rate limiting and an identified User-Agent header are enforced.
- **AcoustID**: Used strictly read-only to map local Chromaprint fingerprints to Recording MBIDs. **AcoustID fingerprint submission is strictly disabled.**
