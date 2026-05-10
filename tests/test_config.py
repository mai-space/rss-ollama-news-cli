import json
from pathlib import Path
from unittest.mock import patch

from newsroom.config import (
    DEFAULT_FEEDS,
    AppConfig,
    FeedConfig,
    OllamaConfig,
    load_config,
    save_config,
)


def test_default_config_has_feeds():
    config = AppConfig()
    assert len(config.feeds) > 0
    assert all(isinstance(f, FeedConfig) for f in config.feeds)


def test_default_feeds_match_constant():
    config = AppConfig()
    assert len(config.feeds) == len(DEFAULT_FEEDS)


def test_default_ollama_model():
    assert AppConfig().ollama.model == "llama3.2"


def test_ollama_prompt_contains_placeholder():
    assert "{content}" in OllamaConfig().prompt


def test_feed_enabled_by_default():
    assert FeedConfig(name="X", url="https://x.com").enabled is True


def test_feed_has_category():
    feed = FeedConfig(name="X", url="https://x.com", category="Tech")
    assert feed.category == "Tech"


def test_save_and_load_roundtrip(tmp_path: Path):
    config = AppConfig(
        feeds=[FeedConfig(name="Round Trip", url="https://rt.example.com", category="Test")]
    )
    config_file = tmp_path / "config.json"

    with (
        patch("newsroom.config.CONFIG_FILE", config_file),
        patch("newsroom.config.CONFIG_DIR", tmp_path),
    ):
        save_config(config)
        assert config_file.exists()
        loaded = load_config()

    assert len(loaded.feeds) == 1
    assert loaded.feeds[0].name == "Round Trip"
    assert loaded.feeds[0].category == "Test"


def test_load_creates_default_when_missing(tmp_path: Path):
    config_file = tmp_path / "config.json"
    assert not config_file.exists()

    with (
        patch("newsroom.config.CONFIG_FILE", config_file),
        patch("newsroom.config.CONFIG_DIR", tmp_path),
    ):
        config = load_config()

    assert isinstance(config, AppConfig)
    assert len(config.feeds) == len(DEFAULT_FEEDS)
    assert config_file.exists()


def test_load_falls_back_on_corrupted_json(tmp_path: Path):
    config_file = tmp_path / "config.json"
    config_file.write_text("not valid json }{{{", encoding="utf-8")

    with (
        patch("newsroom.config.CONFIG_FILE", config_file),
        patch("newsroom.config.CONFIG_DIR", tmp_path),
    ):
        config = load_config()

    assert isinstance(config, AppConfig)
    assert len(config.feeds) > 0


def test_config_serialisation_roundtrip():
    config = AppConfig()
    data = json.loads(config.model_dump_json())
    restored = AppConfig.model_validate(data)
    assert len(restored.feeds) == len(config.feeds)
    assert restored.ollama.model == config.ollama.model


def test_email_config_defaults():
    config = AppConfig()
    assert config.email.enabled is False
    assert config.email.smtp_port == 587
    assert config.email.to_addrs == []
