# SPDX-License-Identifier: GPL-3.0-or-later
"""
Filesystem discovery and acoustic fingerprint harvest.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".aac", ".ogg", ".opus", ".wav", ".alac"}

def scan_directory_for_audio(root: str | Path) -> List[Path]:
    root_path = Path(root)
    found = []
    for dirpath, _, filenames in os.walk(root_path):
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTENSIONS:
                found.append(Path(dirpath) / f)
    return sorted(found)

def compute_acoustic_fingerprint(path: str | Path) -> Dict[str, Any]:
    """Invoke fpcalc locally to generate Chromaprint string and duration."""
    cmd = ["fpcalc", "-json", "-length", "120", str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    import json
    return json.loads(proc.stdout)
