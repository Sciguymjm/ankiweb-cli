from __future__ import annotations

from typing import Any

from anki.collection import Collection


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
