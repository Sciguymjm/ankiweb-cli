import json
import sys

import click

from anki_cli.config import load_config, save_config
from anki_cli.paths import CONFIG_FILE, ensure_dirs


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


if __name__ == "__main__":
    main()
