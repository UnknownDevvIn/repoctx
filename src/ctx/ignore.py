"""Gitignore-aware path filtering built on ``pathspec``.

A :class:`IgnoreMatcher` loads ``.gitignore`` (and optionally a private
``.ctxignore``) files from the tree it is asked about, keyed by their directory,
so nested files follow git's semantics: patterns are relative to the file that
carries them, and a deeper file's decision wins over a shallower one's.
"""

from __future__ import annotations

from pathlib import Path

from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitIgnoreSpecPattern


class IgnoreMatcher:
    """Matches repository paths against accumulated ignore rules."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._dirs: dict[str, PathSpec] = {}  # os-relpath -> lazily built spec

    def _spec_for(self, rel_dir: str) -> PathSpec:
        spec = self._dirs.get(rel_dir)
        if spec is not None:
            return spec
        lines: list[str] = []
        base = self.root if not rel_dir else self.root / rel_dir
        for name in (".gitignore", ".ctxignore"):
            candidate = base / name
            if candidate.is_file():
                _append_lines(candidate, lines)
        spec = PathSpec.from_lines(GitIgnoreSpecPattern, lines)
        self._dirs[rel_dir] = spec
        return spec

    def check(self, rel_path: str, is_dir: bool = False) -> bool:
        """True when ``rel_path`` should be excluded from the context file.

        Evaluates the rule files deepest-first: the decision of a ``.gitignore``
        in the path's own directory (or its nearest ancestor) wins over a higher
        one, mirroring git. Later lines within one file override earlier ones
        (handled by pathspec).
        """
        dir_chain: list[str] = []
        parent = rel_path.rsplit("/", 1)[0] if "/" in rel_path else ""
        while True:
            dir_chain.append(parent)
            if not parent:
                break
            parent = parent.rsplit("/", 1)[0] if "/" in parent else ""

        for rule_dir in dir_chain:  # deepest -> root
            spec = self._spec_for(rule_dir)
            candidate = rel_path[len(rule_dir) + 1 :] if rule_dir else rel_path
            if is_dir and not candidate.endswith("/"):
                candidate += "/"
            result = spec.check_file(candidate)
            if result.include is not None:
                return result.include
        return False


def _append_lines(file: Path, lines: list[str]) -> None:
    try:
        text = file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(line)
