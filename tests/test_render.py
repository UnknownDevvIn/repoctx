"""Tests for :mod:`ctx.render` — ASCII tree and markdown document."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ctx.render import build_tree, render_document
from ctx.walker import FileInfo


def _info(tmp_path: Path, rel: str, data="content\n", binary: bool = False) -> FileInfo:
    """Write ``rel`` under ``tmp_path`` and wrap it in a FileInfo."""
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data)
    return FileInfo(rel=rel, path=path, size=path.stat().st_size, binary=binary)


def _infos(tmp_path: Path, *rels_and_data) -> list[FileInfo]:
    files = []
    for item in rels_and_data:
        if isinstance(item, FileInfo):
            files.append(item)
            continue
        rel, data = item
        files.append(_info(tmp_path, rel, data))
    return files


# --- build_tree -------------------------------------------------------


def test_build_tree_single_file():
    assert build_tree(["file.txt"]) == "└── file.txt"


def test_build_tree_empty_returns_dot():
    assert build_tree([]) == "."


def test_build_tree_nested_dirs_and_connectors():
    tree = build_tree(["a/b/c.txt", "a/b/d.txt"])
    assert tree == ("└── a/\n    └── b/\n        ├── c.txt\n        └── d.txt")


def test_build_tree_dirs_suffixed_with_slash():
    tree = build_tree(["src/main.py"])
    assert "src/" in tree
    assert "main.py" in tree


def test_build_tree_sorts_case_insensitively():
    tree = build_tree(["B.txt", "a.txt"])
    assert tree.index("a.txt") < tree.index("B.txt")


def test_build_tree_flat_files_shape():
    assert build_tree(["a.txt", "b.txt"]) == "├── a.txt\n└── b.txt"


def test_tree_dirs_before_files_contract():
    """Per the documented contract, directories must sort ahead of files."""
    tree = build_tree(["readme.txt", "src/main.py"])
    assert tree.index("src/") < tree.index("readme.txt")


# --- render_document structure ----------------------------------------


def test_render_has_exactly_one_h1(tmp_path):
    doc = render_document("myrepo", _infos(tmp_path, ("a.py", "print(1)\n")))
    h1s = [ln for ln in doc.splitlines() if re.match(r"^# ", ln)]
    assert len(h1s) == 1
    assert h1s[0] == "# myrepo — context"


def test_render_has_tree_and_files_sections(tmp_path):
    doc = render_document("r", _infos(tmp_path, ("a.py", "print(1)\n")))
    assert "## Tree" in doc
    assert "```text" in doc
    assert "## Files" in doc


def test_render_every_file_gets_a_section(tmp_path):
    files = _infos(
        tmp_path,
        ("a.py", "x\n"),
        ("b/c.txt", "y\n"),
    )
    doc = render_document("r", files)
    assert "### `a.py`" in doc
    assert "### `b/c.txt`" in doc


def test_render_token_line_format(tmp_path):
    doc = render_document("r", _infos(tmp_path, ("a.py", "print(1)\n")))
    match = re.search(r"- files: \*\*\d+\*\* · \*\*\d+ bytes\*\* · ~\*\*\d+ tokens\*\*", doc)
    assert match, f"token line not found in:\n{doc}"
    assert "files: **1**" in doc
    assert "bytes**" in doc
    assert "tokens**" in doc


def test_render_include_tree_false_omits_tree_section(tmp_path):
    doc = render_document("r", _infos(tmp_path, ("a.py", "x\n")), include_tree=False)
    assert "## Tree" not in doc
    assert "## Files" in doc


def test_render_file_content_in_fence(tmp_path):
    f = _info(tmp_path, "a.py", "print(1)\n")
    doc = render_document("r", [f], include_tree=False)
    assert "```python" in doc
    assert "print(1)" in doc
    assert doc.count("```") == 2  # an opening and a closing fence for one file


# --- binary / undecodable handling ------------------------------------


def test_render_binary_file_gets_omission_note(tmp_path):
    f = _info(tmp_path, "img.bin", b"\x00\x01\x02", binary=True)
    doc = render_document("r", [f])
    assert "> binary — content omitted" in doc
    assert "### `img.bin`" in doc


def test_render_binary_content_not_emitted(tmp_path):
    f = _info(tmp_path, "img.bin", b"\x00\x01\x02", binary=True)
    doc = render_document("r", [f])
    body = doc.split("### `img.bin`", 1)[1]
    assert "\x00" not in body


def test_render_undecodable_file_gets_omission_not_crash(tmp_path):
    # Non-NUL bytes that are not valid UTF-8: binary sniff says "text",
    # so decoding is what fails.
    f = _info(tmp_path, "weird.txt", b"\xff\xfe\xfd hi")
    doc = render_document("r", [f])
    assert "> binary — content omitted" in doc
    assert "### `weird.txt`" in doc


def test_render_skips_missing_file_without_crash(tmp_path):
    f = FileInfo(rel="gone.txt", path=tmp_path / "gone.txt", size=3, binary=False)
    doc = render_document("r", [f])
    assert "> binary — content omitted" in doc


# --- language hint ----------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "hint"),
    [
        ("app.py", "python"),
        ("lib/main.rs", "rust"),
        ("data.json", "json"),
        ("page.html", "html"),
        ("notes.md", "markdown"),
        ("Dockerfile", "dockerfile"),
        ("Makefile", "makefile"),
    ],
)
def test_render_language_hint_for_known_extensions(tmp_path, rel, hint):
    f = _info(tmp_path, rel, "x\n")
    doc = render_document("r", [f])
    assert f"```{hint}" in doc


def test_render_no_language_hint_for_unknown_extension(tmp_path):
    f = _info(tmp_path, "blob.unknown", "x\n")
    doc = render_document("r", [f], include_tree=False)
    block = doc.split("### `blob.unknown`", 1)[1]
    assert "\n```\nx\n```" in block  # bare fence, no language hint
    assert "`blob.unknown`" in doc
    assert "```python" not in doc


# --- content handling -------------------------------------------------


def test_render_content_is_rstripped(tmp_path):
    f = _info(tmp_path, "a.py", "print(1)\n\n\n")
    doc = render_document("r", [f])
    block = doc.split("### `a.py`", 1)[1]
    assert "```python\nprint(1)\n```" in block
    assert "print(1)\n\n\n" not in block


def test_render_sections_follow_file_order(tmp_path):
    files = _infos(
        tmp_path,
        ("z_first.py", "z\n"),
        ("a_second.py", "a\n"),
    )
    doc = render_document("r", files)
    assert doc.index("### `z_first.py`") < doc.index("### `a_second.py`")


def test_render_empty_file_list_still_well_formed(tmp_path):
    doc = render_document("r", [])
    assert doc.startswith("# r — context")
    assert "## Files" in doc
    assert doc.count("###") == 0


def test_render_backtick_fence_inside_content_keeps_document_well_formed(tmp_path):
    """A triple-backtick line inside a file body must not close the file's fence.

    The fence is widened (one backtick beyond the longest run in the body), so the
    inner ``` line stays inside the fenced block; the closing fence must be longer
    than the inner run, and "before"/"after" must both end up inside the block.
    """
    f = _info(tmp_path, "note.md", "before\n```\nafter\n")
    doc = render_document("r", [f])
    body_section = doc.split("### `note.md`", 1)[1]
    # The block opens and closes with a >=4-backtick fence; between them the
    # inner ``` line is just body text ("markdown" is the language hint).
    assert body_section.lstrip("\n").startswith("````markdown\n")
    assert "before\n```\nafter\n" in body_section
    assert body_section.rstrip("\n").endswith("````")
