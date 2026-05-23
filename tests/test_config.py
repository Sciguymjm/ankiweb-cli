from pathlib import Path

from anki_cli.config import Config, load_config, save_config


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.toml"
    cfg = Config(username="test@example.com", endpoint="https://sync.ankiweb.net")
    save_config(cfg, cfg_path)
    loaded = load_config(cfg_path)
    assert loaded.username == "test@example.com"
    assert loaded.endpoint == "https://sync.ankiweb.net"


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.username is None
