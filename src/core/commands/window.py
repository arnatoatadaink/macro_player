"""Window management commands for CommandExecutor.

WINDOW_FOCUS, WINDOW_MOVE, WINDOW_RESIZE, WINDOW_CLOSE
"""
from __future__ import annotations

from src.utils.optional_deps import win32gui, win32con, HAS_WIN32


def cmd_window_focus(self, args: list[str]) -> None:
    """WINDOW_FOCUS "title" — bring window to foreground."""
    if not HAS_WIN32:
        self._log("WARNING", "WINDOW_FOCUS requires pywin32")
        return
    title = " ".join(args)
    hwnd  = win32gui.FindWindow(None, title)
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    else:
        self._log("WARNING", f"WINDOW_FOCUS: window not found: {title!r}")


def cmd_window_move(self, args: list[str]) -> None:
    """WINDOW_MOVE "title" x y — move window top-left corner."""
    if not HAS_WIN32:
        self._log("WARNING", "WINDOW_MOVE requires pywin32")
        return
    if len(args) < 3:
        self._log("WARNING", "WINDOW_MOVE: usage: WINDOW_MOVE title x y")
        return
    title = args[0]
    try:
        x, y = int(args[1]), int(args[2])
    except ValueError:
        self._log("WARNING", "WINDOW_MOVE: x/y must be integers")
        return
    hwnd = win32gui.FindWindow(None, title)
    if hwnd:
        rect = win32gui.GetWindowRect(hwnd)
        w    = rect[2] - rect[0]
        h    = rect[3] - rect[1]
        win32gui.MoveWindow(hwnd, x, y, w, h, True)
    else:
        self._log("WARNING", f"WINDOW_MOVE: window not found: {title!r}")


def cmd_window_resize(self, args: list[str]) -> None:
    """WINDOW_RESIZE "title" w h — resize window."""
    if not HAS_WIN32:
        self._log("WARNING", "WINDOW_RESIZE requires pywin32")
        return
    if len(args) < 3:
        self._log("WARNING", "WINDOW_RESIZE: usage: WINDOW_RESIZE title w h")
        return
    title = args[0]
    try:
        w, h = int(args[1]), int(args[2])
    except ValueError:
        self._log("WARNING", "WINDOW_RESIZE: w/h must be integers")
        return
    hwnd = win32gui.FindWindow(None, title)
    if hwnd:
        rect = win32gui.GetWindowRect(hwnd)
        x    = rect[0]
        y    = rect[1]
        win32gui.MoveWindow(hwnd, x, y, w, h, True)
    else:
        self._log("WARNING", f"WINDOW_RESIZE: window not found: {title!r}")


def cmd_window_close(self, args: list[str]) -> None:
    """WINDOW_CLOSE "title" — send WM_CLOSE to a window."""
    if not HAS_WIN32:
        self._log("WARNING", "WINDOW_CLOSE requires pywin32")
        return
    title = " ".join(args)
    hwnd  = win32gui.FindWindow(None, title)
    if hwnd:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    else:
        self._log("WARNING", f"WINDOW_CLOSE: window not found: {title!r}")
