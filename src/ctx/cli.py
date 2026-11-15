"""Command-line interface for ctx."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ctx import __version__
from ctx.binary import is_nul_in_text
from ctx.render import render_document
from ctx.tokens import estimate_tokens
from ctx.walker import discover

# Fixed output we always emit per file section; used to make --max-tokens honest.
_PER_FILE_OVERHEAD = 8  # "### `rel`", blank, fence ×2, blank — roughly


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ctx",
        description=(
            "Package a repository into a single, LLM-ready context file with "
            "a tree, file contents, and a token estimate."
        ),
        epilog="Exit status: 0 on success, 1 when the root is missing or nothing is packed.",
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="directory to pack (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="write to FILE (default: ctx.md; use - for stdout)",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="only include paths matching GLOB (repeatable; pathspec syntax)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="exclude paths matching GLOB (repeatable; pathspec syntax)",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        metavar="BYTES",
        help="skip files larger than this many bytes",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        metavar="N",
        help="pack files until the estimated output reaches N tokens",
    )
    parser.add_argument(
        "--no-tree",
        action="store_true",
        help="omit the ASCII tree section",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print a JSON summary instead of the document",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ctx {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"ctx: {args.root}: no such directory", file=sys.stderr)
        return 1

    exclude = list(args.exclude)
    output_path: Path | None
    if args.output == "-":
        output_path = None  # explicit stdout
    elif args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = (Path.cwd() / "ctx.md").resolve()
    if output_path is not None:
        # Don't pack the file we are about to write (or one from a previous run).
        try:
            excluded_above = output_path.relative_to(root.resolve())
            exclude.append(str(excluded_above))
        except ValueError:
            pass  # output lives outside the packed tree; nothing to do

    files = discover(
        root,
        include=tuple(args.include),
        exclude=tuple(exclude),
        max_size=args.max_size,
    )

    if args.json:
        picked = _trim_to_tokens(files, args.max_tokens) if args.max_tokens is not None else files
        sys.stdout.write(_summary_json(root, picked) + "\n")
        return 0

    if args.max_tokens is not None:
        files = _trim_to_tokens(files, args.max_tokens)
    if not files:
        print("ctx: nothing to pack", file=sys.stderr)
        return 1

    doc = render_document(root.name or "repo", files, include_tree=not args.no_tree)
    return _emit(doc, output_path)


def _emit(doc: str, output: Path | None) -> int:
    if output is None:
        sys.stdout.write(doc + "\n")
        return 0
    try:
        output.write_text(doc, encoding="utf-8")
    except OSError as exc:
        print(f"ctx: cannot write {output}: {exc}", file=sys.stderr)
        return 1
    return 0


def _trim_to_tokens(files, limit: int) -> list:
    """Keep files while the estimated output stays under ``limit``.

    The estimate covers the emitted text a file actually produces: its body
    tokens plus the fixed per-section overhead (heading, blank lines, fences).
    Binary files cost only the overhead and are always kept, so they stay
    listed with their omission note. The first file always ships even if it
    alone exceeds ``limit`` — packing nothing because one file is big helps
    nobody.
    """
    kept: list = []
    body_tokens = 0
    for info in files:
        cost = _PER_FILE_OVERHEAD
        if not info.binary:
            text = _read(info)
            if not text:
                continue
            cost += estimate_tokens(text)
        if body_tokens + cost > limit:
            # Even the next file alone exceeds the remaining budget, so no
            # further file can fit; what fits so far is kept (possibly nothing,
            # when a single big file alone exceeds the whole limit).
            break
        kept.append(info)
        body_tokens += cost
    return kept


def _summary_json(root: Path, files) -> str:
    total_bytes = sum(f.size for f in files)
    tokens = sum(_PER_FILE_OVERHEAD + estimate_tokens(_read(f)) for f in files if not f.binary)
    payload = {
        "root": str(root),
        "files": [{"path": f.rel, "bytes": f.size, "binary": f.binary} for f in files],
        "count": len(files),
        "bytes": total_bytes,
        "tokens": tokens,
    }
    return json.dumps(payload, indent=2)


def _read(info) -> str:
    try:
        text = info.path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""
    return "" if is_nul_in_text(text) else text


if __name__ == "__main__":
    raise SystemExit(main())
