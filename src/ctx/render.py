"""Render the tailored context file: an ASCII tree plus per-file sections."""

from __future__ import annotations

from ctx.binary import is_nul_in_text
from ctx.language import language_for
from ctx.tokens import estimate_tokens
from ctx.walker import FileInfo

_BOX = {"pipe": "│   ", "mid": "├── ", "last": "└── ", "pad": "    "}


def build_tree(rels: list[str]) -> str:
    """Return an ASCII directory tree for the given POSIX relative paths."""
    root: dict = {}
    for rel in rels:
        node = root
        for part in rel.split("/"):
            node = node.setdefault(part, {})
    lines: list[str] = []

    def walk(node: dict, prefix: str) -> None:
        # Directories (non-empty children dicts) first, then files, each
        # case-insensitively.
        items = sorted(node.items(), key=lambda kv: (not bool(kv[1]), kv[0].lower()))
        for i, (name, child) in enumerate(items):
            is_last = i == len(items) - 1
            stem = prefix + (_BOX["last"] if is_last else _BOX["mid"]) + name
            if child:
                lines.append(stem + "/")
                extension = _BOX["pad"] if is_last else _BOX["pipe"]
                walk(child, prefix + extension)
            else:
                lines.append(stem)

    walk(root, "")
    return "\n".join(lines) or "."


def _fence_for(body: str) -> str:
    """A code fence delimiter that ``body``'s backtick runs cannot break.

    Uses one backtick more than the longest run in the body (min 3, max 8 — a
    run that long is beyond any reasonable source file, and capping avoids
    pathological fence sizes). ``body`` may instead be omitted with a note.
    """
    longest = 0
    run = 0
    for char in body:
        if char == "`":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return "`" * min(max(longest + 1, 3), 8)


def render_document(
    root_name: str,
    files: list[FileInfo],
    *,
    include_tree: bool = True,
) -> str:
    """Build the whole markdown document as a string."""
    total_bytes = sum(f.size for f in files)

    # Read file bodies once, so binary/undecodable files are handled in a single
    # pass and the token estimate matches exactly what gets emitted.
    bodies: dict[str, str] = {}
    skipped: dict[str, str] = {}
    text_parts: list[str] = []
    for info in files:
        if info.binary:
            skipped[info.rel] = "binary — content omitted"
            continue
        try:
            text = info.path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped[info.rel] = "binary — content omitted"
            continue
        if is_nul_in_text(text):
            skipped[info.rel] = "binary — content omitted"
            continue
        bodies[info.rel] = text
        text_parts.append(text)
    token_estimate = estimate_tokens("\n".join(text_parts))

    out: list[str] = [
        f"# {root_name} — context",
        "",
        f"- files: **{len(files)}** · **{total_bytes} bytes** · ~**{token_estimate} tokens**",
        "",
    ]
    if include_tree:
        out += ["## Tree", "", "```text", build_tree([f.rel for f in files]), "```", ""]

    out += ["## Files", ""]
    for info in files:
        out.append(f"### `{info.rel}`")
        out.append("")
        if info.rel in skipped:
            out.append(f"> {skipped[info.rel]}")
            out.append("")
            continue
        fence = _fence_for(bodies[info.rel])
        out.append(f"{fence}{language_for(info.rel) or ''}")
        out.append(bodies[info.rel].rstrip("\n"))
        out.append(fence)
        out.append("")
    return "\n".join(out)
