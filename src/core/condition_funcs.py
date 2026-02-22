"""Condition function implementations for IMAGE_MATCH, PIXEL_COLOR, etc.

Extracted from condition.py to separate evaluation dispatch logic
from individual function implementations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.utils.optional_deps import (
    cv2, np, mss, HAS_CV, HAS_MSS,
    win32gui, HAS_WIN32,
)

LogFn = Callable[[str, str], None]


# ---------------------------------------------------------------------------
# IMAGE_MATCH
# ---------------------------------------------------------------------------

def image_match(args: list[str], templates_dir: Path, log: LogFn) -> bool:
    """IMAGE_MATCH "template.png" [threshold 0.85] [region x y w h]"""
    if not (HAS_CV and HAS_MSS):
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

def pixel_color(args: list[str], log: LogFn) -> bool:
    """PIXEL_COLOR x y r g b [tolerance=10]"""
    if not (HAS_CV and HAS_MSS):
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

def window_exists(args: list[str], log: LogFn) -> bool:
    """WINDOW_EXISTS "Window Title" """
    if not HAS_WIN32:
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

def file_exists(args: list[str], log: LogFn) -> bool:
    """FILE_EXISTS "path" """
    if not args:
        log("WARNING", "FILE_EXISTS: path required")
        return False
    return Path(" ".join(args)).exists()
