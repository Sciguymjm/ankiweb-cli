# ankiweb-cli

Headless command-line interface for AnkiWeb.

Built on the official [`anki`](https://pypi.org/project/anki/) Python library,
so the sync protocol and collection format match Anki desktop. Everything is
driven from the shell. No GUI, no review interface. Useful for inspecting your
collection, syncing without opening the desktop app, and automating bulk
operations on decks and cards.

## Features

- `sync`: pull from AnkiWeb, push local changes. Handles AnkiWeb's
  load-balancer shard redirects so first-time `--full download` works
  headlessly.
- `decks list`, `cards list`. `cards list` accepts Anki's full search syntax
  (`deck:"X"`, `tag:y`, `is:new`, ...).
- `decks delete`, `decks suspend`, `decks unsuspend`. Recursive by default for
  suspend/unsuspend; `--recursive` for delete. Bulk operations require
  `--yes-really` to confirm.
- `gen reverse`: add a reverse card template to the note type used by a deck.
  Anki regenerates cards for existing notes automatically.
- `audit`: deck inventory, one-direction-only template detection, duplicate
  detection across decks, note-type inventory.
- Auto-backup before every write. Timestamped `.anki2` snapshots.
- OS keyring for the AnkiWeb password via the `keyring` package. No plaintext
  credentials on disk.

Still on the roadmap: `decks rename`/`move`/`merge`, `cards add`/`retag`/`delete`.

## Install

Requires Python 3.11+.

```bash
git clone https://github.com/Sciguymjm/ankiweb-cli
cd ankiweb-cli
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/ankiweb-cli --help
```

## First-time setup

```bash
ankiweb-cli config set username YOUR_ANKIWEB_EMAIL
ankiweb-cli login                # prompts for password; stored in OS keyring
ankiweb-cli sync --full download # bootstraps local collection from AnkiWeb
ankiweb-cli decks list
ankiweb-cli audit
```

After bootstrap, ordinary `ankiweb-cli sync` handles incremental changes in
both directions.

## Data location

The CLI keeps state in a per-user directory chosen by OS convention:

- Linux/BSD: `$XDG_DATA_HOME/ankiweb-cli` (or `~/.local/share/ankiweb-cli`)
- macOS: `~/Library/Application Support/ankiweb-cli`
- Windows: `%APPDATA%\ankiweb-cli`

Override with `ANKIWEB_CLI_HOME=/path/to/dir`. Inside:

```
collection/           your synced collection
backups/              automatic snapshots (one per mutating operation)
cache/                generated artifacts
config.toml           username and endpoint
```

## Confirmations

Mutating commands prompt before running. Two ways to skip:

- `--yes` / `ANKIWEB_CLI_YES=1` skips the basic prompt.
- `--yes-really` is additionally required when an operation affects more than
  50 cards (deck delete, deck suspend).

## License

[GNU AGPL v3.0](LICENSE). Required because the upstream `anki` library is AGPL,
and any program that links it must be AGPL when distributed.

## Status

Pre-1.0. Sync, read-only inspection, deck deletion and suspension, and reverse
template generation are implemented and tested (35+ tests against an isolated
collection). The remaining mutating commands are next.
