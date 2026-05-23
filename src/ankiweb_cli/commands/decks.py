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


def _resolve_deck_ids(
    col: Collection, name: str, *, recursive: bool
) -> list[tuple[str, int]]:
    """Return list of (deck_name, deck_id) for `name`, optionally including subdecks."""
    base_id = col.decks.id_for_name(name)
    if base_id is None:
        return []
    out: list[tuple[str, int]] = [(name, int(base_id))]
    if recursive:
        prefix = name + "::"
        for d in col.decks.all_names_and_ids():
            if d.name.startswith(prefix):
                out.append((d.name, int(d.id)))
    return out


def _card_ids_for_decks(col: Collection, deck_ids: list[int]) -> list[int]:
    if not deck_ids:
        return []
    placeholders = ",".join("?" for _ in deck_ids)
    rows = col.db.list(
        f"select id from cards where did in ({placeholders})", *deck_ids
    )
    return [int(r) for r in rows]


def delete_deck(
    col: Collection, name: str, *, recursive: bool, delete_cards: bool
) -> dict[str, Any]:
    """Delete a deck.

    If recursive=True, also delete all subdecks (matching name and `name::*`).
    If delete_cards=True, cards are deleted with the deck. If False, cards move
    to the Default deck.
    """
    decks = _resolve_deck_ids(col, name, recursive=recursive)
    if not decks:
        return {"status": "noop", "reason": "deck not found", "deck": name}

    deck_ids = [did for _, did in decks]
    card_ids = _card_ids_for_decks(col, deck_ids)

    if delete_cards and card_ids:
        col.remove_cards_and_orphaned_notes(card_ids)
    elif card_ids:
        default_id = col.decks.id("Default")
        col.set_deck(card_ids, default_id)

    col.decks.remove(deck_ids)

    return {
        "status": "ok",
        "decks_deleted": [n for n, _ in decks],
        "cards_affected": len(card_ids),
        "cards_deleted": bool(delete_cards),
    }


def count_cards_in_deck(col: Collection, name: str, *, recursive: bool) -> int | None:
    """Return card count for deck (incl. subdecks if recursive), or None if missing."""
    decks = _resolve_deck_ids(col, name, recursive=recursive)
    if not decks:
        return None
    return len(_card_ids_for_decks(col, [did for _, did in decks]))
