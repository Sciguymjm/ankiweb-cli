from pathlib import Path

from anki_cli.collection import open_collection


def test_open_creates_collection_file(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "backups", write=False) as col:
        assert col_path.exists()
        assert col.decks.all() != []


def test_write_mode_creates_backup(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    backups = tmp_path / "backups"
    with open_collection(col_path, backups_dir=backups, write=False):
        pass
    with open_collection(col_path, backups_dir=backups, write=True, op="test"):
        pass
    snapshots = list(backups.glob("collection-*-test.anki2"))
    assert len(snapshots) == 1


def test_read_mode_no_backup(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    backups = tmp_path / "backups"
    with open_collection(col_path, backups_dir=backups, write=False):
        pass
    with open_collection(col_path, backups_dir=backups, write=False):
        pass
    assert list(backups.glob("*")) == []
