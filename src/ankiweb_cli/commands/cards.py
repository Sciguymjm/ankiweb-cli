from __future__ import annotations

from pathlib import Path
from typing import Any

from anki.collection import Collection
from anki.notes import Note


def list_cards(col: Collection, *, query: str, limit: int = 50) -> list[dict[str, Any]]:
    card_ids = col.find_cards(query)[:limit]
    rows: list[dict[str, Any]] = []
    for cid in card_ids:
        card = col.get_card(cid)
        note = card.note()
        rows.append({
            "card_id": cid,
            "note_id": note.id,
            "deck": col.decks.name(card.did),
            "note_type": note.note_type()["name"],
            "tags": note.tags,
            "fields": dict(zip(note.keys(), note.values(), strict=True)),
            "queue": card.queue,
            "due": card.due,
            "ivl": card.ivl,
            "ease": card.factor,
        })
    return rows


def add_note(
    col: Collection,
    *,
    deck: str,
    note_type: str,
    fields: dict[str, str],
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Add a single note (which produces 1+ cards based on the note type's templates)."""
    nt = col.models.by_name(note_type)
    if nt is None:
        return {
            "status": "error",
            "reason": "note type not found",
            "note_type": note_type,
            "available": [m.name for m in col.models.all_names_and_ids()],
        }
    available_fields = [f["name"] for f in nt["flds"]]
    missing = [k for k in fields if k not in available_fields]
    if missing:
        return {
            "status": "error",
            "reason": "unknown fields",
            "missing_fields": missing,
            "available_fields": available_fields,
        }
    note = Note(col, nt)
    for k, v in fields.items():
        note[k] = v
    if tags:
        note.tags = sorted(set(tags))
    deck_id = col.decks.id(deck)
    col.add_note(note, deck_id)
    card_ids = [int(c) for c in col.db.list("select id from cards where nid = ?", note.id)]
    return {
        "status": "ok",
        "note_id": int(note.id),
        "card_ids": card_ids,
        "deck": deck,
    }


def bulk_add_tsv(
    col: Collection,
    tsv_path: Path,
    *,
    deck: str,
    note_type: str,
    fields: list[str],
    tags: list[str] | None = None,
) -> dict[str, Any]:
    added = 0
    skipped_blank = 0
    errors: list[str] = []
    for lineno, raw in enumerate(tsv_path.read_text().splitlines(), start=1):
        if not raw.strip():
            skipped_blank += 1
            continue
        cols = raw.split("\t")
        if len(cols) != len(fields):
            errors.append(
                f"line {lineno}: expected {len(fields)} columns, got {len(cols)}"
            )
            continue
        result = add_note(
            col,
            deck=deck,
            note_type=note_type,
            fields=dict(zip(fields, cols, strict=True)),
            tags=tags,
        )
        if result["status"] == "ok":
            added += 1
        else:
            errors.append(f"line {lineno}: {result.get('reason', 'error')}")
    return {"added": added, "skipped_blank": skipped_blank, "errors": errors}


def retag_cards(
    col: Collection,
    card_ids: list[int],
    *,
    add: list[str],
    remove: list[str],
) -> dict[str, Any]:
    nids: set[int] = {col.get_card(cid).nid for cid in card_ids}
    add_set = set(add)
    remove_set = set(remove)
    changed = 0
    for nid in nids:
        note = col.get_note(nid)
        current = set(note.tags)
        new_tags = (current | add_set) - remove_set
        if new_tags != current:
            note.tags = sorted(new_tags)
            col.update_note(note)
            changed += 1
    return {
        "status": "ok",
        "notes_touched": len(nids),
        "notes_changed": changed,
        "tags_added": sorted(add_set),
        "tags_removed": sorted(remove_set),
    }
