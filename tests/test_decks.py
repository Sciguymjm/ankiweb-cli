from pathlib import Path

from ankiweb_cli.collection import open_collection
from ankiweb_cli.commands.decks import delete_deck, list_decks

from anki.notes import Note


def test_list_decks_returns_default(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        decks = list_decks(col)
    names = [d["name"] for d in decks]
    assert "Default" in names
    for d in decks:
        assert "id" in d and "card_count" in d and "new" in d and "review" in d


def _add_basic_note(col, deck_name: str, front: str, back: str) -> int:
    nt = col.models.by_name("Basic")
    note = Note(col, nt)
    note["Front"] = front
    note["Back"] = back
    col.add_note(note, col.decks.id(deck_name))
    return note.id


def test_delete_deck_noop_when_missing(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        result = delete_deck(
            col, "DoesNotExist", recursive=False, delete_cards=False
        )
    assert result["status"] == "noop"


def test_delete_deck_moves_cards_to_default(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "Temp", "f", "b")
        default_id = col.decks.id("Default")
        result = delete_deck(col, "Temp", recursive=False, delete_cards=False)
        assert result["status"] == "ok"
        assert result["cards_affected"] == 1
        assert result["cards_deleted"] is False
        assert col.db.scalar(
            "select count() from cards where did = ?", default_id
        ) == 1
        assert col.decks.id_for_name("Temp") is None


def test_delete_deck_recursive(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "Parent", "a", "1")
        _add_basic_note(col, "Parent::Child", "b", "2")
        _add_basic_note(col, "Parent::Child::Grand", "c", "3")
        result = delete_deck(
            col, "Parent", recursive=True, delete_cards=False
        )
        assert result["status"] == "ok"
        assert set(result["decks_deleted"]) == {
            "Parent",
            "Parent::Child",
            "Parent::Child::Grand",
        }
        assert result["cards_affected"] == 3
        assert col.decks.id_for_name("Parent") is None
        assert col.decks.id_for_name("Parent::Child") is None


def test_delete_deck_with_cards(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "Temp", "f", "b")
        before = col.db.scalar("select count() from cards") or 0
        result = delete_deck(col, "Temp", recursive=False, delete_cards=True)
        after = col.db.scalar("select count() from cards") or 0
        assert result["status"] == "ok"
        assert result["cards_deleted"] is True
        assert before - after == 1
        assert col.decks.id_for_name("Temp") is None
