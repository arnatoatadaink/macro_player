"""Command executor — dispatches parsed macro tokens to pynput controllers.

Phase 3 commands
----------------
Mouse   : MOUSE_POS, MOUSE_LEFT/RIGHT/MIDDLE_CLICK/DOWN/UP, WHEEL
Keyboard: KEY, KEYS, KEY_DOWN, KEY_UP, KEYS_DOWN, KEYS_UP, TYPE
Timing  : WAIT

Phase 5 additions
-----------------
Clipboard : CLIPBOARD_SET text
Screen    : SCREENSHOT [path]
Window    : WINDOW_FOCUS title, WINDOW_MOVE title x y,
            WINDOW_RESIZE title w h, WINDOW_CLOSE title

Design notes
------------
- One CommandExecutor instance per playback session.
- All waits honour ``_stop_event``; checking every 50 ms keeps latency low.
- playback_speed scales every WAIT/mousewait/keywait.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from pynput import mouse, keyboard

from src.core.keys import parse_key as _parse_key, parse_combo as _parse_combo
from src.core.commands.window import (
    cmd_window_focus, cmd_window_move, cmd_window_resize, cmd_window_close,
)
from src.core.commands.clipboard import cmd_clipboard_set, cmd_screenshot
from src.core.constants import SLEEP_CHUNK_S


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class CommandExecutor:
    """Executes individual macro commands using pynput controllers."""

    def __init__(self, settings, log_callback=None) -> None:
        self._settings    = settings
        self._mc          = mouse.Controller()
        self._kc          = keyboard.Controller()
        self._stop_event  = threading.Event()
        # Optional callback(level: str, message: str) for PRINT / error output
        self._log = log_callback or (lambda level, msg: None)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def stop_event(self) -> threading.Event:
        return self._stop_event

    def get_mouse_pos(self) -> tuple[int, int]:
        """Return the current mouse position as (x, y)."""
        x, y = self._mc.position
        return int(x), int(y)

    def execute(self, cmd: str, args: list[str]) -> None:
        """Dispatch one command. Raises ValueError on unknown commands."""
        handler = _DISPATCH.get(cmd.upper())
        if handler is None:
            raise ValueError(f"Unknown command: {cmd!r}")
        handler(self, args)

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------

    def _sleep(self, ms: float) -> None:
        """Sleep for ``ms`` milliseconds (scaled by playback_speed).

        Breaks into 50 ms chunks so ``_stop_event`` is polled frequently.
        """
        speed  = max(0.01, self._settings.playback_speed)
        target = ms / speed / 1000.0
        chunk  = SLEEP_CHUNK_S
        elapsed = 0.0
        while elapsed < target:
            if self._stop_event.is_set():
                return
            t = min(chunk, target - elapsed)
            time.sleep(t)
            elapsed += t

    def _mousewait(self) -> None:
        self._sleep(self._settings.mousewait)

    def _keywait(self) -> None:
        self._sleep(self._settings.keywait)

    # ------------------------------------------------------------------
    # Mouse commands
    # ------------------------------------------------------------------

    def _mouse_move(self, x: int, y: int) -> None:
        self._mc.position = (x, y)

    def _opt_move(self, args: list[str]) -> None:
        """Move mouse if x y args are provided, otherwise stay."""
        if len(args) >= 2:
            self._mouse_move(int(args[0]), int(args[1]))

    def _click(self, btn: mouse.Button, args: list[str]) -> None:
        self._opt_move(args)
        self._mc.press(btn)
        self._mousewait()
        self._mc.release(btn)

    def _down(self, btn: mouse.Button, args: list[str]) -> None:
        self._opt_move(args)
        self._mc.press(btn)

    def _up(self, btn: mouse.Button, args: list[str]) -> None:
        self._opt_move(args)
        self._mc.release(btn)

    def _cmd_mouse_pos(self, args: list[str]) -> None:
        self._mouse_move(int(args[0]), int(args[1]))

    def _cmd_mouse_left_click(self, args):   self._click(mouse.Button.left,   args)
    def _cmd_mouse_right_click(self, args):  self._click(mouse.Button.right,  args)
    def _cmd_mouse_middle_click(self, args): self._click(mouse.Button.middle, args)
    def _cmd_mouse_left_down(self, args):    self._down(mouse.Button.left,    args)
    def _cmd_mouse_right_down(self, args):   self._down(mouse.Button.right,   args)
    def _cmd_mouse_middle_down(self, args):  self._down(mouse.Button.middle,  args)
    def _cmd_mouse_left_up(self, args):      self._up(mouse.Button.left,      args)
    def _cmd_mouse_right_up(self, args):     self._up(mouse.Button.right,     args)
    def _cmd_mouse_middle_up(self, args):    self._up(mouse.Button.middle,    args)

    def _cmd_wheel(self, args: list[str]) -> None:
        if len(args) >= 3:
            self._mouse_move(int(args[0]), int(args[1]))
            self._mc.scroll(0, int(args[2]))
        elif len(args) == 1:
            self._mc.scroll(0, int(args[0]))

    # ------------------------------------------------------------------
    # Keyboard commands
    # ------------------------------------------------------------------

    def _cmd_key(self, args: list[str]) -> None:
        """KEY key — press, wait keywait, release."""
        k = _parse_key(args[0]) if args else None
        if k is None:
            return
        self._kc.press(k)
        self._keywait()
        self._kc.release(k)

    def _cmd_key_down(self, args: list[str]) -> None:
        k = _parse_key(args[0]) if args else None
        if k:
            self._kc.press(k)

    def _cmd_key_up(self, args: list[str]) -> None:
        k = _parse_key(args[0]) if args else None
        if k:
            self._kc.release(k)

    def _cmd_keys(self, args: list[str]) -> None:
        """KEYS ctrl+shift+a — press all, wait, release all in reverse."""
        if not args:
            return
        keys = _parse_combo(args[0])
        if not keys:
            return
        for k in keys:
            self._kc.press(k)
        self._keywait()
        for k in reversed(keys):
            self._kc.release(k)

    def _cmd_keys_down(self, args: list[str]) -> None:
        if args:
            for k in _parse_combo(args[0]):
                self._kc.press(k)

    def _cmd_keys_up(self, args: list[str]) -> None:
        if args:
            for k in reversed(_parse_combo(args[0])):
                self._kc.release(k)

    def _cmd_type(self, args: list[str]) -> None:
        """TYPE "text string" — type character by character."""
        text = " ".join(args)          # shlex already stripped quotes
        self._kc.type(text)

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    def _cmd_wait(self, args: list[str]) -> None:
        ms = float(args[0]) if args else 0
        self._sleep(ms)

    # ------------------------------------------------------------------
    # Debug output
    # ------------------------------------------------------------------

    def _cmd_print(self, args: list[str]) -> None:
        """PRINT "message" — write to the log panel."""
        self._log("INFO", " ".join(args))

    # ------------------------------------------------------------------
    # No-ops (placeholders for control flow handled by runner)
    # ------------------------------------------------------------------

    def _cmd_noop(self, args: list[str]) -> None:
        pass


# ---------------------------------------------------------------------------
# Dispatch table — maps UPPER-CASE command name → bound method
# ---------------------------------------------------------------------------

_DISPATCH: dict[str, Any] = {
    # Mouse move
    "MOUSE_POS":          CommandExecutor._cmd_mouse_pos,
    # Mouse clicks
    "MOUSE_LEFT_CLICK":   CommandExecutor._cmd_mouse_left_click,
    "MOUSE_RIGHT_CLICK":  CommandExecutor._cmd_mouse_right_click,
    "MOUSE_MIDDLE_CLICK": CommandExecutor._cmd_mouse_middle_click,
    # Mouse press/release
    "MOUSE_LEFT_DOWN":    CommandExecutor._cmd_mouse_left_down,
    "MOUSE_RIGHT_DOWN":   CommandExecutor._cmd_mouse_right_down,
    "MOUSE_MIDDLE_DOWN":  CommandExecutor._cmd_mouse_middle_down,
    "MOUSE_LEFT_UP":      CommandExecutor._cmd_mouse_left_up,
    "MOUSE_RIGHT_UP":     CommandExecutor._cmd_mouse_right_up,
    "MOUSE_MIDDLE_UP":    CommandExecutor._cmd_mouse_middle_up,
    # Scroll
    "WHEEL":              CommandExecutor._cmd_wheel,
    # Keyboard
    "KEY":                CommandExecutor._cmd_key,
    "KEY_DOWN":           CommandExecutor._cmd_key_down,
    "KEY_UP":             CommandExecutor._cmd_key_up,
    "KEYS":               CommandExecutor._cmd_keys,
    "KEYS_DOWN":          CommandExecutor._cmd_keys_down,
    "KEYS_UP":            CommandExecutor._cmd_keys_up,
    "TYPE":               CommandExecutor._cmd_type,
    # Timing
    "WAIT":               CommandExecutor._cmd_wait,
    # Phase 4 placeholders (recognised but skipped for now)
    "IF":       CommandExecutor._cmd_noop,
    "ELSEIF":   CommandExecutor._cmd_noop,
    "ELSE":     CommandExecutor._cmd_noop,
    "ENDIF":    CommandExecutor._cmd_noop,
    "LOOP":     CommandExecutor._cmd_noop,
    "ENDLOOP":  CommandExecutor._cmd_noop,
    "WHILE":    CommandExecutor._cmd_noop,
    "ENDWHILE": CommandExecutor._cmd_noop,
    "REPEAT":   CommandExecutor._cmd_noop,
    "UNTIL":    CommandExecutor._cmd_noop,
    "CALL":     CommandExecutor._cmd_noop,
    "BREAK":    CommandExecutor._cmd_noop,
    "CONTINUE": CommandExecutor._cmd_noop,
    "RETURN":   CommandExecutor._cmd_noop,
    "EXIT":     CommandExecutor._cmd_noop,
    "PRINT":          CommandExecutor._cmd_print,
    # Mouse position capture (args are variable names — handled by runner)
    "MOUSE_GET_POS":  CommandExecutor._cmd_noop,
    # Phase 5: clipboard, screenshot, window management (from sub-modules)
    "CLIPBOARD_SET":  cmd_clipboard_set,
    "SCREENSHOT":     cmd_screenshot,
    "WINDOW_FOCUS":   cmd_window_focus,
    "WINDOW_MOVE":    cmd_window_move,
    "WINDOW_RESIZE":  cmd_window_resize,
    "WINDOW_CLOSE":   cmd_window_close,
    "FUNCTION":       CommandExecutor._cmd_noop,
    "TRY":            CommandExecutor._cmd_noop,
    "CATCH":          CommandExecutor._cmd_noop,
    "ENDTRY":         CommandExecutor._cmd_noop,
}


def is_commands(key):
    return key in _DISPATCH
