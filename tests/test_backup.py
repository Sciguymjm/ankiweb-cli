import os
from pathlib import Path

from ankiweb_cli.commands.backup import list_backups, restore_backup


def test_list_backups_empty_dir(tmp_path: Path) -> None:
    assert list_backups(tmp_path / "missing") == []
    empty = tmp_path / "b"
    empty.mkdir()
    assert list_backups(empty) == []


def test_list_backups_newest_first(tmp_path: Path) -> None:
    b = tmp_path / "b"
    b.mkdir()
    files = [
        ("collection-20260101-000000-delete.anki2", 1_000_000.0),
        ("collection-20260102-000000-sync.anki2", 2_000_000.0),
        ("collection-20260103-000000-merge.anki2", 3_000_000.0),
    ]
    for name, ts in files:
        p = b / name
        p.write_bytes(b"x")
        os.utime(p, (ts, ts))
    rows = list_backups(b)
    assert [r["name"] for r in rows] == [
        "collection-20260103-000000-merge.anki2",
        "collection-20260102-000000-sync.anki2",
        "collection-20260101-000000-delete.anki2",
    ]
    assert [r["op"] for r in rows] == ["merge", "sync", "delete"]


def test_list_backups_unparseable_filename(tmp_path: Path) -> None:
    b = tmp_path / "b"
    b.mkdir()
    (b / "collection-weirdname.anki2").write_bytes(b"x")
    rows = list_backups(b)
    assert len(rows) == 1
    assert rows[0]["op"] is None


def test_restore_overwrites_target(tmp_path: Path) -> None:
    b = tmp_path / "b"
    b.mkdir()
    src = b / "collection-20260101-000000-sync.anki2"
    src.write_bytes(b"backup-content")
    target = tmp_path / "collection.anki2"
    result = restore_backup(b, src.name, target)
    assert result["status"] == "ok"
    assert target.read_bytes() == b"backup-content"


def test_restore_creates_pre_restore_snapshot(tmp_path: Path) -> None:
    b = tmp_path / "b"
    b.mkdir()
    src = b / "collection-20260101-000000-sync.anki2"
    src.write_bytes(b"new")
    target = tmp_path / "collection.anki2"
    target.write_bytes(b"old")
    result = restore_backup(b, src.name, target)
    assert result["status"] == "ok"
    assert result["pre_restore_backup"] is not None
    pre = b / result["pre_restore_backup"]
    assert pre.exists()
    assert pre.read_bytes() == b"old"
    assert target.read_bytes() == b"new"


def test_restore_missing_backup_error(tmp_path: Path) -> None:
    b = tmp_path / "b"
    b.mkdir()
    target = tmp_path / "collection.anki2"
    result = restore_backup(b, "collection-nope.anki2", target)
    assert result["status"] == "error"
    assert result["reason"] == "backup not found"
    assert not target.exists()
