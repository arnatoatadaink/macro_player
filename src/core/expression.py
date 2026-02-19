"""Expression evaluator and built-in FUNCTION caller for Phase 5.

Expression evaluation
---------------------
Uses Python's eval() with variable substitution.  Only safe operations
are permitted (no builtins).  Supports:
  - Numeric literals:        42, 3.14
  - String literals:         hello  (shlex already stripped quotes)
  - Variable references:     #var  → substituted with its current value
  - Arithmetic:              #a + #b * 2
  - Comparison:              #count == 0,  #x >= 100
  - Logical (case-insensitive): #a > 0 AND #b < 10,  NOT #flag

Built-in FUNCTION calls (assignable via  #var = FUNCTION args)
--------------------------------------------------------------
RANDOM min max          → random integer in [min, max]
GET_TIME                → current Unix timestamp (float)
GET_PIXEL_COLOR x y     → "r g b" string of the screen pixel
CLIPBOARD_GET           → current clipboard text
IMAGE_MATCH / PIXEL_COLOR / WINDOW_EXISTS / FILE_EXISTS
                        → same bool as condition.py (reuses that module)
"""
from __future__ import annotations

import random
import re
import time
from pathlib import Path
from typing import Any, Callable

from src.core.variable_store import VariableStore
from src.core.prefix import VARIABLE_PREFIX,VARIABLE_REGPREFIX

LogFn = Callable[[str, str], None]

# ---------------------------------------------------------------------------
# Variable substitution
# ---------------------------------------------------------------------------

_VAR_RE = re.compile(VARIABLE_REGPREFIX+r"[A-Za-z_]\w*")

_SAFE_GLOBALS: dict = {"__builtins__": {}}


def _sub_vars(expr: str, variables: VariableStore) -> str:
    """Replace every varname with its repr()-formatted value."""
    def sub(m: re.Match) -> str:
        val = variables.get(m.group(0), 0)
        if isinstance(val, bool):
            return "True" if val else "False"
        if isinstance(val, str):
            return repr(val)
        return str(val)
    return _VAR_RE.sub(sub, expr)


def _coerce(s: str) -> Any:
    """Convert a single-token string to the most natural Python type."""
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    low = s.lower()
    if low == "true":  return True
    if low == "false": return False
    return s   # treat as plain string


# ---------------------------------------------------------------------------
# Expression evaluator (public)
# ---------------------------------------------------------------------------

def eval_expr(
    tokens:    list[str],
    variables: VariableStore,
    log:       LogFn | None = None,
) -> Any:
    """Evaluate a token list as a typed expression.

    Single token  → type coercion (int / float / bool / str / variable).
    Multi-token   → Python eval() after variable substitution.
    """
    _log = log or (lambda lvl, msg: None)
    if not tokens:
        return 0
    if len(tokens) == 1:
        tok = tokens[0]
        if tok.startswith(VARIABLE_PREFIX):
            return variables.get(tok, 0)
        return _coerce(tok)

    # Multi-token: substitute variables then eval
    expr = " ".join(tokens)
    expr = re.sub(r"\bAND\b", "and", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bOR\b",  "or",  expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bNOT\b", "not", expr, flags=re.IGNORECASE)
    expr = _sub_vars(expr, variables)

    try:
        return eval(compile(expr, "<macro_expr>", "eval"), _SAFE_GLOBALS, {})
    except Exception as exc:
        _log("WARNING", f"Expression error {expr!r}: {exc}")
        return 0


# ---------------------------------------------------------------------------
# Built-in FUNCTION caller (for #var = FUNCTION …)
# ---------------------------------------------------------------------------

# Functions whose first token should trigger function-call mode
FUNCTION_NAMES: frozenset[str] = frozenset({
    "IMAGE_MATCH", "PIXEL_COLOR", "WINDOW_EXISTS", "FILE_EXISTS",
    "GET_TIME", "RANDOM", "CLIPBOARD_GET", "GET_PIXEL_COLOR",
})


def call_function(
    func_name:     str,
    args:          list[str],
    templates_dir: Path,
    variables:     VariableStore,
    log:           LogFn | None = None,
) -> Any:
    """Evaluate a FUNCTION call and return its typed result.

    Variable references inside ``args`` are resolved before the call.
    """
    _log = log or (lambda lvl, msg: None)
    fname = func_name.upper()

    # Resolve any #var references inside args
    resolved: list[str] = []
    for a in args:
        if a.startswith(VARIABLE_PREFIX):
            val = variables.get(a, 0)
            resolved.append(str(val))
        else:
            resolved.append(a)

    if fname == "GET_TIME":
        return time.time()

    if fname == "RANDOM":
        if len(resolved) < 2:
            _log("WARNING", "RANDOM: usage: RANDOM min max")
            return 0
        try:
            return random.randint(int(resolved[0]), int(resolved[1]))
        except ValueError as exc:
            _log("WARNING", f"RANDOM: {exc}")
            return 0

    if fname == "CLIPBOARD_GET":
        try:
            import pyperclip          # type: ignore[import]
            return pyperclip.paste()
        except Exception as exc:
            _log("WARNING", f"CLIPBOARD_GET: {exc}")
            return ""

    if fname == "GET_PIXEL_COLOR":
        return _get_pixel_color(resolved, _log)

    # Boolean condition functions — delegate to condition.py
    if fname in ("IMAGE_MATCH", "PIXEL_COLOR", "WINDOW_EXISTS", "FILE_EXISTS"):
        from src.core.condition import eval_condition
        return eval_condition([fname] + resolved, templates_dir, log=_log)

    _log("WARNING", f"Unknown function: {func_name!r}")
    return 0


def _get_pixel_color(args: list[str], log: LogFn) -> str:
    """GET_PIXEL_COLOR x y → 'r g b' string."""
    try:
        import mss        # type: ignore[import]
        import numpy as np  # type: ignore[import]
    except ImportError:
        log("WARNING", "GET_PIXEL_COLOR requires mss and numpy")
        return "0 0 0"

    if len(args) < 2:
        log("WARNING", "GET_PIXEL_COLOR: usage: GET_PIXEL_COLOR x y")
        return "0 0 0"

    x, y = int(args[0]), int(args[1])
    with mss.mss() as sct:
        mon = {"top": y, "left": x, "width": 1, "height": 1}
        raw = np.array(sct.grab(mon))   # BGRA

    r, g, b = int(raw[0, 0, 2]), int(raw[0, 0, 1]), int(raw[0, 0, 0])
    return f"{r} {g} {b}"
