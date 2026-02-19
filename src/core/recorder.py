"""Macro recording engine — Phase 2.

Captures mouse/keyboard events via pynput and emits them as macro
command strings in real time. Thread-safe: listener callbacks run in
pynput daemon threads; Qt signals are emitted across threads via
PySide6's default queued-connection mechanism.

Typical recorded output for a Ctrl+C click sequence:
    WAIT 412
    MOUSE_POS 640 480
    WAIT 830
    MOUSE_LEFT_CLICK 640 480
    WAIT 150
    KEYS ctrl+c
"""
from __future__ import annotations

import math
import threading
import time
from typing import Optional

from pynput import mouse, keyboard
from PySide6.QtCore import QObject, Signal

# ---------------------------------------------------------------------------
# Key-name tables
# ---------------------------------------------------------------------------

_MODIFIERS: frozenset = frozenset({
    keyboard.Key.ctrl,    keyboard.Key.ctrl_l,  keyboard.Key.ctrl_r,
    keyboard.Key.shift,   keyboard.Key.shift_l, keyboard.Key.shift_r,
    keyboard.Key.alt,     keyboard.Key.alt_l,   keyboard.Key.alt_r,
    keyboard.Key.cmd,     keyboard.Key.cmd_l,   keyboard.Key.cmd_r,
})

_MOD_NAMES: dict = {
    keyboard.Key.ctrl_l:  "ctrl",  keyboard.Key.ctrl_r:  "ctrl",
    keyboard.Key.ctrl:    "ctrl",
    keyboard.Key.shift_l: "shift", keyboard.Key.shift_r: "shift",
    keyboard.Key.shift:   "shift",
    keyboard.Key.alt_l:   "alt",   keyboard.Key.alt_r:   "alt",
    keyboard.Key.alt:     "alt",
    keyboard.Key.cmd_l:   "win",   keyboard.Key.cmd_r:   "win",
    keyboard.Key.cmd:     "win",
}

_KEY_NAMES: dict = {
    keyboard.Key.space:        "space",
    keyboard.Key.enter:        "enter",
    keyboard.Key.backspace:    "backspace",
    keyboard.Key.tab:          "tab",
    keyboard.Key.esc:          "esc",
    # keyboard.Key.escape:       "esc",
    keyboard.Key.delete:       "delete",
    keyboard.Key.home:         "home",
    keyboard.Key.end:          "end",
    keyboard.Key.page_up:      "pageup",
    keyboard.Key.page_down:    "pagedown",
    keyboard.Key.up:           "up",
    keyboard.Key.down:         "down",
    keyboard.Key.left:         "left",
    keyboard.Key.right:        "right",
    keyboard.Key.insert:       "insert",
    keyboard.Key.caps_lock:    "capslock",
    keyboard.Key.num_lock:     "numlock",
    keyboard.Key.scroll_lock:  "scrolllock",
    keyboard.Key.print_screen: "printscreen",
    keyboard.Key.pause:        "pause",
    keyboard.Key.f1:  "f1",  keyboard.Key.f2:  "f2",  keyboard.Key.f3:  "f3",
    keyboard.Key.f4:  "f4",  keyboard.Key.f5:  "f5",  keyboard.Key.f6:  "f6",
    keyboard.Key.f7:  "f7",  keyboard.Key.f8:  "f8",  keyboard.Key.f9:  "f9",
    keyboard.Key.f10: "f10", keyboard.Key.f11: "f11", keyboard.Key.f12: "f12",
}

# click_cmd, down_cmd, up_cmd
_BUTTON_CMDS: dict = {
    mouse.Button.left:   ("MOUSE_LEFT_CLICK",   "MOUSE_LEFT_DOWN",   "MOUSE_LEFT_UP"),
    mouse.Button.right:  ("MOUSE_RIGHT_CLICK",  "MOUSE_RIGHT_DOWN",  "MOUSE_RIGHT_UP"),
    mouse.Button.middle: ("MOUSE_MIDDLE_CLICK", "MOUSE_MIDDLE_DOWN", "MOUSE_MIDDLE_UP"),
}

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

_CLICK_MAX_MS = 400   # press→release within this → simple CLICK (not DOWN/UP)
_CLICK_MAX_PX = 5     # pixel drift within this    → simple CLICK
_MOVE_MIN_PX  = 20    # minimum Euclidean distance  to emit MOUSE_POS
_MOVE_MIN_MS  = 100   # minimum ms between MOUSE_POS events
_WAIT_MIN_MS  = 10    # WAITs shorter than this are suppressed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _key_name(key) -> Optional[str]:
    """Return the macro key name for a pynput key, or None if unsupported."""
    if key in _KEY_NAMES:
        return _KEY_NAMES[key]
    if hasattr(key, "char") and key.char:
        return key.char
    raw = str(key).replace("Key.", "").replace("'", "")
    # Unknown virtual key code looks like "<65437>"
    return None if (not raw or raw.startswith("<")) else raw


def _hypot(x1: int, y1: int, x2: int, y2: int) -> float:
    return math.hypot(x2 - x1, y2 - y1)


# ---------------------------------------------------------------------------
# Recorder
# ---------------------------------------------------------------------------

class MacroRecorder(QObject):
    """Captures input events and emits them as formatted macro command strings.

    Signals
    -------
    command_recorded(str)
        Emitted once per command line (including WAIT lines).
        Connected to EditorArea.append_text in main_window.py.
    status_changed(str)
        Emits "recording" on start, "stopped" on stop.
    """

    command_recorded = Signal(str)
    status_changed   = Signal(str)

    def __init__(self, settings) -> None:
        super().__init__()
        self._settings  = settings
        self._recording = False
        self._ml: Optional[mouse.Listener]    = None
        self._kl: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        """Begin recording."""
        if self._recording:
            return

        with self._lock:
            self._recording   = True
            self._record_ts   = self._settings.getbool("INPUT", "record_timestamps", True)
            self._last_evt_t  : float = time.monotonic()
            self._last_move_t : float = 0.0
            self._last_pos    : tuple = (0, 0)
            self._active_mods : set   = set()
            self._pending_btn : dict  = {}    # Button → (x, y, monotonic_time)

        self._ml = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._kl = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._ml.start()
        self._kl.start()
        self.status_changed.emit("recording")

    def stop(self) -> None:
        """Stop recording cleanly."""
        if not self._recording:
            return

        with self._lock:
            self._recording = False

        if self._ml:
            self._ml.stop()
            self._ml = None
        if self._kl:
            self._kl.stop()
            self._kl = None

        self.status_changed.emit("stopped")

    # ------------------------------------------------------------------
    # Emission helper
    # ------------------------------------------------------------------

    def _emit_cmd(self, cmd: str, at: float) -> None:
        """Compute WAIT delta, then emit WAIT (if any) and cmd.

        `at` is the monotonic timestamp of the event so that buffered
        events (e.g., click press stored until release) produce correct
        WAIT values.
        """
        if not self._recording:
            return

        wait_line: Optional[str] = None
        with self._lock:
            if self._record_ts:
                delta_ms = round((at - self._last_evt_t) * 1000)
                if delta_ms >= _WAIT_MIN_MS:
                    wait_line = f"WAIT {delta_ms}"
            self._last_evt_t = at

        # Emit outside the lock to avoid holding it during cross-thread signal dispatch
        if wait_line:
            self.command_recorded.emit(wait_line)
        self.command_recorded.emit(cmd)

    # ------------------------------------------------------------------
    # Mouse callbacks  (called from mouse listener thread)
    # ------------------------------------------------------------------

    def _on_move(self, x: int, y: int) -> None:
        if not self._recording:
            return
        now = time.monotonic()

        with self._lock:
            dist = _hypot(*self._last_pos, x, y)
            dt   = (now - self._last_move_t) * 1000
            if dist < _MOVE_MIN_PX or dt < _MOVE_MIN_MS:
                return
            self._last_move_t = now
            self._last_pos    = (x, y)

        self._emit_cmd(f"MOUSE_POS {x} {y}", now)

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        if not self._recording:
            return
        now  = time.monotonic()
        cmds = _BUTTON_CMDS.get(button)
        if cmds is None:
            return
        click_cmd, down_cmd, up_cmd = cmds

        if pressed:
            with self._lock:
                self._pending_btn[button] = (x, y, now)
                self._last_pos = (x, y)
        else:
            with self._lock:
                info = self._pending_btn.pop(button, None)
                self._last_pos = (x, y)

            if info:
                px, py, pt = info
                dt_ms = (now - pt) * 1000
                dist  = _hypot(px, py, x, y)

                if dt_ms <= _CLICK_MAX_MS and dist <= _CLICK_MAX_PX:
                    # Quick click at same position → CLICK
                    self._emit_cmd(f"{click_cmd} {x} {y}", pt)
                else:
                    # Slow or dragged → separate DOWN / UP
                    self._emit_cmd(f"{down_cmd} {px} {py}", pt)
                    self._emit_cmd(f"{up_cmd} {x} {y}", now)
            else:
                # Release with no matching press (recording started mid-hold)
                self._emit_cmd(f"{up_cmd} {x} {y}", now)

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        if not self._recording:
            return
        now   = time.monotonic()
        ticks = int(dy) if dy != 0 else int(dx)
        if ticks == 0:
            return
        with self._lock:
            self._last_pos = (x, y)
        self._emit_cmd(f"WHEEL {x} {y} {ticks}", now)

    # ------------------------------------------------------------------
    # Keyboard callbacks  (called from keyboard listener thread)
    # ------------------------------------------------------------------

    def _on_key_press(self, key) -> None:
        if not self._recording:
            return
        now = time.monotonic()

        # Modifier key → update state, don't emit yet
        if key in _MODIFIERS:
            with self._lock:
                self._active_mods.add(key)
            return

        name = _key_name(key)
        if not name:
            return

        with self._lock:
            mods = {_MOD_NAMES[m] for m in self._active_mods if m in _MOD_NAMES}

        non_shift = mods - {"shift"}

        if non_shift:
            # Ctrl / Alt / Win combo: normalise key to lowercase for shortcuts
            key_part = name.lower() if len(name) == 1 else name
            # Stable order: ctrl → shift → alt → win → key
            _ORDER = {"ctrl": 0, "shift": 1, "alt": 2, "win": 3}
            sorted_mods = sorted(mods, key=lambda m: _ORDER.get(m, 99))
            parts = sorted_mods + [key_part]
            self._emit_cmd(f"KEYS {'+'.join(parts)}", now)
        else:
            # Plain key or Shift+char (char already reflects shift case)
            self._emit_cmd(f"KEY {name}", now)

    def _on_key_release(self, key) -> None:
        if not self._recording:
            return
        if key in _MODIFIERS:
            with self._lock:
                self._active_mods.discard(key)
