# Contributing to ctx

Thanks for your interest. The project is small and intentionally dependency-light, so keep that in mind when you open PRs: every feature should earn its place.

## Reporting a bug

Open an issue with:

- the command you ran (flags and all),
- the output — or the first ~40 lines if it is huge,
- the tree of the repo you ran it on (`ctx --no-tree -o - .` is the fastest way to share one, or just `tree` if you have it),
- your Python version and OS, if it might matter.

"it doesn't work" without a repro can't be acted on; the default context is that you ran `ctx` on a directory and it misbehaved.

## Proposing a feature

Open an issue describing the problem you are solving, not just the flag you want. `ctx` replaces nothing and competes with nothing — a good feature is one that stays useful offline, adds no heavyweight dependency, and fits the "one file, tree, contents, token estimate" model.

## Development setup

Requires Python 3.9+.

```bash
git clone https://github.com/devanshx/ctx
cd ctx
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

That installs the package in editable mode plus pytest, pytest-cov, and ruff. Python is not installed? Then run without installing:

```bash
export PYTHONPATH="$PWD/src"
python3 -m ctx --help
```

## Running tests and lint

```bash
python -m pytest
python -m ruff check .
```

Both must pass on your branch. Tests live in `tests/` and are collected by pytest from the pyproject config.

## What a good PR looks like

- Small. A single focused change is far easier to review and land.
- Tested. Add or update a test in `tests/` alongside the change; no test, no merge.
- Lint-clean (`python -m ruff check .`).
- Documented if it changes the CLI surface — update `--help` text, the README, and the CHANGELOG entry.

Open the PR against `main`, describe what changed and why, and reference the issue it closes if there is one.
