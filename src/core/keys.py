"""Shared key / button / modifier mappings for pynput.

Centralises the name-tables previously duplicated across executor.py
and recorder.py so both modules import from a single source of truth.
"""
from __future__ import annotations

from typing import Any, Optional

from pynput import mouse, keyboard

# ---------------------------------------------------------------------------
# Key-name → pynput Key  (used by executor for playback)
# ---------------------------------------------------------------------------

SPECIAL_KEYS: dict[str, Any] = {
    "CTRL":        keyboard.Key.ctrl,
    "CTRL_L":      keyboard.Key.ctrl_l,
    "CTRL_R":      keyboard.Key.ctrl_r,
    "SHIFT":       keyboard.Key.shift,
    "SHIFT_L":     keyboard.Key.shift_l,
    "SHIFT_R":     keyboard.Key.shift_r,
    "ALT":         keyboard.Key.alt,
    "ALT_L":       keyboard.Key.alt_l,
    "ALT_R":       keyboard.Key.alt_r,
    "WIN":         keyboard.Key.cmd,
    "SUPER":       keyboard.Key.cmd,
    "ENTER":       keyboard.Key.enter,
    "RETURN":      keyboard.Key.enter,
    "SPACE":       keyboard.Key.space,
    "BACKSPACE":   keyboard.Key.backspace,
    "TAB":         keyboard.Key.tab,
    "ESC":         keyboard.Key.esc,
    "ESCAPE":      keyboard.Key.esc,
    "DELETE":      keyboard.Key.delete,
    "DEL":         keyboard.Key.delete,
    "HOME":        keyboard.Key.home,
    "END":         keyboard.Key.end,
    "PAGEUP":      keyboard.Key.page_up,
    "PAGE_UP":     keyboard.Key.page_up,
    "PAGEDOWN":    keyboard.Key.page_down,
    "PAGE_DOWN":   keyboard.Key.page_down,
    "UP":          keyboard.Key.up,
    "DOWN":        keyboard.Key.down,
    "LEFT":        keyboard.Key.left,
    "RIGHT":       keyboard.Key.right,
    "INSERT":      keyboard.Key.insert,
    "CAPSLOCK":    keyboard.Key.caps_lock,
    "NUMLOCK":     keyboard.Key.num_lock,
    "SCROLLLOCK":  keyboard.Key.scroll_lock,
    "PRINTSCREEN": keyboard.Key.print_screen,
    "PAUSE":       keyboard.Key.pause,
    **{f"F{n}": getattr(keyboard.Key, f"f{n}") for n in range(1, 13)},
}

BUTTON_MAP: dict[str, mouse.Button] = {
    "LEFT":   mouse.Button.left,
    "RIGHT":  mouse.Button.right,
    "MIDDLE": mouse.Button.middle,
}

# ---------------------------------------------------------------------------
# pynput Key → macro name  (used by recorder for recording)
# ---------------------------------------------------------------------------

MODIFIERS: frozenset = frozenset({
    keyboard.Key.ctrl,    keyboard.Key.ctrl_l,  keyboard.Key.ctrl_r,
    keyboard.Key.shift,   keyboard.Key.shift_l, keyboard.Key.shift_r,
    keyboard.Key.alt,     keyboard.Key.alt_l,   keyboard.Key.alt_r,
    keyboard.Key.cmd,     keyboard.Key.cmd_l,   keyboard.Key.cmd_r,
})

MOD_NAMES: dict = {
    keyboard.Key.ctrl_l:  "ctrl",  keyboard.Key.ctrl_r:  "ctrl",
    keyboard.Key.ctrl:    "ctrl",
    keyboard.Key.shift_l: "shift", keyboard.Key.shift_r: "shift",
    keyboard.Key.shift:   "shift",
    keyboard.Key.alt_l:   "alt",   keyboard.Key.alt_r:   "alt",
    keyboard.Key.alt:     "alt",
    keyboard.Key.cmd_l:   "win",   keyboard.Key.cmd_r:   "win",
    keyboard.Key.cmd:     "win",
}

KEY_NAMES: dict = {
    keyboard.Key.space:        "space",
    keyboard.Key.enter:        "enter",
    keyboard.Key.backspace:    "backspace",
    keyboard.Key.tab:          "tab",
    keyboard.Key.esc:          "esc",
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

# click_cmd, down_cmd, up_cmd  (used by recorder)
BUTTON_CMDS: dict = {
    mouse.Button.left:   ("MOUSE_LEFT_CLICK",   "MOUSE_LEFT_DOWN",   "MOUSE_LEFT_UP"),
    mouse.Button.right:  ("MOUSE_RIGHT_CLICK",  "MOUSE_RIGHT_DOWN",  "MOUSE_RIGHT_UP"),
    mouse.Button.middle: ("MOUSE_MIDDLE_CLICK", "MOUSE_MIDDLE_DOWN", "MOUSE_MIDDLE_UP"),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_key(name: str) -> Optional[Any]:
    """Convert a key-name string (as recorded) to a pynput Key or KeyCode."""
    upper = name.upper()
    if upper in SPECIAL_KEYS:
        return SPECIAL_KEYS[upper]
    if len(name) == 1:
        return keyboard.KeyCode.from_char(name)
    return None


def parse_combo(combo_str: str) -> list[Any]:
    """Parse 'ctrl+shift+a' → [Key.ctrl, Key.shift, KeyCode('a')]."""
    return [k for n in combo_str.split("+") if (k := parse_key(n.strip())) is not None]


def key_name(key) -> Optional[str]:
    """Return the macro key name for a pynput key, or None if unsupported."""
    if key in KEY_NAMES:
        return KEY_NAMES[key]
    if hasattr(key, "char") and key.char:
        return key.char
    raw = str(key).replace("Key.", "").replace("'", "")
    return None if (not raw or raw.startswith("<")) else raw
