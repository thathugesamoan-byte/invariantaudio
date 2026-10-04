# SPDX-License-Identifier: GPL-3.0-or-later
"""
Configuration management and validation for InvariantAudio.
"""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional

@dataclass
class MusicBrainzConfig:
    rate_limit_seconds: float = 1.0
    user_agent: str = "InvariantAudio/0.1.0 ( https://github.com/invariantaudio/invariantaudio )"
    enable_acoustid_lookup: bool = True
    enable_acoustid_submission: bool = False  # Strictly False for privacy

@dataclass
class ScoringConfig:
    min_auto_approval_score: float = 0.80
    max_auto_approval_runner_up: float = 0.20
    min_auto_approval_margin: float = 0.60
    duration_tolerance_seconds: float = 3.0
    min_acoustic_overlap_frames: int = 150

@dataclass
class AppConfig:
    media_root: Path
    database_path: Path
    backup_root: Path
    quarantine_root: Path
    work_root: Path
    mutation_lock_path: Path
    batch_size_limit: int = 10
    enforce_payload_pcm_preservation: bool = True
    enforce_source_continuity: bool = True
    musicbrainz: MusicBrainzConfig = field(default_factory=MusicBrainzConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AppConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        mb_data = data.get("musicbrainz", {})
        mb_conf = MusicBrainzConfig(
            rate_limit_seconds=float(mb_data.get("rate_limit_seconds", 1.0)),
            user_agent=str(mb_data.get("user_agent", "InvariantAudio/0.1.0")),
            enable_acoustid_lookup=bool(mb_data.get("enable_acoustid_lookup", True)),
            enable_acoustid_submission=bool(mb_data.get("enable_acoustid_submission", False)),
        )

        sc_data = data.get("scoring", {})
        sc_conf = ScoringConfig(
            min_auto_approval_score=float(sc_data.get("min_auto_approval_score", 0.80)),
            max_auto_approval_runner_up=float(sc_data.get("max_auto_approval_runner_up", 0.20)),
            min_auto_approval_margin=float(sc_data.get("min_auto_approval_margin", 0.60)),
            duration_tolerance_seconds=float(sc_data.get("duration_tolerance_seconds", 3.0)),
            min_acoustic_overlap_frames=int(sc_data.get("min_acoustic_overlap_frames", 150)),
        )

        return cls(
            media_root=Path(data.get("media_root", "/tmp/invariantaudio/media")),
            database_path=Path(data.get("database_path", "/tmp/invariantaudio/catalog.sqlite3")),
            backup_root=Path(data.get("backup_root", "/tmp/invariantaudio/backups")),
            quarantine_root=Path(data.get("quarantine_root", "/tmp/invariantaudio/quarantine")),
            work_root=Path(data.get("work_root", "/tmp/invariantaudio/staging")),
            mutation_lock_path=Path(data.get("mutation_lock_path", "/tmp/invariantaudio/.invariant_audio.lock")),
            batch_size_limit=int(data.get("batch_size_limit", 10)),
            enforce_payload_pcm_preservation=bool(data.get("enforce_payload_pcm_preservation", True)),
            enforce_source_continuity=bool(data.get("enforce_source_continuity", True)),
            musicbrainz=mb_conf,
            scoring=sc_conf,
        )
