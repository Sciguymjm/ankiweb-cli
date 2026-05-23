from __future__ import annotations

from typing import Any

from anki.collection import Collection


def _notes_using_note_type(col: Collection, ntid: int) -> int:
    return int(col.db.scalar("select count() from notes where mid = ?", ntid) or 0)


def _cards_for_note_type(col: Collection, ntid: int) -> int:
    return int(
        col.db.scalar(
            "select count() from cards where nid in (select id from notes where mid = ?)",
            ntid,
        )
        or 0
    )


def note_type_for_deck(col: Collection, deck: str) -> dict[str, Any] | None:
    """Return the note type used by the first card in the deck, or None if empty."""
    deck_id = col.decks.id_for_name(deck)
    if deck_id is None:
        return None
    cid = col.db.scalar("select id from cards where did = ? limit 1", deck_id)
    if cid is None:
        return None
    return col.get_card(int(cid)).note().note_type()


def gen_reverse(
    col: Collection,
    *,
    deck: str,
    front_field: str,
    back_field: str,
    template_name: str = "Reverse",
) -> dict[str, Any]:
    """Add a reverse card template to the note type used by `deck`.

    Anki regenerates cards for existing notes automatically.
    """
    deck_id = col.decks.id_for_name(deck)
    if deck_id is None:
        return {"status": "noop", "reason": "deck not found", "deck": deck}

    nt = note_type_for_deck(col, deck)
    if nt is None:
        return {"status": "noop", "reason": "deck is empty", "deck": deck}

    existing_template_names = [t["name"] for t in nt["tmpls"]]
    if template_name in existing_template_names:
        return {
            "status": "noop",
            "reason": "template already exists",
            "note_type": nt["name"],
            "template": template_name,
        }

    field_names = [f["name"] for f in nt["flds"]]
    missing = [f for f in (front_field, back_field) if f not in field_names]
    if missing:
        return {
            "status": "error",
            "reason": "field not found",
            "missing_fields": missing,
            "available_fields": field_names,
        }

    ntid = int(nt["id"])
    cards_before = _cards_for_note_type(col, ntid)

    tmpl = col.models.new_template(template_name)
    tmpl["qfmt"] = "{{" + front_field + "}}"
    tmpl["afmt"] = "{{FrontSide}}<hr id=answer>{{" + back_field + "}}"
    col.models.add_template(nt, tmpl)
    col.models.update_dict(nt)

    cards_after = _cards_for_note_type(col, ntid)

    return {
        "status": "ok",
        "note_type": nt["name"],
        "template": template_name,
        "cards_before": cards_before,
        "cards_after": cards_after,
    }
