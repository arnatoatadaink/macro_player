"""Macro language parser — tokenizer and syntax-sugar expander.

Responsibilities
----------------
- Strip inline comments  (# …) while preserving # inside quoted strings
- Split lines into [COMMAND, arg1, arg2, …] tokens
- Apply syntax-sugar aliases from settings.ini [COMMANDS] section
- Upper-case command tokens for case-insensitive matching

Phase 4 additions (planned): AST builder for IF/LOOP/CALL/WHILE blocks.
"""
from __future__ import annotations

import shlex

from src.core.prefix import COMMENT_PREFIX
from src.core.executor import is_commands

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def strip_comment(line: str) -> str:
    """Return line with trailing comment (# …) removed.

    A '#' that appears inside a double-quoted string is kept.
    """
    in_str = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_str = not in_str
        elif ch == COMMENT_PREFIX and not in_str:
            return line[:i]
    return line


def tokenize(line: str) -> list[str]:
    """Split one source line into a token list.

    Returns an empty list for blank/comment-only lines.
    Quoted arguments (e.g. ``TYPE "hello world"``) are kept as one token
    without surrounding quotes.
    """
    stripped = strip_comment(line).strip()
    if not stripped:
        return []
    try:
        return shlex.split(stripped, posix=True)
    except ValueError:
        # Malformed quotes — fall back to simple split
        return stripped.split()


def expand_sugar(tokens: list[str], sugar_map: dict[str, str]) -> list[str]:
    """Replace an alias command with its canonical equivalent.

    ``sugar_map`` keys and values must already be upper-case
    (see SettingsManager.syntax_sugar).

    Examples
    --------
    >>> expand_sugar(["POS", "100", "200"], {"POS": "MOUSE_POS"})
    ['MOUSE_POS', '100', '200']
    """
    if not tokens:
        return tokens
    cmd = tokens[0].upper()
    canonical = sugar_map.get(cmd, cmd)
    if is_commands(canonical):
        return [canonical] + tokens[1:]
    return tokens

def parse_lines(text: str, sugar_map: dict[str, str]) -> list[list[str]]:
    """Convenience: tokenize every line and expand sugar aliases.

    Returns a list of non-empty token lists (blank/comment lines omitted).
    """
    result: list[list[str]] = []
    for raw in text.splitlines():
        tokens = expand_sugar(tokenize(raw), sugar_map)
        if tokens:
            result.append(tokens)
    return result
