# SPDX-License-Identifier: GPL-3.0-or-later
"""
CLI Entry Point for InvariantAudio.
"""

import argparse
import sys
import sqlite3
from pathlib import Path
from invariantaudio.config import AppConfig, ConfigError
from invariantaudio.discovery.scanner import scan_directory_for_audio
from invariantaudio.integrity.audio_integrity import inspect_stream_health
from invariantaudio.reporting.audit import verify_master_balance
from invariantaudio.recovery.recovery_manager import SCHEMA_VERSION, init_database
from invariantaudio.transactions.engine import TransactionEngine

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="invariant-audio",
        description="Privacy-first, fail-closed music library integrity toolkit."
    )
    parser.add_argument("--config", "-c", default="config.yaml", help="Path to configuration file")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_scan = subparsers.add_parser("scan", help="List audio files in read-only mode")
    p_scan.add_argument("--dir", help="Override directory to scan")

    p_verify = subparsers.add_parser("verify", help="Verify audio stream integrity for a file (read-only, no config needed)")
    p_verify.add_argument("file", help="Audio file path to inspect")

    subparsers.add_parser("audit", help="Compare indexed paths with files on disk (read-only)")
    subparsers.add_parser("init-db", help=f"Initialize the SQLite catalog (schema v{SCHEMA_VERSION})")
    subparsers.add_parser("recover", help="Resolve interrupted transactions (modifies files; takes the mutation lock)")

    args = parser.parse_args()

    if args.command == "verify":
        fp = Path(args.file)
        if not fp.exists():
            print(f"File not found: {fp}", file=sys.stderr)
            sys.exit(1)
        status, details = inspect_stream_health(fp)
        print(f"File: {fp}")
        print(f"Stream Status: {status}")
        print(f"Diagnostics: {details}")
        return

    cfg_path = Path(args.config)
    try:
        cfg = AppConfig.from_yaml(cfg_path)
    except FileNotFoundError:
        print(f"Configuration file not found: {cfg_path}", file=sys.stderr)
        sys.exit(2)
    except ConfigError as e:
        print(f"Invalid configuration: {e}", file=sys.stderr)
        sys.exit(2)

    if args.command == "scan":
        target = Path(args.dir) if args.dir else cfg.media_root
        print(f"Scanning media directory: {target} (READ-ONLY)")
        files = scan_directory_for_audio(target)
        print(f"Found {len(files)} audio files.")
        for f in files[:10]:
            print(f"  - {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more files.")

    elif args.command == "init-db":
        cfg.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(cfg.database_path)
        try:
            init_database(conn)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        finally:
            conn.close()
        print(f"Initialized database schema v{SCHEMA_VERSION} at: {cfg.database_path}")

    elif args.command == "audit":
        if not cfg.database_path.exists():
            print(f"Database not found at {cfg.database_path}. Run init-db first.", file=sys.stderr)
            sys.exit(1)
        conn = sqlite3.connect(f"file:{cfg.database_path}?mode=ro", uri=True)
        bal = verify_master_balance(conn, cfg.media_root)
        conn.close()
        print("--- Library Balance Audit ---")
        print(f"  DB Tracks:        {bal['db_tracks']}")
        print(f"  Physical Files:   {bal['physical_media_files']}")
        print(f"  Unindexed Files:  {bal['unindexed_files']}")
        print(f"  Missing Files:    {bal['missing_files']}")
        print(f"  Balance Status:   {'BALANCED' if bal['is_balanced'] else 'DISCREPANCY'}")

    elif args.command == "recover":
        if not cfg.database_path.exists():
            print(f"Database not found at {cfg.database_path}. Run init-db first.", file=sys.stderr)
            sys.exit(1)
        conn = sqlite3.connect(cfg.database_path)
        try:
            engine = TransactionEngine(conn, cfg.backup_root, cfg.work_root, cfg.mutation_lock_path,
                                       media_root=cfg.media_root, batch_size_limit=cfg.batch_size_limit)
            results = engine.recover()
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        finally:
            conn.close()
        print(f"Resolved {len(results)} interrupted transaction(s).")
        for r in results:
            print(f"  - #{r['transaction_id']}: {r['previous_state']} -> {r['state']}")
        if any(r["state"] == "NEEDS_REVIEW" for r in results):
            sys.exit(3)

if __name__ == "__main__":
    main()
