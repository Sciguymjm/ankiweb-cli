# anki-cli

Headless CLI for AnkiWeb, primarily driven by Claude. The design spec lives in the sibling `hindi` repo at `docs/superpowers/specs/2026-05-23-anki-cli-design.md`.

## Setup

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/anki-cli --help
```

## First run

```bash
anki-cli config set username YOUR_ANKIWEB_EMAIL
anki-cli login          # prompts for password, stores in OS keyring
anki-cli sync           # pulls collection to ./collection/
```
