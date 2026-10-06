# SPDX-License-Identifier: GPL-3.0-or-later
"""
Example: apply one tag-write + relocate transaction through the Python API.

    python examples/basic_usage.py SOURCE.mp3 TARGET.mp3

WARNING: this really moves SOURCE to TARGET (after a backup). Run it on a copy.
It uses a scratch database, backup and staging directory next to TARGET's
parent so staging stays on the same filesystem.
"""

import sqlite3
import sys
from pathlib import Path

from invariantaudio.recovery.recovery_manager import init_database
from invariantaudio.transactions.engine import TransactionEngine, TransactionError


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, tgt = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    work = tgt.parent / ".invariantaudio-example"
    work.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(work / "catalog.sqlite3")
    init_database(conn)
    engine = TransactionEngine(conn, work / "backups", work / "staging", work / "mutation.lock")
    try:
        result = engine.apply_batch([{
            "source_path": str(src),
            "target_path": str(tgt),
            "tags": {"title": "Example Title", "artist": "Example Artist"},
        }])[0]
    except TransactionError as e:
        print(f"Refused or rolled back: {e.code}: {e.detail}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    print(result["status"], result["target_path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
