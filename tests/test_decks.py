from pathlib import Path

from anki_cli.collection import open_collection
from anki_cli.commands.decks import list_decks


def test_list_decks_returns_default(tmp_path: Path) -> None:
    col_path = tmp_path / "col.anki2"
    with open_collection(col_path, backups_dir=tmp_path / "b", write=False) as col:
        decks = list_decks(col)
    names = [d["name"] for d in decks]
    assert "Default" in names
    for d in decks:
        assert "id" in d and "card_count" in d and "new" in d and "review" in d
