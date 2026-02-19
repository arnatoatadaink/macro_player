"""Variable watch panel — shows live $var values during macro playback.

Displayed as a two-column QTableWidget (Name | Value) inside a QDockWidget.
Updates are pushed from the playback thread via MacroPlayer.vars_updated.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

_DARK = """
    QTableWidget {
        background-color: #1E1E1E;
        color: #D4D4D4;
        border: none;
        gridline-color: #3C3C3C;
    }
    QTableWidget::item { padding: 2px 6px; }
    QTableWidget::item:selected {
        background: #264F78;
    }
    QHeaderView::section {
        background-color: #2D2D2D;
        color: #AAAAAA;
        border: none;
        border-bottom: 1px solid #3C3C3C;
        padding: 3px 6px;
    }
    QPushButton {
        background: #3C3C3C; color: #CCCCCC;
        border: 1px solid #555; border-radius: 3px;
        padding: 2px 10px; font-size: 11px;
    }
    QPushButton:hover { background: #4A4A4A; }
"""

_COL_NAME  = "#9CDCFE"   # light blue — same as variable colour in highlighter
_COL_VALUE_INT   = "#B5CEA8"   # light green  — numbers
_COL_VALUE_FLOAT = "#B5CEA8"
_COL_VALUE_BOOL  = "#569CD6"   # blue-ish      — keywords
_COL_VALUE_STR   = "#CE9178"   # orange        — strings


def _value_color(val: Any) -> str:
    if isinstance(val, bool):
        return _COL_VALUE_BOOL
    if isinstance(val, int):
        return _COL_VALUE_INT
    if isinstance(val, float):
        return _COL_VALUE_FLOAT
    return _COL_VALUE_STR


class VariablePanel(QWidget):
    """A table that displays the current variable snapshot."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_DARK)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Toolbar
        bar = QHBoxLayout()
        self._clear_btn = QPushButton("クリア")
        self._clear_btn.setFixedHeight(22)
        self._clear_btn.clicked.connect(self.clear)
        bar.addStretch()
        bar.addWidget(self._clear_btn)
        layout.addLayout(bar)

        # Table
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["変数名", "値"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setDefaultSectionSize(130)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)

        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._table.setFont(mono)

        layout.addWidget(self._table)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_vars(self, variables: dict) -> None:
        """Refresh the table with a new variable snapshot.

        Existing rows are updated in-place; new variables are appended;
        variables that no longer exist are removed.
        """
        # Build index of current rows: name → row index
        current: dict[str, int] = {}
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item:
                current[item.text()] = row

        # Update or add
        for name, val in sorted(variables.items()):
            val_str = str(val)
            color   = _value_color(val)

            if name in current:
                row = current[name]
            else:
                row = self._table.rowCount()
                self._table.insertRow(row)
                name_item = QTableWidgetItem(name)
                name_item.setForeground(QColor(_COL_NAME))
                self._table.setItem(row, 0, name_item)

            val_item = QTableWidgetItem(val_str)
            val_item.setForeground(QColor(color))
            self._table.setItem(row, 1, val_item)

        # Remove rows whose variable no longer exists
        surviving = set(variables.keys())
        rows_to_remove = [
            row for name, row in current.items()
            if name not in surviving
        ]
        for row in sorted(rows_to_remove, reverse=True):
            self._table.removeRow(row)

    def clear(self) -> None:
        """Remove all rows from the table."""
        self._table.setRowCount(0)
