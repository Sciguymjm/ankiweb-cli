from __future__ import annotations

from collections import Counter
from typing import Any

from anki.collection import Collection

from ankiweb_cli.commands.decks import list_decks


def audit_collection(col: Collection) -> dict[str, Any]:
    decks = list_decks(col)
    enriched_decks: list[dict[str, Any]] = []
    for d in decks:
        sample_cid = col.db.scalar("select id from cards where did = ? limit 1", d["id"])
        templates = 0
        one_direction = False
        note_type_name: str | None = None
        if sample_cid:
            card = col.get_card(sample_cid)
            nt = card.note().note_type()
            templates = len(nt["tmpls"])
            one_direction = templates == 1
            note_type_name = nt["name"]
        enriched_decks.append({**d, "templates": templates,
                                "one_direction": one_direction,
                                "note_type": note_type_name})

    front_counts: Counter[str] = Counter()
    for nid in col.db.list("select id from notes"):
        note = col.get_note(nid)
        front = note.values()[0] if note.values() else ""
        if front:
            front_counts[front] += 1
    duplicates = [
        {"front": f, "count": c}
        for f, c in front_counts.items()
        if c > 1
    ]

    note_types: list[dict[str, Any]] = []
    for nt in col.models.all():
        nid_count = col.db.scalar("select count() from notes where mid = ?", nt["id"]) or 0
        note_types.append({
            "id": nt["id"],
            "name": nt["name"],
            "fields": [f["name"] for f in nt["flds"]],
            "templates": [t["name"] for t in nt["tmpls"]],
            "note_count": nid_count,
        })

    return {
        "decks": enriched_decks,
        "duplicates": duplicates,
        "note_types": note_types,
        "totals": {
            "decks": len(enriched_decks),
            "cards": col.db.scalar("select count() from cards") or 0,
            "notes": col.db.scalar("select count() from notes") or 0,
        },
    }
