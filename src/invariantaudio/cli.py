# SPDX-License-Identifier: GPL-3.0-or-later
"""
CLI Entry Point for InvariantAudio.
"""

import argparse
import sys
import sqlite3
from pathlib import Path
from invariantaudio.config import AppConfig
from invariantaudio.discovery.scanner import scan_directory_for_audio
from invariantaudio.integrity.audio_integrity import inspect_stream_health
from invariantaudio.reporting.audit import verify_master_balance
from invariantaudio.recovery.recovery_manager import init_database

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="invariant-audio",
        description="Privacy-First, Fail-Closed Music Library Remediation Framework."
    )
    parser.add_argument("--config", "-c", default="config.yaml", help="Path to configuration file")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan (Read-Only)
    p_scan = subparsers.add_parser("scan", help="Scan media directory in read-only mode")
    p_scan.add_argument("--dir", help="Override directory to scan")

    # verify (Read-Only)
    p_verify = subparsers.add_parser("verify", help="Verify audio stream integrity for a file")
    p_verify.add_argument("file", help="Audio file path to inspect")

    # audit (Read-Only)
    p_audit = subparsers.add_parser("audit", help="Run master library inventory balance audit")

    # init-db (Setup)
    p_init = subparsers.add_parser("init-db", help="Initialize SQLite catalog schema v6")

    args = parser.parse_args()

    # Load configuration
    cfg_path = Path(args.config)
    if cfg_path.exists():
        cfg = AppConfig.from_yaml(cfg_path)
    else:
        cfg = AppConfig(
            media_root=Path("/tmp/invariantaudio/media"),
            database_path=Path("/tmp/invariantaudio/catalog.sqlite3"),
            backup_root=Path("/tmp/invariantaudio/backups"),
            quarantine_root=Path("/tmp/invariantaudio/quarantine"),
            work_root=Path("/tmp/invariantaudio/staging"),
            mutation_lock_path=Path("/tmp/invariantaudio/.invariant_audio.lock"),
        )

    if args.command == "scan":
        target = Path(args.dir) if args.dir else cfg.media_root
        print(f"Scanning media directory: {target} (READ-ONLY)")
        files = scan_directory_for_audio(target)
        print(f"Found {len(files)} audio files.")
        for f in files[:10]:
            print(f"  - {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more files.")

    elif args.command == "verify":
        fp = Path(args.file)
        if not fp.exists():
            print(f"File not found: {fp}", file=sys.stderr)
            sys.exit(1)
        status, details = inspect_stream_health(fp)
        print(f"File: {fp}")
        print(f"Stream Status: {status}")
        print(f"Diagnostics: {details}")

    elif args.command == "init-db":
        cfg.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(cfg.database_path)
        init_database(conn)
        conn.close()
        print(f"Initialized database schema v6 at: {cfg.database_path}")

    elif args.command == "audit":
        if not cfg.database_path.exists():
            print(f"Database not found at {cfg.database_path}. Run init-db first.", file=sys.stderr)
            sys.exit(1)
        conn = sqlite3.connect(f"file:{cfg.database_path}?mode=ro", uri=True)
        bal = verify_master_balance(conn, cfg.media_root)
        conn.close()
        print("--- Master Library Balance Audit ---")
        print(f"  DB Tracks:        {bal['db_tracks']}")
        print(f"  Physical Files:   {bal['physical_media_files']}")
        print(f"  Unindexed Files:  {bal['unindexed_files']}")
        print(f"  Balance Status:   {'BALANCED' if bal['is_balanced'] else 'DISCREPANCY'}")

if __name__ == "__main__":
    main()
