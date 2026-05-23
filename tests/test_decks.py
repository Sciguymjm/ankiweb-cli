from pathlib import Path

from ankiweb_cli.collection import open_collection
from ankiweb_cli.commands.decks import (
    delete_deck,
    list_decks,
    merge_decks,
    move_cards,
    rename_deck,
    suspend_deck,
    unsuspend_deck,
)

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


def test_suspend_and_unsuspend_deck(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        nid = _add_basic_note(col, "Temp", "f", "b")
        cid = col.db.scalar("select id from cards where nid = ?", nid)
        assert cid is not None
        assert col.get_card(int(cid)).queue != -1

        s = suspend_deck(col, "Temp", recursive=False)
        assert s["status"] == "ok"
        assert s["cards_suspended"] == 1
        assert col.get_card(int(cid)).queue == -1

        s2 = suspend_deck(col, "Temp", recursive=False)
        assert s2["status"] == "noop"

        u = unsuspend_deck(col, "Temp", recursive=False)
        assert u["status"] == "ok"
        assert u["cards_unsuspended"] == 1
        assert col.get_card(int(cid)).queue != -1


def test_suspend_deck_noop_when_missing(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        assert suspend_deck(col, "Nope", recursive=False)["status"] == "noop"
        assert unsuspend_deck(col, "Nope", recursive=False)["status"] == "noop"


def test_rename_deck(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "Foo", "f", "b")
        old_id = col.decks.id_for_name("Foo")
        result = rename_deck(col, "Foo", "Bar")
        assert result["status"] == "ok"
        assert result["id"] == int(old_id)
        assert col.decks.id_for_name("Foo") is None
        assert col.decks.id_for_name("Bar") == old_id


def test_rename_target_exists_error(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "Foo", "f", "b")
        _add_basic_note(col, "Bar", "f2", "b2")
        result = rename_deck(col, "Foo", "Bar")
        assert result["status"] == "error"
        assert result["target"] == "Bar"
        assert col.decks.id_for_name("Foo") is not None


def test_rename_missing_noop(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        result = rename_deck(col, "Nope", "Nada")
        assert result["status"] == "noop"


def test_rename_carries_subdecks(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "Foo", "f", "b")
        _add_basic_note(col, "Foo::Bar", "f2", "b2")
        result = rename_deck(col, "Foo", "Baz")
        assert result["status"] == "ok"
        assert col.decks.id_for_name("Foo") is None
        assert col.decks.id_for_name("Foo::Bar") is None
        assert col.decks.id_for_name("Baz") is not None
        assert col.decks.id_for_name("Baz::Bar") is not None


def test_move_cards(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        nid1 = _add_basic_note(col, "Src", "a", "1")
        nid2 = _add_basic_note(col, "Src", "b", "2")
        _add_basic_note(col, "Dst", "c", "3")
        src_id = col.decks.id("Src")
        dst_id = col.decks.id("Dst")
        cids = [
            int(col.db.scalar("select id from cards where nid = ?", nid1)),
            int(col.db.scalar("select id from cards where nid = ?", nid2)),
        ]
        result = move_cards(col, cids, dst_name="Dst")
        assert result["status"] == "ok"
        assert result["moved"] == 2
        assert col.db.scalar(
            "select count() from cards where did = ?", src_id
        ) == 0
        assert col.db.scalar(
            "select count() from cards where did = ?", dst_id
        ) == 3


def test_move_creates_destination(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        nid = _add_basic_note(col, "Src", "a", "1")
        cid = int(col.db.scalar("select id from cards where nid = ?", nid))
        assert col.decks.id_for_name("Brand::New") is None
        result = move_cards(col, [cid], dst_name="Brand::New")
        assert result["status"] == "ok"
        new_id = col.decks.id_for_name("Brand::New")
        assert new_id is not None
        assert col.db.scalar(
            "select did from cards where id = ?", cid
        ) == new_id


def test_merge_decks(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "A", "a1", "1")
        _add_basic_note(col, "A", "a2", "2")
        _add_basic_note(col, "B", "b1", "3")
        result = merge_decks(col, ["A", "B"], into="C")
        assert result["status"] == "ok"
        assert result["moved"] == 3
        assert set(result["removed_decks"]) == {"A", "B"}
        assert col.decks.id_for_name("A") is None
        assert col.decks.id_for_name("B") is None
        c_id = col.decks.id_for_name("C")
        assert c_id is not None
        assert col.db.scalar(
            "select count() from cards where did = ?", c_id
        ) == 3


def test_merge_skips_missing_sources(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "A", "a1", "1")
        result = merge_decks(col, ["A", "Nope"], into="C")
        assert result["status"] == "ok"
        assert result["moved"] == 1
        assert result["removed_decks"] == ["A"]
        assert result["skipped"] == ["Nope"]


def test_merge_into_existing_destination(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        _add_basic_note(col, "A", "a1", "1")
        _add_basic_note(col, "Dest", "d1", "x")
        dest_id = col.decks.id("Dest")
        result = merge_decks(col, ["A", "Dest"], into="Dest")
        assert result["status"] == "ok"
        assert result["moved"] == 1
        assert result["removed_decks"] == ["A"]
        assert col.decks.id_for_name("A") is None
        assert col.decks.id_for_name("Dest") == dest_id
        assert col.db.scalar(
            "select count() from cards where did = ?", dest_id
        ) == 2
