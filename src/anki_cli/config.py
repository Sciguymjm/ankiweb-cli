from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomli_w


@dataclass
class Config:
    username: str | None = None
    endpoint: str = "https://sync.ankiweb.net"


def load_config(path: Path) -> Config:
    if not path.exists():
        return Config()
    data = tomllib.loads(path.read_text())
    return Config(
        username=data.get("username"),
        endpoint=data.get("endpoint", "https://sync.ankiweb.net"),
    )


def save_config(cfg: Config, path: Path) -> None:
    payload: dict[str, str] = {"endpoint": cfg.endpoint}
    if cfg.username is not None:
        payload["username"] = cfg.username
    path.write_text(tomli_w.dumps(payload))
