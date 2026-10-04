# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import subprocess
import sys
import os
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
CLI_ENTRY = SRC_DIR / "invariantaudio/cli.py"
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

def test_cli_verify_smoke():
    mp3 = FIXTURES_DIR / "synthetic_test_track.mp3"
    env = {**dict(os.environ), "PYTHONPATH": str(SRC_DIR)}
    cmd = [sys.executable, str(CLI_ENTRY), "verify", str(mp3)]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert proc.returncode == 0
    assert "Stream Status:" in proc.stdout

def test_cli_init_db_and_audit(tmp_path):
    db_path = tmp_path / "test_cat.sqlite3"
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(f'''
media_root: "{tmp_path}/media"
database_path: "{db_path}"
backup_root: "{tmp_path}/backups"
quarantine_root: "{tmp_path}/quarantine"
work_root: "{tmp_path}/staging"
mutation_lock_path: "{tmp_path}/.lock"
''')

    (tmp_path / "media").mkdir()
    env = {**dict(os.environ), "PYTHONPATH": str(SRC_DIR)}

    # Run init-db
    proc1 = subprocess.run([sys.executable, str(CLI_ENTRY), "--config", str(cfg_file), "init-db"], capture_output=True, text=True, env=env)
    assert proc1.returncode == 0

    # Run audit
    proc2 = subprocess.run([sys.executable, str(CLI_ENTRY), "--config", str(cfg_file), "audit"], capture_output=True, text=True, env=env)
    assert proc2.returncode == 0
    assert "Balance Status:   BALANCED" in proc2.stdout
