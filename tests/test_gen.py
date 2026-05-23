from pathlib import Path

from ankiweb_cli.collection import open_collection
from ankiweb_cli.commands.gen import gen_reverse

from anki.notes import Note


def _add_basic_note(col, deck_name: str, front: str, back: str) -> int:
    nt = col.models.by_name("Basic")
    note = Note(col, nt)
    note["Front"] = front
    note["Back"] = back
    col.add_note(note, col.decks.id(deck_name))
    return note.id


def test_gen_reverse_adds_template_and_card(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        nid = _add_basic_note(col, "Temp", "hello", "नमस्ते")
        cards_before = col.db.scalar(
            "select count() from cards where nid = ?", nid
        )
        assert cards_before == 1

        result = gen_reverse(
            col, deck="Temp", front_field="Back", back_field="Front"
        )
        assert result["status"] == "ok"
        assert result["template"] == "Reverse"

        cards_after = col.db.scalar(
            "select count() from cards where nid = ?", nid
        )
        assert cards_after == 2


def test_gen_reverse_noop_on_missing_deck(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        result = gen_reverse(
            col, deck="Nope", front_field="Back", back_field="Front"
        )
        assert result["status"] == "noop"


def test_gen_reverse_noop_on_empty_deck(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        col.decks.id("Empty")
        result = gen_reverse(
            col, deck="Empty", front_field="Back", back_field="Front"
        )
        assert result["status"] == "noop"


def test_gen_reverse_error_on_unknown_field(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "Temp", "hello", "नमस्ते")
        result = gen_reverse(
            col, deck="Temp", front_field="Nonexistent", back_field="Front"
        )
        assert result["status"] == "error"
        assert "Nonexistent" in result["missing_fields"]


def test_gen_reverse_noop_when_template_exists(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "Temp", "hello", "नमस्ते")
        first = gen_reverse(
            col, deck="Temp", front_field="Back", back_field="Front"
        )
        assert first["status"] == "ok"
        second = gen_reverse(
            col, deck="Temp", front_field="Back", back_field="Front"
        )
        assert second["status"] == "noop"
