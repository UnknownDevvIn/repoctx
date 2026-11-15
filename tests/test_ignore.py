"""Unit tests for :mod:`ctx.ignore` — gitignore / .ctxignore semantics."""

from __future__ import annotations

from ctx.ignore import IgnoreMatcher


def _matcher(tree, text: str, rel: str = ".gitignore") -> IgnoreMatcher:
    tree.gitignore(text, rel)
    return IgnoreMatcher(tree.root)


# --- plain rules -------------------------------------------------------


def test_plain_pattern_ignores_file(tree):
    m = _matcher(tree, "*.log\n")
    assert m.check("app.log") is True
    assert m.check("app.py") is False


def test_plain_pattern_matches_nested_paths(tree):
    m = _matcher(tree, "*.log\n")
    assert m.check("a/b/c.log") is True
    assert m.check("a/b/c.py") is False


def test_unmatched_path_returns_false(tree):
    m = _matcher(tree, "*.log\n")
    assert m.check("README.me") is False
    assert m.check("") is False


# --- negation ----------------------------------------------------------


def test_negation_reincludes_file(tree):
    m = _matcher(tree, "*.log\n!keep.log\n")
    assert m.check("drop.log") is True
    assert m.check("keep.log") is False


def test_negation_works_inside_subdirectory(tree):
    m = _matcher(tree, "*.tmp\n!keep.tmp\n")
    assert m.check("sub/drop.tmp") is True
    assert m.check("sub/keep.tmp") is False


# --- directory-only rules ---------------------------------------------


def test_dir_only_pattern_matches_directory(tree):
    m = _matcher(tree, "build/\n")
    assert m.check("build", is_dir=True) is True
    assert m.check("build/obj/main.o") is True
    assert m.check("src/main.c") is False


def test_dir_only_pattern_does_not_match_file_with_same_name(tree):
    m = _matcher(tree, "build/\n")
    # a *file* named "build" (no trailing slash in the candidate) is not ignored
    assert m.check("build") is False


def test_plain_dir_name_matches_directory_too(tree):
    m = _matcher(tree, "node_modules\n")
    assert m.check("node_modules", is_dir=True) is True
    assert m.check("node_modules/pkg/x.js") is True
    assert m.check("src/index.js") is False


# --- anchored patterns ------------------------------------------------


def test_anchored_pattern_only_matches_root(tree):
    m = _matcher(tree, "/root.txt\n")
    assert m.check("root.txt") is True
    assert m.check("sub/root.txt") is False


def test_slash_pattern_is_anchored_to_its_own_directory(tree):
    tree.gitignore("*.txt\n")
    tree.gitignore("out/data.txt\n", rel="gen/.gitignore")
    m = IgnoreMatcher(tree.root)
    assert m.check("gen/out/data.txt") is True
    assert m.check("out/data.txt") is True  # root spec: *.txt
    assert m.check("gen/out/keep.md") is False


# --- nested .gitignore (deepest wins) ---------------------------------


def test_nested_gitignore_overrides_root(tree):
    tree.gitignore("*.txt\n")
    tree.gitignore("!keep.txt\n", rel="sub/.gitignore")
    m = IgnoreMatcher(tree.root)
    assert m.check("sub/keep.txt") is False
    assert m.check("sub/other.txt") is True
    assert m.check("top.txt") is True  # root rule still applies outside sub/


def test_deepest_gitignore_wins_for_sibling_dirs(tree):
    tree.gitignore("*.md\n")
    tree.gitignore("!keep.md\n", rel="a/b/.gitignore")
    m = IgnoreMatcher(tree.root)
    assert m.check("a/b/keep.md") is False
    assert m.check("a/b/other.md") is True  # overridden by deeper file? no rule
    assert m.check("a/keep.md") is True  # root rule applies one level up


def test_root_gitignore_still_counts_when_nested_has_no_matching_pattern(tree):
    # A nested .gitignore that provides no decision (comment-only) lets the
    # parent rule apply, mirroring git.
    tree.gitignore("*.tmp\n")
    tree.gitignore("# only a comment\n", rel="nested/.gitignore")
    m = IgnoreMatcher(tree.root)
    assert m.check("nested/x.tmp") is True
    assert m.check("x.tmp") is True


# --- ** patterns ------------------------------------------------------


def test_double_star_matches_multiple_levels(tree):
    m = _matcher(tree, "doc/**/tmp.txt\n")
    assert m.check("doc/tmp.txt") is True
    assert m.check("doc/a/b/c/tmp.txt") is True
    assert m.check("doc/a/b/c/keep.txt") is False


# --- comments and blank lines ----------------------------------------


def test_comments_and_blank_lines_are_skipped(tree):
    m = _matcher(tree, "# leading comment\n\n# another\n*.bak\n")
    assert m.check("notes.bak") is True
    assert m.check("notes.txt") is False


def test_leading_whitespace_is_part_of_pattern(tree):
    # gitignore leading whitespace is significant; ctx passes raw lines through.
    m = _matcher(tree, "   *.xy\n")
    assert m.check("a.xy") is False


# --- later lines override earlier -------------------------------------


def test_later_line_overrides_earlier_in_same_file(tree):
    m = _matcher(tree, "*.txt\n!keep.txt\n")
    assert m.check("keep.txt") is False
    assert m.check("other.txt") is True


# --- .ctxignore -------------------------------------------------------


def test_ctxignore_is_consulted(tree):
    m = _matcher(tree, "secret*\n", rel=".ctxignore")
    assert m.check("secret.key") is True
    assert m.check("secrets/cron") is True
    assert m.check("other.txt") is False


def test_gitignore_and_ctxignore_rules_accumulate(tree):
    tree.gitignore("*.log\n")
    tree.gitignore("*.cache\n", rel=".ctxignore")
    m = IgnoreMatcher(tree.root)
    assert m.check("a.log") is True
    assert m.check("b.cache") is True
    assert m.check("c.txt") is False
