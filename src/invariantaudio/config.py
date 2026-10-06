# SPDX-License-Identifier: GPL-3.0-or-later
"""
Strict configuration parsing for InvariantAudio.

Every value is type-checked without coercion: a YAML string such as ``"false"``
is rejected, never interpreted as a boolean. Unknown keys, missing path keys
and values that would disable a safety invariant are errors (fail closed).
"""

import math
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping

from invariantaudio import __version__

DEFAULT_USER_AGENT = f"InvariantAudio/{__version__} ( https://github.com/thathugesamoan-byte/invariantaudio )"


class ConfigError(ValueError):
    """Invalid configuration."""


@dataclass
class MusicBrainzConfig:
    rate_limit_seconds: float = 1.0
    user_agent: str = DEFAULT_USER_AGENT
    # Reserved. No network lookup exists in v0.1.0-alpha, so True is rejected.
    enable_acoustid_lookup: bool = False
    # Submission is prohibited by project policy; False is the only accepted value.
    enable_acoustid_submission: bool = False


@dataclass
class ScoringConfig:
    # Parsed and validated, but not yet consumed by evidence.scorer, which uses
    # module-level constants in v0.1.0-alpha.
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
    # Both must be True in v0.1.0-alpha; the engine always enforces them.
    enforce_payload_pcm_preservation: bool = True
    enforce_source_continuity: bool = True
    musicbrainz: MusicBrainzConfig = field(default_factory=MusicBrainzConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AppConfig":
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ConfigError(f"invalid YAML: {e}")
        return cls.from_mapping(data)

    @classmethod
    def from_mapping(cls, data: Any) -> "AppConfig":
        if not isinstance(data, dict):
            raise ConfigError("top level must be a mapping")
        data = dict(data)
        mb_raw = data.pop("musicbrainz", {})
        sc_raw = data.pop("scoring", {})

        paths = {}
        for key in ("media_root", "database_path", "backup_root", "quarantine_root", "work_root", "mutation_lock_path"):
            if key not in data:
                raise ConfigError(f"{key} is required")
            paths[key] = Path(_str(data.pop(key), key))
        batch = _int(data.pop("batch_size_limit", 10), "batch_size_limit", minimum=1)
        enforce_pcm = _bool(data.pop("enforce_payload_pcm_preservation", True), "enforce_payload_pcm_preservation")
        enforce_src = _bool(data.pop("enforce_source_continuity", True), "enforce_source_continuity")
        if not enforce_pcm:
            raise ConfigError("enforce_payload_pcm_preservation cannot be disabled in v0.1.0-alpha")
        if not enforce_src:
            raise ConfigError("enforce_source_continuity cannot be disabled in v0.1.0-alpha")
        if data:
            raise ConfigError(f"unknown configuration keys: {sorted(map(str, data))}")

        return cls(
            **paths,
            batch_size_limit=batch,
            enforce_payload_pcm_preservation=enforce_pcm,
            enforce_source_continuity=enforce_src,
            musicbrainz=_musicbrainz(mb_raw),
            scoring=_scoring(sc_raw),
        )


def _section(raw: Any, name: str) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ConfigError(f"{name} must be a mapping")
    return dict(raw)


def _musicbrainz(raw: Any) -> MusicBrainzConfig:
    d = _section(raw, "musicbrainz")
    rate = _float(d.pop("rate_limit_seconds", 1.0), "musicbrainz.rate_limit_seconds")
    if rate < 1.0:
        raise ConfigError("musicbrainz.rate_limit_seconds must be >= 1.0")
    ua = _str(d.pop("user_agent", DEFAULT_USER_AGENT), "musicbrainz.user_agent")
    lookup = _bool(d.pop("enable_acoustid_lookup", False), "musicbrainz.enable_acoustid_lookup")
    submit = _bool(d.pop("enable_acoustid_submission", False), "musicbrainz.enable_acoustid_submission")
    if lookup:
        raise ConfigError("musicbrainz.enable_acoustid_lookup is reserved: no network lookup exists in v0.1.0-alpha")
    if submit:
        raise ConfigError("musicbrainz.enable_acoustid_submission is prohibited")
    if d:
        raise ConfigError(f"unknown musicbrainz keys: {sorted(map(str, d))}")
    return MusicBrainzConfig(rate_limit_seconds=rate, user_agent=ua, enable_acoustid_lookup=lookup,
                             enable_acoustid_submission=submit)


def _scoring(raw: Any) -> ScoringConfig:
    d = _section(raw, "scoring")
    out = ScoringConfig(
        min_auto_approval_score=_unit(d.pop("min_auto_approval_score", 0.80), "scoring.min_auto_approval_score"),
        max_auto_approval_runner_up=_unit(d.pop("max_auto_approval_runner_up", 0.20), "scoring.max_auto_approval_runner_up"),
        min_auto_approval_margin=_unit(d.pop("min_auto_approval_margin", 0.60), "scoring.min_auto_approval_margin"),
        duration_tolerance_seconds=_float(d.pop("duration_tolerance_seconds", 3.0), "scoring.duration_tolerance_seconds", minimum=0.0),
        min_acoustic_overlap_frames=_int(d.pop("min_acoustic_overlap_frames", 150), "scoring.min_acoustic_overlap_frames", minimum=0),
    )
    if d:
        raise ConfigError(f"unknown scoring keys: {sorted(map(str, d))}")
    return out


def _bool(v: Any, name: str) -> bool:
    if type(v) is not bool:
        raise ConfigError(f"{name} must be a boolean (true/false), got {type(v).__name__}: {v!r}")
    return v


def _int(v: Any, name: str, minimum: int) -> int:
    if type(v) is not int:
        raise ConfigError(f"{name} must be an integer, got {type(v).__name__}: {v!r}")
    if v < minimum:
        raise ConfigError(f"{name} must be >= {minimum}")
    return v


def _float(v: Any, name: str, minimum: float = float("-inf")) -> float:
    if type(v) not in (int, float):
        raise ConfigError(f"{name} must be a number, got {type(v).__name__}: {v!r}")
    f = float(v)
    if not math.isfinite(f) or f < minimum:
        raise ConfigError(f"{name} must be a finite number >= {minimum}")
    return f


def _unit(v: Any, name: str) -> float:
    f = _float(v, name, minimum=0.0)
    if f > 1.0:
        raise ConfigError(f"{name} must be between 0 and 1")
    return f


def _str(v: Any, name: str) -> str:
    if type(v) is not str or not v.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    return v
