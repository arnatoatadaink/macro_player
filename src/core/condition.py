"""Condition evaluators for IF / WHILE / UNTIL.

Supported Phase-4 functions
---------------------------
IMAGE_MATCH "template.png" [threshold 0.85] [region x y w h]
PIXEL_COLOR x y r g b [tolerance]
WINDOW_EXISTS "Window Title"
FILE_EXISTS "path/to/file"
TRUE  / FALSE  (literals)

Phase-5 additions
-----------------
Variable references and arithmetic/comparison expressions are handled by
delegating to expression.eval_expr() when the condition doesn't match any
known function name.  Pass a VariableStore to enable this.

Optional dependencies
---------------------
- opencv-python + mss  → IMAGE_MATCH, PIXEL_COLOR
- pywin32              → WINDOW_EXISTS on Windows
Missing libraries degrade gracefully (condition returns False with a warning).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.core.variable_store import VariableStore

from src.utils.optional_deps import (
    cv2, np, mss, HAS_CV as _HAS_CV, HAS_MSS as _HAS_MSS,
    win32gui, HAS_WIN32 as _HAS_WIN32,
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
    via expression.eval_expr() (Phase 5).  If no ``variables`` store is
    provided, simple literal / variable-only expressions still work.
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
        return _image_match(args, templates_dir, _log)
    if func == "PIXEL_COLOR":
        return _pixel_color(args, _log)
    if func == "WINDOW_EXISTS":
        return _window_exists(args, _log)
    if func == "FILE_EXISTS":
        return _file_exists(args, _log)

    # Phase 5: treat the token list as a boolean expression
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


# ---------------------------------------------------------------------------
# IMAGE_MATCH
# ---------------------------------------------------------------------------

def _image_match(args: list[str], templates_dir: Path, log: LogFn) -> bool:
    """IMAGE_MATCH "template.png" [threshold 0.85] [region x y w h]"""
    if not _HAS_CV:
        log("WARNING", "IMAGE_MATCH requires opencv-python and mss")
        return False
    if not args:
        log("WARNING", "IMAGE_MATCH: template filename required")
        return False

    template_file = args[0]
    threshold     = 0.80
    region        = None

    i = 1
    while i < len(args):
        key = args[i].lower()
        if key == "threshold" and i + 1 < len(args):
            try:
                threshold = float(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif key == "region" and i + 4 < len(args):
            try:
                region = tuple(int(args[i + j]) for j in range(1, 5))
            except ValueError:
                pass
            i += 5
        else:
            i += 1

    # Resolve template path
    p = Path(template_file)
    template_path = p if p.is_absolute() else templates_dir / p
    if not template_path.exists():
        log("WARNING", f"IMAGE_MATCH: template not found: {template_path}")
        return False

    template = cv2.imread(str(template_path))
    if template is None:
        log("WARNING", f"IMAGE_MATCH: cannot read image: {template_path}")
        return False

    # Capture screen region
    with mss.mss() as sct:
        if region:
            x, y, w, h = region
            monitor = {"top": y, "left": x, "width": w, "height": h}
        else:
            monitor = sct.monitors[1]   # primary monitor
        raw = np.array(sct.grab(monitor))

    screen = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)

    # Template matching — CCOEFF_NORMED gives 0..1 confidence
    if (screen.shape[0] < template.shape[0] or
            screen.shape[1] < template.shape[1]):
        log("WARNING", "IMAGE_MATCH: screenshot smaller than template")
        return False

    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val) >= threshold


# ---------------------------------------------------------------------------
# PIXEL_COLOR
# ---------------------------------------------------------------------------

def _pixel_color(args: list[str], log: LogFn) -> bool:
    """PIXEL_COLOR x y r g b [tolerance=10]"""
    if not _HAS_CV:
        log("WARNING", "PIXEL_COLOR requires mss")
        return False
    if len(args) < 5:
        log("WARNING", "PIXEL_COLOR: usage: PIXEL_COLOR x y r g b [tolerance]")
        return False

    try:
        x, y         = int(args[0]), int(args[1])
        er, eg, eb   = int(args[2]), int(args[3]), int(args[4])
        tolerance    = int(args[5]) if len(args) > 5 else 10
    except ValueError as exc:
        log("WARNING", f"PIXEL_COLOR: invalid argument: {exc}")
        return False

    with mss.mss() as sct:
        mon = {"top": y, "left": x, "width": 1, "height": 1}
        pixel = np.array(sct.grab(mon))   # BGRA

    # mss returns BGRA
    pb, pg, pr = int(pixel[0, 0, 0]), int(pixel[0, 0, 1]), int(pixel[0, 0, 2])
    return (
        abs(pr - er) <= tolerance and
        abs(pg - eg) <= tolerance and
        abs(pb - eb) <= tolerance
    )


# ---------------------------------------------------------------------------
# WINDOW_EXISTS
# ---------------------------------------------------------------------------

def _window_exists(args: list[str], log: LogFn) -> bool:
    """WINDOW_EXISTS "Window Title" """
    if not _HAS_WIN32:
        log("WARNING", "WINDOW_EXISTS requires pywin32")
        return False
    if not args:
        log("WARNING", "WINDOW_EXISTS: title required")
        return False

    title = " ".join(args)
    hwnd  = win32gui.FindWindow(None, title)
    return hwnd != 0


# ---------------------------------------------------------------------------
# FILE_EXISTS
# ---------------------------------------------------------------------------

def _file_exists(args: list[str], log: LogFn) -> bool:
    """FILE_EXISTS "path" """
    if not args:
        log("WARNING", "FILE_EXISTS: path required")
        return False
    return Path(" ".join(args)).exists()
