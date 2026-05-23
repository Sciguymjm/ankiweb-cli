# Changelog

## 0.2.0

Completes the CRUD surface for decks and cards, plus a way to use the
auto-created backups.

### Added

- `decks rename` — rename a deck; subdecks under the old prefix are carried
  along automatically.
- `decks move` — move specific cards to another deck (destination created if
  missing).
- `decks merge` — consolidate one or more source decks into a destination
  deck; sources are removed afterwards.
- `cards add` — add a single note via `--field KEY=VALUE` flags, or bulk-add
  from a TSV with `--from-file` and `--fields-order`.
- `cards retag` — add and/or remove tags on the notes underlying the given
  cards. Only notes whose tag set actually changes are written.
- `cards delete` — delete cards by ID; orphan notes are removed too.
- `backup list` — list `.anki2` snapshots in the backups directory, newest
  first, with parsed operation labels.
- `backup restore` — replace the live collection with a named snapshot. The
  current collection is snapshotted to `collection-<ts>-pre-restore.anki2`
  first, so a botched restore is undoable.

### Tests

48 tests, all passing on Python 3.11 and 3.12 in CI.

## 0.1.0

Initial release.

- Headless AnkiWeb sync via the official `anki` library, including the
  load-balancer shard redirect handling needed for `--full upload/download`
  to work without Anki desktop.
- Read-only commands: `decks list`, `cards list`, `audit`.
- Mutating commands: `decks delete`, `decks suspend`, `decks unsuspend`.
- Additive generator: `gen reverse`.
- Auto-backup of the collection file before every mutation.
- AnkiWeb password stored in the OS keyring.
- XDG-conventional per-user data directory, overridable with
  `ANKIWEB_CLI_HOME`.
