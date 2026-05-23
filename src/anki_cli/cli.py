import getpass
import json
import sys

import click

from anki_cli import sync as sync_mod
from anki_cli.collection import open_collection
from anki_cli.commands.cards import list_cards
from anki_cli.commands.decks import list_decks
from anki_cli.config import Config, load_config, save_config
from anki_cli.output import emit
from anki_cli.paths import BACKUPS_DIR, COLLECTION_FILE, CONFIG_FILE, ensure_dirs


@click.group()
@click.version_option()
def main() -> None:
    """Headless CLI for AnkiWeb."""


@main.group()
def config() -> None:
    """View and edit anki-cli config."""


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
        raise click.ClickException("Run `anki-cli config set username <email>` first.")
    password = getpass.getpass("AnkiWeb password: ")
    _, endpoint = sync_mod.login_and_get_hkey(cfg.username, password, cfg.endpoint)
    sync_mod.store_password(cfg.username, password)
    save_config(Config(username=cfg.username, endpoint=endpoint), CONFIG_FILE)
    emit({"ok": True, "endpoint": endpoint})


@main.command("sync")
def sync_cmd() -> None:
    """Pull from AnkiWeb, push local changes."""
    ensure_dirs()
    cfg = load_config(CONFIG_FILE)
    if not cfg.username:
        raise click.ClickException("Not configured. Run `anki-cli login` first.")
    password = sync_mod.get_password(cfg.username)
    if not password:
        raise click.ClickException("No password in keyring. Run `anki-cli login`.")
    hkey, endpoint = sync_mod.login_and_get_hkey(
        cfg.username, password, cfg.endpoint
    )
    with open_collection(
        COLLECTION_FILE, backups_dir=BACKUPS_DIR, write=True, op="sync"
    ) as col:
        result = sync_mod.do_sync(col, hkey, endpoint)
    emit(
        {
            "pulled": result.pulled,
            "pushed": result.pushed,
            "endpoint": result.new_endpoint or endpoint,
            "required_full_sync": result.required_full_sync,
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


if __name__ == "__main__":
    main()
