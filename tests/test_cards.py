from pathlib import Path

from ankiweb_cli.collection import open_collection
from ankiweb_cli.commands.cards import add_note, bulk_add_tsv, list_cards, retag_cards

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


def test_add_basic_note(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        result = add_note(
            col,
            deck="Temp",
            note_type="Basic",
            fields={"Front": "hello", "Back": "hola"},
            tags=["greet"],
        )
        assert result["status"] == "ok"
        assert isinstance(result["note_id"], int)
        assert len(result["card_ids"]) == 1
        cid = result["card_ids"][0]
        card = col.get_card(cid)
        assert card.note()["Front"] == "hello"
        assert card.note().tags == ["greet"]


def test_add_unknown_field_error(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        result = add_note(
            col,
            deck="Temp",
            note_type="Basic",
            fields={"Front": "hi", "Nope": "x"},
        )
    assert result["status"] == "error"
    assert "Nope" in result["missing_fields"]
    assert "Front" in result["available_fields"]


def test_add_unknown_note_type_error(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        result = add_note(
            col,
            deck="Temp",
            note_type="DoesNotExist",
            fields={"Front": "x"},
        )
    assert result["status"] == "error"
    assert result["note_type"] == "DoesNotExist"
    assert isinstance(result["available"], list)


def test_bulk_add_tsv(tmp_path: Path) -> None:
    tsv = tmp_path / "in.tsv"
    tsv.write_text("hello\thola\nbye\tadios\n")
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        result = bulk_add_tsv(
            col,
            tsv,
            deck="Bulk",
            note_type="Basic",
            fields=["Front", "Back"],
        )
        assert result["added"] == 2
        assert result["errors"] == []
        deck_id = col.decks.id("Bulk")
        assert col.db.scalar(
            "select count() from cards where did = ?", deck_id
        ) == 2


def test_bulk_add_tsv_column_mismatch_in_errors(tmp_path: Path) -> None:
    tsv = tmp_path / "in.tsv"
    tsv.write_text("hello\thola\nbadrow\n\ngood\tbueno\n")
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        result = bulk_add_tsv(
            col,
            tsv,
            deck="Bulk",
            note_type="Basic",
            fields=["Front", "Back"],
        )
    assert result["added"] == 2
    assert result["skipped_blank"] == 1
    assert len(result["errors"]) == 1
    assert "line 2" in result["errors"][0]


def test_retag_adds_and_removes(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        nt = col.models.by_name("Basic")
        note = Note(col, nt)
        note["Front"] = "f"
        note["Back"] = "b"
        note.tags = ["old", "keep"]
        col.add_note(note, col.decks.id("Default"))
        cid = int(col.db.scalar("select id from cards where nid = ?", note.id))

        result = retag_cards(col, [cid], add=["new"], remove=["old"])
        assert result["status"] == "ok"
        assert result["notes_touched"] == 1
        assert result["notes_changed"] == 1
        refreshed = col.get_note(note.id)
        assert set(refreshed.tags) == {"new", "keep"}


def test_retag_noop_when_tags_already_match(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        nt = col.models.by_name("Basic")
        note = Note(col, nt)
        note["Front"] = "f"
        note["Back"] = "b"
        note.tags = ["keep"]
        col.add_note(note, col.decks.id("Default"))
        cid = int(col.db.scalar("select id from cards where nid = ?", note.id))

        result = retag_cards(col, [cid], add=["keep"], remove=["absent"])
        assert result["status"] == "ok"
        assert result["notes_touched"] == 1
        assert result["notes_changed"] == 0
