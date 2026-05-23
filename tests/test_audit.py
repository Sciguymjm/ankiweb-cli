from pathlib import Path

from ankiweb_cli.collection import open_collection
from ankiweb_cli.commands.audit import audit_collection

from anki.notes import Note


def test_audit_flags_one_direction_note_type(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        nt = col.models.by_name("Basic")
        note = Note(col, nt)
        note["Front"] = "हाथी"
        note["Back"] = "elephant"
        col.add_note(note, col.decks.id("OneWay"))

        report = audit_collection(col)
    one_way = [d for d in report["decks"] if d["name"] == "OneWay"][0]
    assert one_way["templates"] == 1
    assert one_way["one_direction"] is True


def test_audit_finds_duplicates(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        nt = col.models.by_name("Basic")
        for _ in range(2):
            note = Note(col, nt)
            note["Front"] = "किताब"
            note["Back"] = "book"
            col.add_note(note, col.decks.id("Default"))
        report = audit_collection(col)
    assert any(d["front"] == "किताब" and d["count"] >= 2 for d in report["duplicates"])
