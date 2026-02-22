"""Condition evaluators for IF / WHILE / UNTIL.

Supported functions
-------------------
IMAGE_MATCH "template.png" [threshold 0.85] [region x y w h]
PIXEL_COLOR x y r g b [tolerance]
WINDOW_EXISTS "Window Title"
FILE_EXISTS "path/to/file"
TRUE  / FALSE  (literals)

Variable references and arithmetic/comparison expressions are handled by
delegating to expression.eval_expr() when the condition doesn't match any
known function name.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.core.variable_store import VariableStore

from src.core.condition_funcs import (
    image_match, pixel_color, window_exists, file_exists,
)

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

LogFn = Callable[[str, str], None]   # (level, message)


def eval_condition(
    tokens:        list[str],
    templates_dir: Path,
    log:           LogFn | None = None,
    variables:     "VariableStore | None" = None,
) -> bool:
    """Evaluate a condition token list and return True or False.

    For known function names (IMAGE_MATCH, etc.) ``tokens[0]`` is the
    function name and ``tokens[1:]`` are arguments.

    For everything else the full token list is evaluated as an expression
    via expression.eval_expr().
    """
    _log = log or (lambda lvl, msg: None)

    if not tokens:
        return False

    func = tokens[0].upper()
    args = tokens[1:]

    if func in ("TRUE", "1"):
        return True
    if func in ("FALSE", "0"):
        return False
    if func == "IMAGE_MATCH":
        return image_match(args, templates_dir, _log)
    if func == "PIXEL_COLOR":
        return pixel_color(args, _log)
    if func == "WINDOW_EXISTS":
        return window_exists(args, _log)
    if func == "FILE_EXISTS":
        return file_exists(args, _log)

    # Fallback: treat the token list as a boolean expression
    from src.core.expression import eval_expr
    from src.core.variable_store import VariableStore as _VS
    vs = variables if variables is not None else _VS()
    result = eval_expr(tokens, vs, log=_log)
    if isinstance(result, bool):
        return result
    try:
        return bool(result)
    except Exception:
        _log("WARNING", f"Condition could not be converted to bool: {tokens!r}")
        return False
