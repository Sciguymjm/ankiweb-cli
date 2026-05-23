import getpass
import json
import sys

import click

from ankiweb_cli import sync as sync_mod
from ankiweb_cli.collection import open_collection
from ankiweb_cli.commands.audit import audit_collection
from ankiweb_cli.commands.cards import list_cards
from ankiweb_cli.commands.decks import (
    count_cards_in_deck,
    delete_deck,
    list_decks,
)
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
@click.option("--yes", is_flag=True, envvar="ANKI_CLI_YES")
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


@main.group()
def cards() -> None:
    """Operations on cards."""


@cards.command("list")
@click.option("--query", "-q", default="", help="Anki search syntax")
@click.option("--deck", default=None)
@click.option("--limit", default=50, type=int)
def cards_list(query: str, deck: str | None, limit: int) -> None:
    full_query = query
    if deck:
        full_query = f'deck:"{deck}" {query}'.strip()
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        rows = list_cards(col, query=full_query, limit=limit)
    emit(rows)


@main.command("audit")
def audit_cmd() -> None:
    """Compute deck/duplicate/note-type audit report."""
    with open_collection(COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=False) as col:
        report = audit_collection(col)
    emit(report)


if __name__ == "__main__":
    main()
