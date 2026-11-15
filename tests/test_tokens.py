"""Tests for :mod:`ctx.tokens` — the token estimate heuristic."""

from __future__ import annotations

from ctx.tokens import estimate_tokens


def test_empty_string_is_zero():
    assert estimate_tokens("") == 0


def test_single_short_string_is_at_least_one():
    assert estimate_tokens("a") >= 1
    assert isinstance(estimate_tokens("a"), int)


def test_longer_text_estimates_strictly_more():
    short = estimate_tokens("short text")
    long_ = estimate_tokens("short text " + "x" * 200)
    assert long_ > short


def test_estimates_grow_with_length():
    prev = estimate_tokens("")
    for i in range(1, 300):
        cur = estimate_tokens("a" * i)
        assert cur >= prev, f"estimate not monotonic at length {i}"
        prev = cur


def test_whitespace_still_counts():
    assert estimate_tokens("   ") >= 1


def test_newlines_are_counted():
    assert estimate_tokens("\n".join(["hello"] * 20)) > estimate_tokens("hello")


def test_multiline_code_structure_counts():
    code = "\n".join(f"line_{i} = {i}" for i in range(50))
    assert estimate_tokens(code) > estimate_tokens(code.splitlines()[0])


def test_result_is_positive_integer_for_any_nonempty_input():
    for text in ("x", "a b c", "\n", " " * 5, "λ"):
        val = estimate_tokens(text)
        assert isinstance(val, int)
        assert val >= 1
