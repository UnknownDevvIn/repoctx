"""Tests for :mod:`ctx.walker` — file discovery and filtering."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ctx.walker import FileInfo, discover


def _infos(root, **kwargs):
    return discover(root, **kwargs)


# --- FileInfo shape ---------------------------------------------------


def test_fileinfo_is_frozen_dataclass():
    import dataclasses

    assert dataclasses.is_dataclass(FileInfo)
    with pytest.raises(dataclasses.FrozenInstanceError):
        FileInfo(rel="a", path=Path("/x"), size=1, binary=False).rel = "b"


def test_fileinfo_fields(clean):
    p = clean.write("dir/file.txt", "hello")
    (info,) = _infos(clean.root)
    assert info.rel == "dir/file.txt"
    assert info.rel == "dir/file.txt"
    assert isinstance(info.size, int) and info.size == p.stat().st_size
    assert info.binary is False
    assert isinstance(info.path, Path)
    assert info.path.is_absolute()


# --- gitignore integration --------------------------------------------


def test_default_gitignore_excludes_logs(tree):
    tree.write("app.log")
    tree.write("app.txt")
    tree.write("x/main.py")
    assert tree.packed() == ["app.txt", "x/main.py"]


def test_negation_reincludes_via_walker(tree):
    tree.gitignore("*.log\n!keep.log\n")
    tree.write("drop.log")
    tree.write("keep.log")
    assert tree.packed() == ["keep.log"]


def test_dir_only_ignore_prunes_whole_dir(tree):
    tree.gitignore("build/\n")
    tree.write("build/obj/main.o")
    tree.write("build/x.txt")
    tree.write("src/main.c")
    assert tree.packed() == ["src/main.c"]


def test_nested_gitignore_overrides_in_walker(tree):
    tree.gitignore("*.txt\n")
    tree.gitignore("!keep.txt\n", rel="sub/.gitignore")
    tree.write("sub/keep.txt")
    tree.write("sub/other.txt")
    tree.write("top.txt")
    assert tree.packed() == ["sub/.gitignore", "sub/keep.txt"]


def test_anchored_pattern_via_walker(tree):
    tree.gitignore("/root.txt\n")
    tree.write("root.txt")
    tree.write("sub/root.txt")
    assert tree.packed() == ["sub/root.txt"]


def test_double_star_via_walker(tree):
    tree.gitignore("doc/**/tmp.txt\n")
    tree.write("doc/tmp.txt")
    tree.write("doc/a/b/c/tmp.txt")
    tree.write("doc/a/b/c/keep.txt")
    assert tree.packed() == ["doc/a/b/c/keep.txt"]


def test_ctxignore_only_tree(tree):
    tree.gitignore(".ctxignore-tests\n")  # replace default *.log
    tree.gitignore("*.secret\n", rel=".ctxignore")
    tree.write("a.secret")
    tree.write("a.txt")
    assert tree.packed() == ["a.txt"]


# --- always-skipped directories ---------------------------------------


def test_skips_default_vcs_and_cache_dirs(clean):
    for name in (".git", ".svn", ".hg", ".ctx", "__pycache__", ".mypy_cache"):
        path = clean.write(f"{name}/inner.txt")
        assert path.exists()
    clean.write("src/real.txt")
    result = sorted(f.rel for f in _infos(clean.root))
    assert result == ["src/real.txt"]


# --- dotfiles ---------------------------------------------------------


def test_hidden_dotfiles_are_included_by_default(clean):
    clean.write(".env", "KEY=value\n")
    clean.write(".hidden", "x\n")
    clean.write("visible.txt", "x\n")
    result = sorted(f.rel for f in _infos(clean.root))
    assert ".env" in result
    assert ".hidden" in result
    assert "visible.txt" in result


def test_dotfile_can_be_ignored_like_anything_else(clean):
    clean.gitignore(".env\n")
    clean.write(".env", "KEY=value\n")
    clean.write("visible.txt", "x\n")
    result = sorted(f.rel for f in _infos(clean.root))
    assert ".env" not in result
    assert "visible.txt" in result


# --- include / exclude ------------------------------------------------


def test_include_glob_filters_to_matches(clean):
    clean.write("a.py", "print(1)\n")
    clean.write("b.txt", "x\n")
    clean.write("sub/c.py", "print(2)\n")
    result = sorted(f.rel for f in _infos(clean.root, include=("*.py",)))
    assert result == ["a.py", "sub/c.py"]


def test_exclude_glob_drops_matches(clean):
    clean.write("a.py", "print(1)\n")
    clean.write("b.txt", "x\n")
    result = sorted(f.rel for f in _infos(clean.root, exclude=("*.py",)))
    assert result == ["b.txt"]


def test_exclude_wins_over_include(clean):
    clean.write("a.py", "x\n")
    clean.write("bad.py", "x\n")
    clean.write("c.txt", "x\n")
    result = sorted(f.rel for f in _infos(clean.root, include=("*.py",), exclude=("bad.py",)))
    assert result == ["a.py"]


def test_empty_include_matches_nothing(clean):
    clean.write("a.txt", "x\n")
    result = _infos(clean.root, include=("*.zzz",))
    assert result == []


# --- max_size ---------------------------------------------------------


def test_max_size_drops_files_over_limit(clean):
    clean.write("small.txt", "abc")  # 3 bytes
    clean.write("large.txt", "abcd")  # 4 bytes
    result = [(f.rel, f.size) for f in _infos(clean.root, max_size=3)]
    assert result == [("small.txt", 3)]


def test_max_size_boundary_is_inclusive(clean):
    clean.write("exact.txt", "abcd")  # exactly 4 bytes
    result = [f.rel for f in _infos(clean.root, max_size=4)]
    assert result == ["exact.txt"]


def test_max_size_none_keeps_everything(clean):
    clean.write("a.txt", "a" * 1000)
    clean.write("b.txt", "b" * 100)
    assert len(_infos(clean.root)) == 2


# --- binary detection -------------------------------------------------


def test_binary_file_listed_with_binary_flag(clean):
    clean.write("img.bin", b"\x00\x01\x02")
    clean.write("text.txt", "just text\n")
    result = {(f.rel, f.binary) for f in _infos(clean.root)}
    assert ("img.bin", True) in result
    assert ("text.txt", False) in result


def test_skip_binary_false_marks_nothing_binary(clean):
    clean.write("img.bin", b"\x00\x01\x02")
    result = [(f.rel, f.binary) for f in _infos(clean.root, skip_binary=False)]
    assert result == [("img.bin", False)]


# --- sorting ----------------------------------------------------------


def test_sorting_is_case_insensitive_then_raw(clean):
    clean.write("B.txt", "x\n")
    clean.write("a.txt", "x\n")
    clean.write("A.txt", "x\n")
    result = [f.rel for f in _infos(clean.root)]
    # lower-cased tie between "A.txt" and "a.txt" breaks on the raw path
    assert result == ["A.txt", "a.txt", "B.txt"]


def test_sorting_is_case_insensitive_across_dirs(clean):
    clean.write("zNotes.txt", "x\n")
    clean.write("a/deep.txt", "x\n")
    clean.write("A-toplevel", "x\n")
    result = [f.rel for f in _infos(clean.root)]
    assert result == sorted(result, key=lambda r: (r.lower(), r))


# --- symlinks ---------------------------------------------------------


def test_symlinks_not_followed_and_file_symlinks_listed(clean):
    real_dir = clean.root / "real"
    real_dir.mkdir()
    (real_dir / "inner.txt").write_text("x")
    (clean.root / "file.txt").write_text("x")
    try:
        os.symlink(real_dir, clean.root / "linkdir")
        os.symlink(clean.root / "file.txt", clean.root / "linkfile.txt")
    except (OSError, NotImplementedError, PermissionError):
        pytest.skip("symlinks unsupported in this environment")
    result = sorted(f.rel for f in _infos(clean.root))
    assert "linkdir/inner.txt" not in result  # dir symlink not followed
    assert "real/inner.txt" in result
    assert "linkfile.txt" in result  # file symlink listed as a file


# --- misc -------------------------------------------------------------


def test_empty_root_yields_no_files(clean):
    assert _infos(clean.root) == []


def test_missing_include_dirs_do_not_crash(tree):
    assert tree.packed(include=("src/**",)) == []


def test_filename_with_spaces(clean):
    clean.write("my file.txt", "hello\n")
    result = [f.rel for f in _infos(clean.root)]
    assert result == ["my file.txt"]
