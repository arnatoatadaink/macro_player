"""Clipboard and screenshot commands for CommandExecutor.

CLIPBOARD_SET, SCREENSHOT
"""
from __future__ import annotations

from src.utils.optional_deps import pyperclip, HAS_PYPERCLIP, mss, HAS_MSS


def cmd_clipboard_set(self, args: list[str]) -> None:
    """CLIPBOARD_SET text — copy text to the clipboard."""
    if not HAS_PYPERCLIP:
        self._log("WARNING", "CLIPBOARD_SET requires pyperclip")
        return
    text = " ".join(args)
    try:
        pyperclip.copy(text)
    except Exception as exc:
        self._log("WARNING", f"CLIPBOARD_SET: {exc}")


def cmd_screenshot(self, args: list[str]) -> None:
    """SCREENSHOT [path] — save a screenshot; default path is screenshots/YYYYMMDD_HHMMSS.png"""
    if not HAS_MSS:
        self._log("WARNING", "SCREENSHOT requires mss")
        return
    import datetime
    from pathlib import Path as _Path

    if args:
        path = args[0]
    else:
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"screenshots/{ts}.png"

    try:
        _Path(path).parent.mkdir(parents=True, exist_ok=True)
        with mss.mss() as sct:
            sct.shot(mon=1, output=path)
        self._log("INFO", f"SCREENSHOT saved: {path}")
    except Exception as exc:
        self._log("WARNING", f"SCREENSHOT: {exc}")
