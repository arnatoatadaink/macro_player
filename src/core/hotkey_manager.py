"""Global hotkey manager — system-wide keyboard shortcuts via pynput.

Listens for key combinations defined in settings.ini [HOTKEYS] and
emits Qt signals that the main window can connect to its action handlers.

The listener runs in a daemon thread and is stopped when stop() is called
or the QObject is destroyed.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Signal

from pynput import keyboard


def _parse_hotkey(combo_str: str) -> str | None:
    """Convert 'Ctrl+Shift+R' into pynput GlobalHotKeys format '<ctrl>+<shift>+r'.

    Returns None if the combo string is empty or unparseable.
    """
    if not combo_str or not combo_str.strip():
        return None

    _MAP = {
        "CTRL":  "<ctrl>",
        "ALT":   "<alt>",
        "SHIFT": "<shift>",
        "WIN":   "<cmd>",
        "SUPER": "<cmd>",
    }

    parts = [p.strip() for p in combo_str.split("+")]
    result: list[str] = []
    for p in parts:
        upper = p.upper()
        if upper in _MAP:
            result.append(_MAP[upper])
        else:
            # Single character or function key
            result.append(p.lower())
    return "+".join(result)


class HotkeyManager(QObject):
    """Manages global hotkeys for record/stop/play.

    Signals
    -------
    record_triggered : emitted when the record hotkey is pressed
    stop_triggered   : emitted when the stop hotkey is pressed
    play_triggered   : emitted when the play hotkey is pressed
    """

    record_triggered = Signal()
    stop_triggered   = Signal()
    play_triggered   = Signal()

    def __init__(self, settings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self) -> None:
        """Start listening for global hotkeys."""
        if self._listener is not None:
            return

        hotkeys: dict[str, Callable] = {}

        record_combo = _parse_hotkey(
            self._settings.get("HOTKEYS", "record_start", "")
        )
        stop_combo = _parse_hotkey(
            self._settings.get("HOTKEYS", "record_stop", "")
        )
        play_combo = _parse_hotkey(
            self._settings.get("HOTKEYS", "play", "")
        )

        if record_combo:
            hotkeys[record_combo] = self.record_triggered.emit
        if stop_combo:
            hotkeys[stop_combo] = self.stop_triggered.emit
        if play_combo:
            hotkeys[play_combo] = self.play_triggered.emit

        if not hotkeys:
            return

        self._listener = keyboard.GlobalHotKeys(hotkeys)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        """Stop the global hotkey listener."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def restart(self) -> None:
        """Restart with potentially updated settings."""
        self.stop()
        self.start()
