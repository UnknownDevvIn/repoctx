# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-11-15

### Changed

- `ctx` with no `-o/--output` now writes `ctx.md` in the current directory,
  instead of printing to stdout. `-o FILE` writes that file as before, and
  `-o -` still prints to stdout explicitly.
- The output file is now excluded from packing even when it is the default
  `ctx.md`, so repeated runs never include their own previous output.

## [0.1.0] - 2026-11-15

### Added

- `ctx` CLI with a `root` argument (defaults to the current directory) and an
  `-o/--output` flag for writing the context file instead of stdout.
- Repository walker that honors `.gitignore` and `.ctxignore` at every level of
  the tree, following git semantics, and always skips `.git`, `.svn`, `.hg`,
  `.ctx`, `__pycache__`, and `.mypy_cache`.
- `--include` and `--exclude` filter flags using pathspec glob syntax
  (`exclude` wins over `include`), plus `--max-size` to skip large files.
- Binary-file detection via NUL-byte sniffing; binary files are listed in the
  context document but their content is omitted.
- Token estimation with no external tokenizer dependency; accurate enough to
  budget context window fits and slightly conservative.
- Markdown renderer emitting a directory tree, a files/bytes/tokens summary,
  and one fenced block per source file with a language hint.
- `--max-tokens` to stop early once the running token estimate exceeds a limit,
  `--no-tree` to omit the ASCII tree, and `--json` for a machine-readable
  summary.
- `python -m ctx` support, `ctx --version`, and a `py.typed` marker.
