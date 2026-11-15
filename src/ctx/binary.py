"""Heuristic detection of binary files.

No file signature database: a file is treated as binary when its first chunk
contains a NUL byte, which is reliable for the formats programmers actually
commit (images, archives, compiled objects, fonts, audio). UTF-16 text and some
encodings can contain NUL, but they are vanishingly rare in repository trees.
"""

from __future__ import annotations

from pathlib import Path

_SNIFF_BYTES = 8192
_NUL = b"\x00"


def is_nul_in_text(text: str) -> bool:
    """True when decoded ``text`` still contains a NUL character.

    ``is_binary`` sniffs only the first chunk, so a NUL past that window would
    otherwise slip through; checking the decoded text is the definitive gate.
    """
    return _NUL.decode("ascii") in text


def is_binary(path: Path) -> bool:
    """Return True when ``path`` looks like a binary file.

    Reads at most :data:`_SNIFF_BYTES` bytes. Files shorter than that are judged
    on their whole content. A missing file answers False (the caller handles it).
    """
    try:
        with path.open("rb") as handle:
            chunk = handle.read(_SNIFF_BYTES)
    except OSError:
        return False
    return _NUL in chunk
