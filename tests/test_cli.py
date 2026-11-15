"""End-to-end CLI tests for ``python -m ctx`` / the ``ctx`` console command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ctx import __version__
from ctx.cli import main


def make_repo(tmp_path: Path, files: dict) -> Path:
    """Write ``{rel: bytes|str}`` under ``tmp_path`` and return it."""
    for rel, data in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            p.write_bytes(data)
        else:
            p.write_text(data)
    return tmp_path


SIMPLE = {"ctx": "def helper():\n    return 42\n", "notes.txt": "hello\n"}


# --- exit codes & basic streaming -------------------------------------


def test_missing_root_exits_1(capsys):
    rc = main(["/definitely/not/a/real/ctx/root"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "no such directory" in err


def test_empty_repo_exits_1(tmp_path, capsys):
    rc = main([str(tmp_path)])
    assert rc == 1
    assert "nothing to pack" in capsys.readouterr().err


def test_dash_output_goes_to_stdout(tmp_path, capsys):
    make_repo(tmp_path, SIMPLE)
    rc = main([str(tmp_path), "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "`ctx`" in out  # a file in the packed doc
    assert "— context" in out  # the H1 header


def test_default_root_is_cwd(tmp_path, capsys, monkeypatch):
    make_repo(tmp_path, {"hello.txt": "hi\n"})
    monkeypatch.chdir(tmp_path)
    rc = main(["-o", "-"])
    assert rc == 0
    assert "hello.txt" in capsys.readouterr().out


# --- output file ------------------------------------------------------


def test_output_file_is_written(tmp_path, capsys):
    make_repo(tmp_path, SIMPLE)
    dest = tmp_path / "packed.md"
    rc = main([str(tmp_path), "-o", str(dest)])
    out = capsys.readouterr().out
    assert rc == 0
    assert out == ""  # nothing on stdout when writing to a file
    text = dest.read_text()
    assert "## Files" in text
    assert "`ctx`" in text


def test_default_writes_ctx_md_in_cwd(tmp_path, capsys, monkeypatch):
    make_repo(tmp_path, {"hello.txt": "hi\n"})
    monkeypatch.chdir(tmp_path)
    rc = main([])  # no -o: should write ctx.md, not stdout
    out = capsys.readouterr().out
    assert rc == 0
    assert out == ""  # nothing printed to stdout
    created = tmp_path / "ctx.md"
    assert created.is_file()
    assert "## Files" in created.read_text()
    assert "hello.txt" in created.read_text()


# --- include / exclude ------------------------------------------------


def test_include_filters_files(tmp_path, capsys):
    make_repo(tmp_path, {"a.py": "print(1)\n", "b.txt": "hi\n"})
    rc = main([str(tmp_path), "--include", "*.py", "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "a.py" in out
    assert "b.txt" not in out


def test_exclude_removes_files(tmp_path, capsys):
    make_repo(tmp_path, {"keep.py": "x\n", "drop.py": "y\n"})
    rc = main([str(tmp_path), "--exclude", "drop.py", "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "keep.py" in out
    assert "drop.py" not in out


# --- no-tree ----------------------------------------------------------


def test_no_tree_removes_tree_section(tmp_path, capsys):
    make_repo(tmp_path, SIMPLE)
    rc = main([str(tmp_path), "--no-tree", "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "## Tree" not in out
    assert "## Files" in out


def test_tree_present_by_default(tmp_path, capsys):
    make_repo(tmp_path, SIMPLE)
    main([str(tmp_path), "-o", "-"])
    out = capsys.readouterr().out
    assert "## Tree" in out


# --- JSON summary -----------------------------------------------------


def test_json_summary_parses_with_expected_keys(tmp_path, capsys):
    make_repo(tmp_path, {"a.py": "print(1)\n", "b.txt": "xy\n", "img.bin": b"\x00\x01"})
    rc = main([str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert {"count", "tokens", "files", "root", "bytes"} <= set(payload)
    assert payload["count"] == 3
    assert len(payload["files"]) == 3
    for f in payload["files"]:
        assert {"path", "bytes", "binary"} <= set(f)
    assert payload["tokens"] >= 1
    assert payload["bytes"] >= 1


def test_json_summary_on_empty_repo_succeeds(tmp_path, capsys):
    rc = main([str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 0
    assert payload["files"] == []
    assert payload["tokens"] == 0


# --- max-tokens -------------------------------------------------------


def test_max_tokens_trims_tail(tmp_path, capsys):
    make_repo(tmp_path, {"a.txt": "x" * 200, "b.txt": "y" * 200})
    rc = main([str(tmp_path), "--max-tokens", "100", "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "a.txt" in out
    assert "b.txt" not in out


def test_max_tokens_zero_drops_everything(tmp_path, capsys):
    make_repo(tmp_path, {"a.txt": "x" * 100})
    rc = main([str(tmp_path), "--max-tokens", "0"])
    assert rc == 1
    assert "nothing to pack" in capsys.readouterr().err


def test_max_tokens_large_keeps_everything(tmp_path, capsys):
    make_repo(tmp_path, {"a.txt": "x\n", "b.txt": "y\n"})
    rc = main([str(tmp_path), "--max-tokens", "10000", "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "a.txt" in out
    assert "b.txt" in out


# --- version ----------------------------------------------------------


def test_version_prints_and_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"ctx {__version__}"


# --- edge cases -------------------------------------------------------


def test_binary_file_gets_omission_note(tmp_path, capsys):
    make_repo(tmp_path, {"img.bin": b"\x00\x01\x02"})
    rc = main([str(tmp_path), "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "img.bin" in out
    assert "> binary — content omitted" in out


def test_undecodable_utf8_gets_omission_note(tmp_path, capsys):
    make_repo(tmp_path, {"weird.txt": b"\xff\xfe hey"})
    rc = main([str(tmp_path), "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "weird.txt" in out
    assert "> binary — content omitted" in out


def test_filename_with_spaces(tmp_path, capsys):
    make_repo(tmp_path, {"my file.txt": "hi\n"})
    rc = main([str(tmp_path), "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "my file.txt" in out
    assert "hi" in out


def test_ctxignore_only_tree(tmp_path, capsys):
    make_repo(
        tmp_path,
        {".ctxignore": "*.secret\n", "a.secret": "s\n", "b.txt": "b\n"},
    )
    rc = main([str(tmp_path), "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "b.txt" in out
    assert "a.secret" not in out


# --- regressions found in review --------------------------------------


def test_output_file_is_not_packed_into_itself(tmp_path):
    make_repo(tmp_path, {"src.py": "x = 1\n"})
    out = tmp_path / "readme.md"
    rc1 = main([str(tmp_path), "-o", str(out)])
    assert rc1 == 0
    # A second run must not discover the file the first run wrote.
    rc2 = main([str(tmp_path), "-o", str(out)])
    doc = out.read_text()
    assert rc2 == 0
    assert doc.count("###") == 1  # only src.py, not readme.md
    assert "readme.md" not in doc.split("## Files", 1)[1]


def test_missing_output_directory_returns_1(capsys):
    rc = main(["/tmp", "-o", "/definitely/not/a/real/dir/out.md"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "cannot write" in err and "ctx:" in err


def test_json_max_tokens_zero_still_trims(tmp_path, capsys):
    make_repo(tmp_path, {"a.txt": "x" * 100})
    rc = main([str(tmp_path), "--json", "--max-tokens", "0"])
    out = capsys.readouterr().out
    assert rc == 0
    assert json.loads(out)["count"] == 0


def test_binary_file_listed_under_max_tokens(tmp_path, capsys):
    make_repo(tmp_path, {"img.bin": b"\x00\x01", "note.txt": "hi\n"})
    rc = main([str(tmp_path), "--max-tokens", "100000", "-o", "-"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "img.bin" in out
    assert "binary — content omitted" in out
