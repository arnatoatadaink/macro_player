"""Variable store for one playback session.

Variables are global to the session (shared across CALL'd macros).
All access is single-threaded (same QThread as the runner).

Naming convention: variable names always start with '#', e.g. ``#count``.
"""
from __future__ import annotations

from typing import Any


class VariableStore:
    """Maps '$varname' → Any value (int, float, str, bool)."""

    def __init__(self) -> None:
        self._vars: dict[str, Any] = {}

    # ------------------------------------------------------------------
    def get(self, name: str, default: Any = 0) -> Any:
        return self._vars.get(name, default)

    def set(self, name: str, value: Any) -> None:
        self._vars[name] = value

    def as_dict(self) -> dict[str, Any]:
        return dict(self._vars)

    def __repr__(self) -> str:
        return f"VariableStore({self._vars!r})"
