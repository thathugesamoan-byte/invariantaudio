# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import yaml

from invariantaudio.config import AppConfig, ConfigError

BASE = {
    "media_root": "/m", "database_path": "/d.sqlite3", "backup_root": "/b",
    "quarantine_root": "/q", "work_root": "/w", "mutation_lock_path": "/l",
}


def load(tmp_path, **extra):
    data = {**BASE, **extra}
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(data))
    return AppConfig.from_yaml(p)


def raw(tmp_path, text):
    p = tmp_path / "c.yaml"
    p.write_text(text)
    return AppConfig.from_yaml(p)


def test_defaults_are_safe(tmp_path):
    c = load(tmp_path)
    assert c.enforce_source_continuity is True and c.enforce_payload_pcm_preservation is True
    assert c.musicbrainz.enable_acoustid_submission is False
    assert c.musicbrainz.enable_acoustid_lookup is False
    assert c.batch_size_limit == 10
    assert "thathugesamoan-byte/invariantaudio" in c.musicbrainz.user_agent


@pytest.mark.parametrize("key", ["enforce_source_continuity", "enforce_payload_pcm_preservation"])
@pytest.mark.parametrize("val", ["false", "False", "true", "no", "0", 0, 1, None, [], "off"])
def test_non_boolean_safety_flags_are_rejected(tmp_path, key, val):
    with pytest.raises(ConfigError, match="boolean"):
        load(tmp_path, **{key: val})


@pytest.mark.parametrize("key", ["enforce_source_continuity", "enforce_payload_pcm_preservation"])
def test_safety_flags_cannot_be_disabled(tmp_path, key):
    with pytest.raises(ConfigError, match="cannot be disabled"):
        load(tmp_path, **{key: False})


@pytest.mark.parametrize("val", ["false", "no", 0, 1, "true"])
def test_acoustid_submission_string_or_int_is_rejected(tmp_path, val):
    with pytest.raises(ConfigError, match="boolean"):
        load(tmp_path, musicbrainz={"enable_acoustid_submission": val})


def test_acoustid_submission_true_is_prohibited(tmp_path):
    with pytest.raises(ConfigError, match="prohibited"):
        load(tmp_path, musicbrainz={"enable_acoustid_submission": True})


def test_acoustid_lookup_true_is_reserved(tmp_path):
    with pytest.raises(ConfigError, match="reserved"):
        load(tmp_path, musicbrainz={"enable_acoustid_lookup": True})


def test_yaml_bare_no_is_a_boolean_but_still_validated(tmp_path):
    # YAML 1.1 parsers turn bare `no`/`off` into False; PyYAML does. It must hit the "cannot be disabled" rule.
    with pytest.raises(ConfigError, match="cannot be disabled"):
        raw(tmp_path, "\n".join(f"{k}: {v}" for k, v in BASE.items()) + "\nenforce_source_continuity: off\n")


@pytest.mark.parametrize("bad", ["10", 10.5, True, 0, -1, None])
def test_batch_size_limit_must_be_positive_int(tmp_path, bad):
    with pytest.raises(ConfigError):
        load(tmp_path, batch_size_limit=bad)


@pytest.mark.parametrize("bad", ["1.0", True, 0.5, float("nan"), float("inf"), None])
def test_rate_limit_must_be_number_at_least_one_second(tmp_path, bad):
    with pytest.raises(ConfigError):
        load(tmp_path, musicbrainz={"rate_limit_seconds": bad})


@pytest.mark.parametrize("bad", ["0.8", True, 1.5, -0.1, None])
def test_score_thresholds_are_unit_floats(tmp_path, bad):
    with pytest.raises(ConfigError):
        load(tmp_path, scoring={"min_auto_approval_score": bad})


def test_unknown_keys_are_rejected(tmp_path):
    with pytest.raises(ConfigError, match="unknown"):
        load(tmp_path, enforce_source_continuty=True)  # typo must not be silently ignored
    with pytest.raises(ConfigError, match="unknown musicbrainz"):
        load(tmp_path, musicbrainz={"enable_acoustid_submision": False})
    with pytest.raises(ConfigError, match="unknown scoring"):
        load(tmp_path, scoring={"x": 1})


@pytest.mark.parametrize("missing", list(BASE))
def test_paths_are_required_no_silent_tmp_defaults(tmp_path, missing):
    data = {k: v for k, v in BASE.items() if k != missing}
    with pytest.raises(ConfigError, match="required"):
        AppConfig.from_mapping(data)


@pytest.mark.parametrize("bad", [123, "", "  ", None, ["x"]])
def test_paths_must_be_non_empty_strings(tmp_path, bad):
    with pytest.raises(ConfigError):
        load(tmp_path, media_root=bad)


@pytest.mark.parametrize("doc", ["", "[]", "just a string", "- a\n- b"])
def test_top_level_must_be_mapping(tmp_path, doc):
    with pytest.raises(ConfigError):
        raw(tmp_path, doc)


def test_sections_must_be_mappings(tmp_path):
    with pytest.raises(ConfigError):
        load(tmp_path, musicbrainz="yes")


def test_malformed_yaml(tmp_path):
    with pytest.raises(ConfigError, match="invalid YAML"):
        raw(tmp_path, "media_root: [unclosed")


def test_example_config_parses(tmp_path):
    from pathlib import Path
    ex = Path(__file__).resolve().parents[2] / "config.example.yaml"
    c = AppConfig.from_yaml(ex)
    assert c.musicbrainz.enable_acoustid_submission is False
