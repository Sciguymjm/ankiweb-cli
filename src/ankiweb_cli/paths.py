from __future__ import annotations

import os
import sys
from pathlib import Path


def _default_home() -> Path:
    """Pick a writeable per-user data directory.

    Honors $ANKIWEB_CLI_HOME if set. Otherwise follows the OS convention:
    XDG_DATA_HOME on Linux/BSD, ~/Library/Application Support on macOS,
    %APPDATA% on Windows.
    """
    override = os.environ.get("ANKIWEB_CLI_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ankiweb-cli"
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / "ankiweb-cli"
    xdg = os.environ.get("XDG_DATA_HOME")
    return (Path(xdg) if xdg else Path.home() / ".local" / "share") / "ankiweb-cli"


HOME_DIR = _default_home()
COLLECTION_DIR = HOME_DIR / "collection"
COLLECTION_FILE = COLLECTION_DIR / "collection.anki2"
BACKUPS_DIR = HOME_DIR / "backups"
CACHE_DIR = HOME_DIR / "cache"
CONFIG_FILE = HOME_DIR / "config.toml"


def ensure_dirs() -> None:
    for d in (COLLECTION_DIR, BACKUPS_DIR, CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)
