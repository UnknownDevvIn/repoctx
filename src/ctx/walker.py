"""Repository file discovery: walk, filter, and produce FileInfo records."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitIgnoreSpecPattern

from ctx.binary import is_binary
from ctx.ignore import IgnoreMatcher

# Always skipped, even with --no-ignore.
_EXCLUDED_DIRS = {
    ".git",
    ".svn",
    ".hg",
    ".ctx",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
}


@dataclass(frozen=True)
class FileInfo:
    """One file that made it into the context file."""

    rel: str  # POSIX-ish path relative to the repo root
    path: Path  # absolute path on disk
    size: int  # bytes
    binary: bool  # detected as binary (content excluded from output)


def discover(
    root: Path,
    *,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    max_size: int | None = None,
    skip_binary: bool = True,
) -> list[FileInfo]:
    """Walk ``root`` and return the files that belong in the context file.

    Honors ``.gitignore`` everywhere in the tree. ``include`` and ``exclude``
    are pathspec-style patterns applied to POSIX relative paths after ignore
    filtering; ``exclude`` wins over ``include``. Files larger than ``max_size``
    bytes are dropped. ``skip_binary`` keeps binary files in the list (so the
    reader knows they were omitted); when false, binary content is read anyway.
    """
    root = Path(root).resolve()
    ignore = IgnoreMatcher(root)
    include_spec = PathSpec.from_lines(GitIgnoreSpecPattern, include) if include else None
    exclude_spec = PathSpec.from_lines(GitIgnoreSpecPattern, exclude) if exclude else None

    files: list[FileInfo] = []
    for dirpath, dirnames, filenames in _walk(root, ignore):
        # Prune ignored directories in place so we never descend into them.
        kept: list[str] = []
        for name in dirnames:
            rel = _rel(root, dirpath, name)
            if name in _EXCLUDED_DIRS or ignore.check(rel, is_dir=True):
                continue
            kept.append(name)
        dirnames[:] = kept

        for name in filenames:
            abs_path = Path(dirpath) / name
            rel = _rel(root, dirpath, name)
            if _blocked(rel, include_spec, exclude_spec):
                continue
            if ignore.check(rel, is_dir=False):
                continue
            try:
                size = abs_path.stat().st_size
            except OSError:
                continue
            if max_size is not None and size > max_size:
                continue
            binary = is_binary(abs_path) if skip_binary else False
            files.append(FileInfo(rel=rel, path=abs_path, size=size, binary=binary))

    files.sort(key=lambda f: (f.rel.lower(), f.rel))
    return files


def _walk(root: Path, ignore: IgnoreMatcher):
    """os.walk-compatible generator; ``ignore`` is consulted by ``discover``."""
    stack = [str(root)]
    while stack:
        dirpath = stack.pop()
        try:
            with os.scandir(dirpath) as it:
                names = sorted((e.name for e in it), key=str.lower)
        except OSError:
            continue
        dirnames: list[str] = []
        filenames: list[str] = []
        for name in names:
            child = os.path.join(dirpath, name)
            try:
                if os.path.isdir(child) and not os.path.islink(child):
                    dirnames.append(name)
                elif os.path.isfile(child):
                    filenames.append(name)
            except OSError:
                continue
        yield dirpath, dirnames, filenames
        for name in reversed(dirnames):
            stack.append(os.path.join(dirpath, name))


def _rel(root: Path, dirpath: str, name: str) -> str:
    if dirpath == str(root):
        return name
    relative = str(Path(dirpath).relative_to(root))
    if os.sep == "\\":  # Windows paths are backslash-separated; normalise to /
        relative = relative.replace("\\", "/")
    return relative + "/" + name


def _blocked(rel: str, include: PathSpec | None, exclude: PathSpec | None) -> bool:
    if exclude is not None and exclude.match_file(rel):
        return True
    return include is not None and not include.match_file(rel)
