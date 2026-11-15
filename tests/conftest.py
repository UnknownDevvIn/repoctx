"""Shared fixtures for the ctx test suite.

Every test runs inside a fresh ``tmp_path`` directory; nothing touches the
real repository.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Root .gitignore used by the default ``tree`` fixture. Exercises comments,
# blank lines and a plain ``*.log`` ignore in one go.
DEFAULT_GITIGNORE = "# ctx test fixture — comment line\n\n*.log\n"


class Tree:
    """Helper bound to a temporary repo root."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, rel: str, data="content\n") -> Path:
        """Create a file (nesting directories as needed) and return its path."""
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data)
        return path

    def gitignore(self, text: str, rel: str = ".gitignore") -> Path:
        """Write a (possibly replacing) ignore file."""
        return self.write(rel, text)

    def packed(self, **kwargs):
        """Run ``discover`` and return rel paths minus the ignore bookkeeping
        files, so assertions focus on the tree content."""
        from ctx.walker import discover

        ignore_files = {".gitignore", ".ctxignore"}
        return sorted(f.rel for f in discover(self.root, **kwargs) if f.rel not in ignore_files)


@pytest.fixture
def tree(tmp_path: Path) -> Tree:
    """A tmp repo whose root ``.gitignore`` carries a comment, a blank line and
    the rule ``*.log`` — the canonical "gitignore'd tree" fixture."""
    t = Tree(tmp_path)
    t.gitignore(DEFAULT_GITIGNORE)
    return t


@pytest.fixture
def clean(tmp_path: Path) -> Tree:
    """A tmp repo with no ignore rules at all (unless the test adds one)."""
    return Tree(tmp_path)
