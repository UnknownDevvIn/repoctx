# ctx

Package a repository into a single, LLM-ready context file.

`ctx` walks a directory and emits one markdown file containing an ASCII tree of
the repo, the contents of every source file (fenced with language hints), and a
token estimate — so you can paste a whole repository into an LLM prompt, or
point an agent at it, and the model sees structure and code together.

## What it looks like

Running `ctx` on this repo (tree trimmed for the README; the header counts are real):

````text
# repo — context

- files: **26** · **67650 bytes** · ~**19838 tokens**

## Tree

```text
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── release.yml
│   └── FUNDING.yml
├── src/
│   └── ctx/
│       ├── __init__.py
│       ├── __main__.py
│       ├── ...
│       └── walker.py
├── tests/
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_ignore.py
│   ├── test_render.py
│   ├── test_tokens.py
│   └── test_walker.py
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── MANIFEST.in
├── pyproject.toml
└── README.md
```
````

## Features

- **One file out.** Directory tree, file contents, and a token estimate in a
  single markdown document — ready to paste into a prompt.
- **Gitignore-aware.** Follows `.gitignore` (and `.ctxignore`) at every level
  of the tree, with git's semantics: deeper rule files win.
- **Binary-safe.** Binary files are detected and listed, but their content is
  omitted instead of corrupting the document.
- **Token-aware.** `--max-tokens` stops early once the running estimate crosses
  the limit, so the output fits your context window.
- **Filterable.** `--include` / `--exclude` with repeatable pathspec globs, and
  `--max-size` to skip files that are too big.
- **Offline and light.** The only runtime dependency is `pathspec`.

## Install

Requires Python 3.10+.

```bash
pipx install .
```

Or with plain pip:

```bash
pip install .
```

Either installs a `ctx` command (it also runs as `python -m ctx`).

## Usage

```text
usage: ctx [-h] [-o FILE] [--include GLOB] [--exclude GLOB] [--max-size BYTES]
           [--max-tokens N] [--no-tree] [--json] [--version]
           [root]
```

- `root` — directory to pack. Defaults to the current directory. The header
  uses the directory's name (or `repo` when the name is empty, e.g. `.`).
- `-o FILE, --output FILE` — write to a file instead of stdout. `-o -` means
  stdout explicitly.
- `--include GLOB` / `--exclude GLOB` — keep or drop paths matching a glob
  (repeatable; pathspec syntax). Both are applied after ignore filtering, and
  `--exclude` wins over `--include`.
- `--max-size BYTES` — skip files larger than this many bytes.
- `--max-tokens N` — stop once the emitted text reaches N tokens.
- `--no-tree` — omit the ASCII tree section; just the files.
- `--json` — print a machine-readable summary (file list, counts, bytes,
  tokens) instead of the document.

### With LLMs

The output is self-contained, so driving an LLM is two steps:

```bash
# write it to a file for an agent that can read files
ctx -o ctx.md

# or just paste stdout straight into the prompt
ctx | head -c 20000
```

Point the model at `ctx.md` ("this is my whole repo, read it") or paste it
directly — the tree tells it the layout, the fenced blocks give it the code,
and the token estimate tells you whether it fits.

## How it decides what to include

- **Gitignore semantics.** `.gitignore` files are read at every directory and
  applied to relative paths; a deeper `.gitignore`'s decision wins over a
  shallower one's, and later lines override earlier ones. A private
  `.ctxignore` file is honored the same way, for rules you do not want to
  commit to git.
- **Always-skipped directories.** `.git`, `.svn`, `.hg`, `.ctx`,
  `__pycache__`, and `.mypy_cache` are always skipped.
- **Binary omission.** A file is treated as binary when its first 8 KB contain
  a NUL byte — images, archives, compiled objects. It is still listed in the
  document, but with a note instead of content.
- **Files, not directories.** Only regular files are packed; empty directories
  and directory symlinks do not appear in the tree.

## Philosophy

Offline-first. There is no telemetry, no network call, and no tokenizer — token
counts come from a small local heuristic that errs high, which is the safe
direction for context budgeting. The dependency list stays minimal
(`pathspec` is the only runtime dependency) and the output is plain markdown
you can read, diff, and paste anywhere.

## Development

```bash
git clone <your fork>/ctx
cd ctx
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

- Run tests: `python -m pytest`
- Lint: `python -m ruff check .` (config and dev extras live in `pyproject.toml`)

No need to install to poke at the CLI:

```bash
export PYTHONPATH="$PWD/src"
python3 -m ctx --help
```

## Testing & compatibility

Honest status of what is and isn't verified:

- **Tested on:** Linux, Python 3.12 — 106 automated tests pass (`pytest`),
  `ruff` clean, wheel + sdist build clean, `twine check` passes. Edge cases
  covered by tests: nested/overriding `.gitignore`, negation, directory-only
  patterns, filenames with spaces, undecodable and binary files, oversized
  files, symlinks (not followed for dirs), backtick-fences inside file bodies,
  and `--max-tokens` / `--json` behavior.
- **Expected but not yet verified:** macOS and Windows, and Python 3.10–3.11.
  The code is pure Python + `pathspec` with no OS-specific calls, so it
  *should* run anywhere, but only Linux/3.12 has been exercised. The GitHub
  Actions matrix (`ci.yml`) runs 3.10–3.12 on Linux for every push; wider
  platform testing is welcome via PRs / CI runs.
- **Not verified at all:** any real PyPI publication (needs a maintainer token).

If you hit a platform you use that isn't green, open an issue with your OS,
Python version, and the error — that's the fastest way this list gets shorter.

## License

[MIT](LICENSE) © 2026 Kamran
