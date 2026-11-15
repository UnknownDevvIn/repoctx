"""Map file extensions to fenced-code-block language hints.

Everything falls back to ``None``, which produces an unlabelled fence. Only the
extensions people hit often are listed; adding more is trivially safe.
"""

from __future__ import annotations

_MAP = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".fish": "fish",
    ".ps1": "powershell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".jsonc": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".tex": "latex",
    ".lua": "lua",
    ".pl": "perl",
    ".ex": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".clj": "clojure",
    ".zig": "zig",
    ".dart": "dart",
    ".sol": "solidity",
    ".dockerfile": "dockerfile",
    ".docker": "dockerfile",
    ".tf": "hcl",
    ".hcl": "hcl",
}


def language_for(relative_path: str) -> str | None:
    """Return a language hint for ``relative_path``, or None."""
    for suffix, hint in _MAP.items():
        if relative_path.lower().endswith(suffix):
            return hint
    lower = relative_path.lower()
    if lower in {"makefile", "dockerfile"}:
        return lower
    if lower in {"gemfile", "rakefile"}:
        return "ruby"
    return None
