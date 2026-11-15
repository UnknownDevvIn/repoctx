"""Rough token estimation without any tokenizer dependency.

``ctx`` aims to be dependency-light and offline. A real BPE tokenizer (tiktoken)
is an extra dependency most users will not want, so this module approximates
tokens from a mix of characters and whitespace-delimited words. It is calibrated
toward English prose and code and overestimates by ~10-20% rather than
underestimating, which is the safe direction for context budgeting.
"""

from __future__ import annotations

import math


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens ``text`` contains.

    Uses a blended heuristic: about one token per 4.0 characters, nudged upward
    by whitespace-delimited words. The result is an integer >= 1.
    """
    if not text:
        return 0
    chars = len(text)
    words = len(text.split())
    # Code mixes in long identifiers and symbols; prose is denser per word. The
    # 4.0 chars/token base handles long tokens, and 1.1 words/token proxy keeps
    # short-word prose honest.
    estimate = chars / 4.0 + words * 0.4
    return max(1, math.ceil(estimate))
