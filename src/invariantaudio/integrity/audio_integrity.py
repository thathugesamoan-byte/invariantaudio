# SPDX-License-Identifier: GPL-3.0-or-later
"""
Audio Stream & Payload Integrity Module.
Extracts compressed audio payloads and decoded PCM sample stream hashes.
"""

import hashlib
import subprocess
from pathlib import Path
from typing import Tuple

def compute_file_sha256(path: str | Path) -> str:
    """Compute the whole-file SHA-256 hash."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def compute_compressed_audio_payload_sha256(path: str | Path) -> str:
    """
    Extract the raw compressed audio frames (excluding container tags)
    and compute their SHA-256 digest using ffmpeg streamcopy hash format.
    """
    cmd = [
        "ffmpeg", "-nostdin", "-v", "error",
        "-i", str(path),
        "-map", "0:a:0",
        "-c", "copy",
        "-f", "hash", "-hash", "sha256", "-"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for line in proc.stdout.splitlines():
            if "SHA256=" in line:
                return line.split("SHA256=", 1)[1].strip().lower()
            elif "=" in line:
                return line.split("=", 1)[1].strip().lower()
        raise RuntimeError("ffmpeg output did not contain SHA256 payload hash")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Payload extraction failed for {path}: {e.stderr}")

def compute_decoded_pcm_sha256(path: str | Path) -> str:
    """
    Decode audio into normalized 16-bit 44.1kHz stereo linear PCM samples
    and compute their SHA-256 digest.
    """
    cmd = [
        "ffmpeg", "-nostdin", "-v", "error",
        "-i", str(path),
        "-map", "0:a:0",
        "-f", "s16le",
        "-ac", "2",
        "-ar", "44100",
        "-"
    ]
    h = hashlib.sha256()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdout is not None
        while chunk := proc.stdout.read(65536):
            h.update(chunk)
        _, stderr = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"PCM decode failed for {path}: {stderr.decode('utf-8', errors='ignore')}")
        return h.hexdigest()
    except Exception as e:
        raise RuntimeError(f"PCM extraction error on {path}: {e}")

def inspect_stream_health(path: str | Path) -> Tuple[str, str]:
    """
    Inspect an audio file using ffmpeg full decode.
    Returns (status, diagnostic_details).
    Statuses:
      - 'TRUSTED': 0 decode warnings, clean bitstream.
      - 'DAMAGED_BUT_PLAYABLE': Minor bit-reservoir/sync warnings, complete PCM decode.
      - 'INTEGRITY_EXCEPTION': Pre-existing dropped sync frames.
      - 'UNUSABLE': Fatal stream corruption / zero audio.
    """
    cmd = [
        "ffmpeg", "-nostdin", "-v", "warning",
        "-i", str(path),
        "-f", "null", "-"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    stderr = proc.stderr.strip()
    
    if proc.returncode != 0:
        return "UNUSABLE", stderr
    
    if not stderr:
        return "TRUSTED", "Pristine decode with zero warnings"
    
    if "bit reservoir underflow" in stderr or "sync error" in stderr:
        if "partial file" in stderr or "Invalid data found" in stderr:
            return "INTEGRITY_EXCEPTION", stderr
        return "DAMAGED_BUT_PLAYABLE", stderr
        
    return "DAMAGED_BUT_PLAYABLE", stderr
