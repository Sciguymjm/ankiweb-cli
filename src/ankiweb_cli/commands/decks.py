from __future__ import annotations

from typing import Any

from anki.collection import Collection


def list_decks(col: Collection) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for d in col.decks.all_names_and_ids():
        deck_id = d.id
        card_count = col.db.scalar("select count() from cards where did = ?", deck_id) or 0
        new = col.db.scalar(
            "select count() from cards where did = ? and queue = 0", deck_id
        ) or 0
        review = col.db.scalar(
            "select count() from cards where did = ? and queue in (2, 3)", deck_id
        ) or 0
        learning = col.db.scalar(
            "select count() from cards where did = ? and queue in (1, 4)", deck_id
        ) or 0
        suspended = col.db.scalar(
            "select count() from cards where did = ? and queue = -1", deck_id
        ) or 0
        rows.append({
            "id": deck_id,
            "name": d.name,
            "card_count": card_count,
            "new": new,
            "learning": learning,
            "review": review,
            "suspended": suspended,
        })
    rows.sort(key=lambda r: r["name"])
    return rows
