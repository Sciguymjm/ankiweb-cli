from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def _parse_op(name: str) -> str | None:
    if not name.endswith(".anki2") or not name.startswith("collection-"):
        return None
    stem = name[len("collection-"):-len(".anki2")]
    parts = stem.split("-")
    if len(parts) < 2:
        return None
    return parts[-1] or None


def list_backups(backups_dir: Path) -> list[dict[str, Any]]:
    if not backups_dir.exists():
        return []
    rows: list[dict[str, Any]] = []
    for p in backups_dir.glob("collection-*.anki2"):
        st = p.stat()
        rows.append({
            "name": p.name,
            "size": st.st_size,
            "mtime": st.st_mtime,
            "op": _parse_op(p.name),
        })
    rows.sort(key=lambda r: r["mtime"], reverse=True)
    return rows


def restore_backup(backups_dir: Path, name: str, target: Path) -> dict[str, Any]:
    src = backups_dir / name
    if not src.exists():
        return {"status": "error", "reason": "backup not found", "name": name}
    pre_name: str | None = None
    if target.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        pre_name = f"collection-{ts}-pre-restore.anki2"
        backups_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backups_dir / pre_name)
    shutil.copy2(src, target)
    return {
        "status": "ok",
        "restored": name,
        "pre_restore_backup": pre_name,
        "size": target.stat().st_size,
    }
