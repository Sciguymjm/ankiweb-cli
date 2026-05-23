from __future__ import annotations

from pathlib import Path

ANKI_DIR = Path(__file__).resolve().parents[2]
COLLECTION_DIR = ANKI_DIR / "collection"
COLLECTION_FILE = COLLECTION_DIR / "collection.anki2"
BACKUPS_DIR = ANKI_DIR / "backups"
CACHE_DIR = ANKI_DIR / "cache"
CONFIG_FILE = ANKI_DIR / "config.toml"


def ensure_dirs() -> None:
    for d in (COLLECTION_DIR, BACKUPS_DIR, CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)
