# Contributing to InvariantAudio

Thank you for contributing to InvariantAudio!

## Developer Certificate of Origin (DCO)
InvariantAudio is an open-source project released under the **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.

To ensure all contributions are legally clean, InvariantAudio uses the **Developer Certificate of Origin (DCO v1.1)**. By signing off your commit with `git commit -s`, you certify that you have the legal right to submit the work under the project's GPL-3.0-or-later license.

### Developer Certificate of Origin 1.1
```
By making a contribution to this project, I certify that:
(a) The contribution was created in whole or in part by me and I have the right to submit it under the open source license indicated in the file; or
(b) The contribution is based upon previous work that, to the best of my knowledge, is covered under an appropriate open source license...
```

## Core Architectural Invariants
Any contribution modifying core engine logic must uphold our **Four Non-Negotiable Invariants**:
1. **Never transcode or clip audio**: Metadata tagging must preserve 100% bit-exact compressed audio payloads and decoded PCM sample streams.
2. **Fail-closed transactional safety**: Any error or discrepancy must abort and roll back immediately.
3. **Parent-only mutation ownership**: Consequential disk and database mutations must be executed directly by the single lock-owning process.
4. **Local-first privacy**: No audio uploads, telemetry, or un-sanitized external queries.

## Development Workflow
```bash
git clone https://github.com/thathugesamoan-byte/invariantaudio.git
cd invariantaudio
pip install -e ".[dev]"
pytest
```
