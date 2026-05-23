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
- `audit`: deck inventory, one-direction-only template detection, duplicate
  detection across decks, note-type inventory.
- Auto-backup before every write. Timestamped `.anki2` snapshots under
  `backups/`.
- OS keyring for the AnkiWeb password via the `keyring` package. No plaintext
  credentials on disk.

Mutating commands (`decks rename/move/merge/delete`, `cards add/retag/delete`)
are on the roadmap.

## Install

Requires Python 3.11+.

```bash
git clone https://github.com/<you>/ankiweb-cli
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

After bootstrap, ordinary `ankiweb-cli sync` handles incremental changes in both
directions.

## Layout

```
src/ankiweb_cli/         package source
  cli.py              click entry point
  collection.py       Collection context manager + auto-backup
  sync.py             AnkiWeb sync (login, normal, full upload/download)
  config.py           TOML config load/save
  paths.py            repo-root-relative path constants
  output.py           formatted output helper
  commands/           subcommand implementations (decks, cards, audit)

collection/           your synced collection (gitignored)
backups/              automatic snapshots (gitignored)
cache/                generated artifacts (gitignored)
```

## License

[GNU AGPL v3.0](LICENSE). Required because the upstream `anki` library is AGPL,
and any program that links it must be AGPL when distributed.

## Status

Pre-1.0. Sync and read-only commands are implemented and tested. Mutating
commands are in progress.
