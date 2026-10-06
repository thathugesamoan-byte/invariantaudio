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
Contributions that touch the mutation engine must preserve (and test) these invariants; see [docs/safety-model.md](docs/safety-model.md):
1. **Never transcode or clip audio**: tag writes must keep the compressed-payload and decoded-PCM hashes identical.
2. **Fail closed**: any error or discrepancy aborts and rolls back via the journal; never add a silent fallback.
3. **Never overwrite** an existing destination, backup or quarantine file; the original is removed only after the database commit.
4. **Local-first privacy**: no audio uploads, telemetry or un-sanitized external queries. Adding any network code requires updating `tests/unit/test_no_network_code.py`, `PRIVACY.md` and `docs/privacy-model.md` in the same change.
5. **No unqualified claims**: documentation may only state guarantees the code enforces and tests cover.

## Development Workflow
```bash
git clone https://github.com/thathugesamoan-byte/invariantaudio.git
cd invariantaudio
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"          # also requires ffmpeg on PATH
python -m pytest
flake8 src tests && mypy src
```
Tests use synthetic fixtures only. Never commit real media, databases, configuration files or logs.
