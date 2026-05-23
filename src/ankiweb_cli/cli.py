import getpass
import json
import sys
from pathlib import Path

import click

from ankiweb_cli import sync as sync_mod
from ankiweb_cli.collection import open_collection
from ankiweb_cli.commands.audit import audit_collection
from ankiweb_cli.commands.backup import list_backups, restore_backup
from ankiweb_cli.commands.cards import (
    add_note,
    bulk_add_tsv,
    delete_cards,
    list_cards,
    retag_cards,
)
from ankiweb_cli.commands.decks import (
    count_cards_in_deck,
    delete_deck,
    list_decks,
    merge_decks,
    move_cards,
    rename_deck,
    suspend_deck,
    unsuspend_deck,
)
from ankiweb_cli.commands.gen import gen_reverse, note_type_for_deck
from ankiweb_cli.config import Config, load_config, save_config
from ankiweb_cli.output import emit
from ankiweb_cli.paths import BACKUPS_DIR, COLLECTION_FILE, CONFIG_FILE, ensure_dirs


@click.group()
@click.version_option()
def main() -> None:
    """Headless CLI for AnkiWeb."""


@main.group()
def config() -> None:
    """View and edit ankiweb-cli config."""


@config.command("show")
def config_show() -> None:
    ensure_dirs()
    cfg = load_config(CONFIG_FILE)
    json.dump({"username": cfg.username, "endpoint": cfg.endpoint}, sys.stdout, indent=2)
    sys.stdout.write("\n")


@config.command("set")
@click.argument("key", type=click.Choice(["username", "endpoint"]))
@click.argument("value")
def config_set(key: str, value: str) -> None:
    ensure_dirs()
    cfg = load_config(CONFIG_FILE)
    setattr(cfg, key, value)
    save_config(cfg, CONFIG_FILE)


@main.command()
def login() -> None:
    """Store AnkiWeb password in OS keyring and verify it."""
    ensure_dirs()
    cfg = load_config(CONFIG_FILE)
    if not cfg.username:
        raise click.ClickException("Run `ankiweb-cli config set username <email>` first.")
    password = getpass.getpass("AnkiWeb password: ")
    _, endpoint = sync_mod.login_and_get_hkey(cfg.username, password, cfg.endpoint)
    sync_mod.store_password(cfg.username, password)
    save_config(Config(username=cfg.username, endpoint=endpoint), CONFIG_FILE)
    emit({"ok": True, "endpoint": endpoint})


@main.command("sync")
@click.option(
    "--full",
    type=click.Choice(["upload", "download"]),
    default=None,
    help="Force a full sync in this direction (replaces server or local copy).",
)
def sync_cmd(full: str | None) -> None:
    """Pull from AnkiWeb, push local changes."""
    ensure_dirs()
    cfg = load_config(CONFIG_FILE)
    if not cfg.username:
        raise click.ClickException("Not configured. Run `ankiweb-cli login` first.")
    password = sync_mod.get_password(cfg.username)
    if not password:
        raise click.ClickException("No password in keyring. Run `ankiweb-cli login`.")
    hkey, endpoint = sync_mod.login_and_get_hkey(
        cfg.username, password, cfg.endpoint
    )
    if endpoint != cfg.endpoint:
        save_config(Config(username=cfg.username, endpoint=endpoint), CONFIG_FILE)

    if full is not None:
        result = sync_mod.do_full_sync(
            COLLECTION_FILE,
            BACKUPS_DIR,
            username=cfg.username,
            password=password,
            endpoint=cfg.endpoint,
            upload=(full == "upload"),
        )
        emit(result)
        return

    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="sync"
    ) as col:
        result = sync_mod.do_sync(col, hkey, endpoint)
    if result.required_full_sync:
        raise click.ClickException(
            "Server requires a full sync. Re-run with `--full download` to pull "
            "the AnkiWeb collection (replacing local) or `--full upload` to push "
            "local (replacing AnkiWeb)."
        )
    emit(
        {
            "pulled": result.pulled,
            "pushed": result.pushed,
            "endpoint": result.new_endpoint or endpoint,
            "server_message": result.server_message,
        }
    )


@main.group()
def decks() -> None:
    """Operations on decks."""


@decks.command("list")
def decks_list() -> None:
    """List all decks with card counts and review state."""
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        rows = list_decks(col)
    emit(rows, human=lambda rs: "\n".join(
        f"{r['name']:<40} {r['card_count']:>6}  new={r['new']} rev={r['review']}"
        for r in rs
    ))


@decks.command("delete")
@click.argument("name")
@click.option("--recursive", "-r", is_flag=True, help="Delete subdecks too")
@click.option(
    "--delete-cards", is_flag=True, help="Delete cards (default: move to Default)"
)
@click.option("--yes", is_flag=True, envvar="ANKIWEB_CLI_YES")
@click.option("--yes-really", is_flag=True)
def decks_delete(
    name: str, recursive: bool, delete_cards: bool, yes: bool, yes_really: bool
) -> None:
    """Delete a deck (and optionally its subdecks/cards)."""
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        card_count = count_cards_in_deck(col, name, recursive=recursive)
    if card_count is None:
        emit({"status": "noop", "reason": "deck not found", "deck": name})
        return
    if card_count > 50 and not yes_really:
        raise click.ClickException(
            f"Deck has {card_count} cards; pass --yes-really to confirm bulk action."
        )
    action = "delete cards" if delete_cards else "move cards to Default"
    if not yes:
        click.confirm(
            f"Delete deck '{name}'"
            f"{' and subdecks' if recursive else ''} "
            f"({card_count} cards will {action})?",
            abort=True,
        )
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="delete"
    ) as col:
        result = delete_deck(
            col, name, recursive=recursive, delete_cards=delete_cards
        )
    emit(result)


@decks.command("suspend")
@click.argument("name")
@click.option(
    "--recursive", "-r", is_flag=True, default=True, help="Include subdecks (default: yes)"
)
@click.option("--yes", is_flag=True, envvar="ANKIWEB_CLI_YES")
@click.option("--yes-really", is_flag=True)
def decks_suspend(name: str, recursive: bool, yes: bool, yes_really: bool) -> None:
    """Suspend all cards in a deck."""
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        card_count = count_cards_in_deck(col, name, recursive=recursive)
    if card_count is None:
        emit({"status": "noop", "reason": "deck not found", "deck": name})
        return
    if card_count > 50 and not yes_really:
        raise click.ClickException(
            f"Deck has {card_count} cards; pass --yes-really to confirm bulk action."
        )
    if not yes:
        click.confirm(
            f"Suspend all cards in '{name}'"
            f"{' (incl. subdecks)' if recursive else ''} ({card_count} cards)?",
            abort=True,
        )
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="suspend"
    ) as col:
        result = suspend_deck(col, name, recursive=recursive)
    emit(result)


@decks.command("unsuspend")
@click.argument("name")
@click.option("--recursive", "-r", is_flag=True, default=True)
@click.option("--yes", is_flag=True, envvar="ANKIWEB_CLI_YES")
def decks_unsuspend(name: str, recursive: bool, yes: bool) -> None:
    """Unsuspend all suspended cards in a deck."""
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        card_count = count_cards_in_deck(col, name, recursive=recursive)
    if card_count is None:
        emit({"status": "noop", "reason": "deck not found", "deck": name})
        return
    if not yes:
        click.confirm(
            f"Unsuspend cards in '{name}'"
            f"{' (incl. subdecks)' if recursive else ''}?",
            abort=True,
        )
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="unsuspend"
    ) as col:
        result = unsuspend_deck(col, name, recursive=recursive)
    emit(result)


@decks.command("rename")
@click.argument("old")
@click.argument("new")
@click.option("--dry-run", is_flag=True)
def decks_rename(old: str, new: str, dry_run: bool) -> None:
    """Rename a deck (and its subdecks)."""
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        old_id = col.decks.id_for_name(old)
        if old_id is None:
            emit({"status": "noop", "reason": "deck not found", "deck": old})
            return
        if col.decks.id_for_name(new) is not None:
            emit({"status": "error", "reason": "target deck exists", "target": new})
            return
        if dry_run:
            prefix = old + "::"
            subdecks = [
                d.name for d in col.decks.all_names_and_ids()
                if d.name.startswith(prefix)
            ]
            renames = [(old, new)] + [
                (s, new + "::" + s[len(prefix):]) for s in subdecks
            ]
            emit({
                "status": "dry-run",
                "renames": [{"from": a, "to": b} for a, b in renames],
            })
            return
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="rename"
    ) as col:
        result = rename_deck(col, old, new)
    emit(result)


@decks.command("move")
@click.option("--ids", required=True, help="Comma-separated card IDs")
@click.option("--to", "dst", required=True, help="Destination deck (created if missing)")
@click.option("--yes", is_flag=True, envvar="ANKIWEB_CLI_YES")
@click.option("--yes-really", is_flag=True)
def decks_move(ids: str, dst: str, yes: bool, yes_really: bool) -> None:
    """Move specific cards to another deck."""
    try:
        card_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError as e:
        raise click.ClickException(f"Invalid card IDs: {e}") from e
    if not card_ids:
        emit({"status": "noop", "reason": "no card ids", "deck": dst})
        return
    if len(card_ids) > 50 and not yes_really:
        raise click.ClickException(
            f"Moving {len(card_ids)} cards; pass --yes-really to confirm bulk action."
        )
    if not yes:
        click.confirm(
            f"Move {len(card_ids)} cards to '{dst}'?",
            abort=True,
        )
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="move"
    ) as col:
        result = move_cards(col, card_ids, dst_name=dst)
    emit(result)


@decks.command("merge")
@click.argument("sources", nargs=-1, required=True)
@click.option("--into", required=True, help="Destination deck (created if missing)")
@click.option("--yes", is_flag=True, envvar="ANKIWEB_CLI_YES")
@click.option("--yes-really", is_flag=True)
def decks_merge(
    sources: tuple[str, ...], into: str, yes: bool, yes_really: bool
) -> None:
    """Merge one or more decks into a destination deck (sources are deleted)."""
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        total = 0
        found: list[str] = []
        missing: list[str] = []
        for src in sources:
            sid = col.decks.id_for_name(src)
            if sid is None:
                missing.append(src)
                continue
            found.append(src)
            total += int(
                col.db.scalar("select count() from cards where did = ?", int(sid)) or 0
            )
    if not found:
        emit({"status": "noop", "reason": "no source decks found", "skipped": missing})
        return
    if total > 50 and not yes_really:
        raise click.ClickException(
            f"Merge would move {total} cards; pass --yes-really to confirm bulk action."
        )
    if not yes:
        msg = (
            f"Merge {found} into '{into}' ({total} cards total)"
            + (f"; skipping missing: {missing}" if missing else "")
            + "?"
        )
        click.confirm(msg, abort=True)
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="merge"
    ) as col:
        result = merge_decks(col, list(sources), into=into)
    emit(result)


@main.group()
def gen() -> None:
    """Generators (additive only)."""


@gen.command("reverse")
@click.argument("deck")
@click.option("--front-field", required=True)
@click.option("--back-field", required=True)
@click.option("--template-name", default="Reverse")
@click.option("--yes", is_flag=True, envvar="ANKIWEB_CLI_YES")
def gen_reverse_cmd(
    deck: str,
    front_field: str,
    back_field: str,
    template_name: str,
    yes: bool,
) -> None:
    """Add a reverse card template to the note type used by DECK."""
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        nt = note_type_for_deck(col, deck)
        if nt is None:
            emit({"status": "noop", "reason": "deck not found or empty", "deck": deck})
            return
        ntid = int(nt["id"])
        note_count = int(
            col.db.scalar("select count() from notes where mid = ?", ntid) or 0
        )
        nt_name = nt["name"]
    if not yes:
        click.confirm(
            f"Add template '{template_name}' to note type '{nt_name}' "
            f"(will create ~{note_count} new cards across all notes using this type)?",
            abort=True,
        )
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="gen-reverse"
    ) as col:
        result = gen_reverse(
            col,
            deck=deck,
            front_field=front_field,
            back_field=back_field,
            template_name=template_name,
        )
    emit(result)


@main.group()
def cards() -> None:
    """Operations on cards."""


@cards.command("list")
@click.option("--query", "-q", default="", help="Anki search syntax")
@click.option("--deck", default=None)
@click.option("--limit", default=50, type=int)
def cards_list(query: str, deck: str | None, limit: int) -> None:
    """List cards matching an Anki search query."""
    full_query = query
    if deck:
        full_query = f'deck:"{deck}" {query}'.strip()
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        rows = list_cards(col, query=full_query, limit=limit)
    emit(rows)


@cards.command("add")
@click.option("--deck", required=True, help="Destination deck (created if missing)")
@click.option("--note-type", default="Basic")
@click.option(
    "--field",
    "fields_in",
    multiple=True,
    metavar="KEY=VALUE",
    help="Field assignment, can repeat (e.g. --field Front=hello --field Back=hola)",
)
@click.option("--tag", "tags_in", multiple=True, help="Tag to attach; can repeat")
@click.option(
    "--from-file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Bulk add from a TSV file",
)
@click.option(
    "--fields-order",
    default=None,
    help="With --from-file: comma-separated field names matching TSV columns",
)
@click.option("--yes", is_flag=True, envvar="ANKIWEB_CLI_YES")
@click.option("--yes-really", is_flag=True)
def cards_add(
    deck: str,
    note_type: str,
    fields_in: tuple[str, ...],
    tags_in: tuple[str, ...],
    from_file: Path | None,
    fields_order: str | None,
    yes: bool,
    yes_really: bool,
) -> None:
    """Add one or more notes (and the cards they generate)."""
    tags = list(tags_in) if tags_in else None
    if from_file is not None:
        if not fields_order:
            raise click.ClickException("--from-file requires --fields-order")
        field_names = [f.strip() for f in fields_order.split(",") if f.strip()]
        line_count = sum(
            1 for line in from_file.read_text().splitlines() if line.strip()
        )
        if line_count > 50 and not yes_really:
            raise click.ClickException(
                f"Adding {line_count} notes; pass --yes-really to confirm bulk action."
            )
        if not yes:
            click.confirm(
                f"Add {line_count} notes from {from_file} to deck '{deck}' "
                f"using '{note_type}'?",
                abort=True,
            )
        with open_collection(
            COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="cards-add"
        ) as col:
            result = bulk_add_tsv(
                col,
                from_file,
                deck=deck,
                note_type=note_type,
                fields=field_names,
                tags=tags,
            )
        emit(result)
        return

    if not fields_in:
        raise click.ClickException("Provide at least one --field KEY=VALUE")
    fields: dict[str, str] = {}
    for item in fields_in:
        if "=" not in item:
            raise click.ClickException(f"Invalid --field (expected KEY=VALUE): {item}")
        k, v = item.split("=", 1)
        fields[k] = v
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="cards-add"
    ) as col:
        result = add_note(
            col, deck=deck, note_type=note_type, fields=fields, tags=tags
        )
    emit(result)


@cards.command("retag")
@click.option("--ids", required=True, help="Comma-separated card IDs")
@click.option("--add", multiple=True, help="Tag to add; repeatable")
@click.option("--remove", multiple=True, help="Tag to remove; repeatable")
@click.option("--yes", is_flag=True, envvar="ANKIWEB_CLI_YES")
def cards_retag(
    ids: str, add: tuple[str, ...], remove: tuple[str, ...], yes: bool
) -> None:
    """Add and/or remove tags on the notes underlying given cards."""
    if not add and not remove:
        raise click.ClickException("Provide at least one --add or --remove tag")
    try:
        card_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError as e:
        raise click.ClickException(f"Invalid card IDs: {e}") from e
    if not card_ids:
        emit({"status": "noop", "reason": "no card ids"})
        return
    if not yes:
        click.confirm(
            f"Retag notes for {len(card_ids)} cards "
            f"(+{list(add)} -{list(remove)})?",
            abort=True,
        )
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="cards-retag"
    ) as col:
        result = retag_cards(col, card_ids, add=list(add), remove=list(remove))
    emit(result)


@cards.command("delete")
@click.option("--ids", required=True, help="Comma-separated card IDs")
@click.option("--yes", is_flag=True, envvar="ANKIWEB_CLI_YES")
@click.option("--yes-really", is_flag=True)
def cards_delete(ids: str, yes: bool, yes_really: bool) -> None:
    """Delete cards by ID (orphan notes are removed too)."""
    try:
        card_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError as e:
        raise click.ClickException(f"Invalid card IDs: {e}") from e
    if not card_ids:
        emit({"status": "noop", "reason": "no card ids", "deleted": 0})
        return
    if len(card_ids) > 50 and not yes_really:
        raise click.ClickException(
            f"Deleting {len(card_ids)} cards; pass --yes-really to confirm bulk action."
        )
    if not yes:
        click.confirm(f"Delete {len(card_ids)} cards (and orphan notes)?", abort=True)
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="cards-delete"
    ) as col:
        result = delete_cards(col, card_ids)
    emit(result)


@main.group()
def backup() -> None:
    """Manage local backup snapshots."""


@backup.command("list")
def backup_list() -> None:
    """List backup snapshots, newest first."""
    rows = list_backups(BACKUPS_DIR)
    emit(rows, human=lambda rs: "\n".join(
        f"{r['name']:<60} {r['size']:>10}  op={r['op'] or '-'}"
        for r in rs
    ) or "(no backups)")


@backup.command("restore")
@click.argument("name")
@click.option("--yes", is_flag=True, envvar="ANKIWEB_CLI_YES")
def backup_restore(name: str, yes: bool) -> None:
    """Replace the live collection with a backup snapshot."""
    target = COLLECTION_FILE
    if not yes:
        click.confirm(
            f"Overwrite {target} with backup '{name}'? "
            "(current collection is snapshotted first)",
            abort=True,
        )
    result = restore_backup(BACKUPS_DIR, name, target)
    emit(result)


@main.command("audit")
def audit_cmd() -> None:
    """Compute deck/duplicate/note-type audit report."""
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        report = audit_collection(col)
    emit(report)


if __name__ == "__main__":
    main()
