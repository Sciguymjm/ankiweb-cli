from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from anki.collection import Collection


@contextmanager
def open_collection(
    path: Path,
    *,
    backups_dir: Path,
    write: bool,
    op: str = "op",
) -> Iterator[Collection]:
    """Open the Anki collection. If write=True, snapshots the file first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    backups_dir.mkdir(parents=True, exist_ok=True)
    if write and path.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, backups_dir / f"collection-{ts}-{op}.anki2")
    col = Collection(str(path))
    try:
        yield col
    finally:
        col.close()
