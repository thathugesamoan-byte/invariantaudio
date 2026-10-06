# SPDX-License-Identifier: GPL-3.0-or-later
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from helpers import sha256_of
from invariantaudio.transactions.engine import TransactionEngine

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
CLI = [sys.executable, "-m", "invariantaudio.cli"]


def run(*args):
    return subprocess.run([*CLI, *args], capture_output=True, text=True)


def write_cfg(tmp_path, extra=""):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(f'''
media_root: "{tmp_path}/media"
database_path: "{tmp_path}/test_cat.sqlite3"
backup_root: "{tmp_path}/backups"
quarantine_root: "{tmp_path}/quarantine"
work_root: "{tmp_path}/staging"
mutation_lock_path: "{tmp_path}/.lock"
{extra}''')
    (tmp_path / "media").mkdir(exist_ok=True)
    return cfg


def test_cli_verify_smoke():
    proc = run("verify", str(FIXTURES_DIR / "synthetic_test_track.mp3"))
    assert proc.returncode == 0, proc.stderr
    assert "Stream Status:" in proc.stdout


def test_cli_verify_needs_no_config(tmp_path):
    proc = subprocess.run([*CLI, "verify", str(FIXTURES_DIR / "synthetic_test_track.mp3")],
                          capture_output=True, text=True, cwd=tmp_path)
    assert proc.returncode == 0


def test_cli_init_db_scan_and_audit(tmp_path):
    cfg = write_cfg(tmp_path)
    shutil.copy2(FIXTURES_DIR / "synthetic_test_track.mp3", tmp_path / "media" / "a.mp3")
    assert run("--config", str(cfg), "init-db").returncode == 0
    scan = run("--config", str(cfg), "scan")
    assert scan.returncode == 0 and "Found 1 audio files." in scan.stdout
    audit = run("--config", str(cfg), "audit")
    assert audit.returncode == 0
    assert "Unindexed Files:  1" in audit.stdout and "DISCREPANCY" in audit.stdout


def test_cli_audit_balanced_when_empty(tmp_path):
    cfg = write_cfg(tmp_path)
    run("--config", str(cfg), "init-db")
    out = run("--config", str(cfg), "audit")
    assert out.returncode == 0 and "Balance Status:   BALANCED" in out.stdout


def test_cli_missing_config_fails_closed(tmp_path):
    proc = run("--config", str(tmp_path / "nope.yaml"), "scan")
    assert proc.returncode == 2 and "not found" in proc.stderr


def test_cli_invalid_config_fails_closed(tmp_path):
    cfg = write_cfg(tmp_path, 'enforce_source_continuity: "false"\n')
    proc = run("--config", str(cfg), "scan")
    assert proc.returncode == 2 and "boolean" in proc.stderr


def test_cli_init_db_refuses_other_schema_version(tmp_path):
    cfg = write_cfg(tmp_path)
    conn = sqlite3.connect(tmp_path / "test_cat.sqlite3")
    conn.execute("PRAGMA user_version = 6")
    conn.commit()
    conn.close()
    proc = run("--config", str(cfg), "init-db")
    assert proc.returncode == 1 and "UNSUPPORTED_SCHEMA_VERSION" in proc.stderr


def test_cli_recover_resolves_interrupted_transaction(tmp_path, monkeypatch):
    cfg = write_cfg(tmp_path)
    assert run("--config", str(cfg), "init-db").returncode == 0
    src = tmp_path / "media" / "raw.mp3"
    shutil.copy2(FIXTURES_DIR / "synthetic_test_track.mp3", src)
    src_sha = sha256_of(src)
    conn = sqlite3.connect(tmp_path / "test_cat.sqlite3")
    eng = TransactionEngine(conn, tmp_path / "backups", tmp_path / "staging", tmp_path / ".lock",
                            media_root=tmp_path / "media")

    class Crash(BaseException):
        pass

    def crash(*a, **k):
        raise Crash()

    monkeypatch.setattr(eng, "_commit_track", crash)
    try:
        eng.apply_batch([{"source_path": str(src), "target_path": str(tmp_path / "media" / "A" / "t.mp3"),
                          "tags": {"title": "T"}}])
    except Crash:
        pass
    conn.close()
    proc = run("--config", str(cfg), "recover")
    assert proc.returncode == 0, proc.stderr
    assert "INSTALLED -> ROLLED_BACK" in proc.stdout
    assert sha256_of(src) == src_sha and not (tmp_path / "media" / "A" / "t.mp3").exists()
