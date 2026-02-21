"""Centralised optional-dependency imports.

Each library is imported once at module level.  Consumers check the
``HAS_*`` flags before using the corresponding module reference.

This eliminates scattered try/except ImportError blocks across
executor.py, condition.py, and expression.py.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# opencv-python + numpy + mss  (IMAGE_MATCH, PIXEL_COLOR, GET_PIXEL_COLOR,
#                                SCREENSHOT)
# ---------------------------------------------------------------------------
try:
    import cv2 as cv2                # type: ignore[import]
    import numpy as np               # type: ignore[import]
    HAS_CV = True
except ImportError:
    cv2 = None  # type: ignore[assignment]
    np = None   # type: ignore[assignment]
    HAS_CV = False

try:
    import mss as mss                # type: ignore[import]
    import mss.tools as mss_tools    # type: ignore[import]
    HAS_MSS = True
except ImportError:
    mss = None       # type: ignore[assignment]
    mss_tools = None  # type: ignore[assignment]
    HAS_MSS = False

# ---------------------------------------------------------------------------
# pywin32  (WINDOW_FOCUS, WINDOW_MOVE, WINDOW_RESIZE, WINDOW_CLOSE,
#           WINDOW_EXISTS)
# ---------------------------------------------------------------------------
try:
    import win32gui as win32gui      # type: ignore[import]
    import win32con as win32con      # type: ignore[import]
    HAS_WIN32 = True
except ImportError:
    win32gui = None  # type: ignore[assignment]
    win32con = None  # type: ignore[assignment]
    HAS_WIN32 = False

# ---------------------------------------------------------------------------
# pyperclip  (CLIPBOARD_SET, CLIPBOARD_GET)
# ---------------------------------------------------------------------------
try:
    import pyperclip as pyperclip    # type: ignore[import]
    HAS_PYPERCLIP = True
except ImportError:
    pyperclip = None  # type: ignore[assignment]
    HAS_PYPERCLIP = False
