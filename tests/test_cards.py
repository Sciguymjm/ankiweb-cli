from pathlib import Path

from anki_cli.collection import open_collection
from anki_cli.commands.cards import list_cards

from anki.notes import Note


def test_list_cards_filters_by_query(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        nt = col.models.by_name("Basic")
        note = Note(col, nt)
        note["Front"] = "नमस्ते"
        note["Back"] = "hello"
        col.add_note(note, col.decks.id("Default"))

        results = list_cards(col, query="hello", limit=10)
    assert len(results) == 1
    assert results[0]["fields"]["Back"] == "hello"
