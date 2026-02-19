"""Left sidebar: control buttons + macro file tree."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QPushButton,
)
from PySide6.QtCore import Signal

from src.gui.file_tree import MacroFileTree

_BTN_BASE = """
    QPushButton {{
        padding: 7px 6px;
        border-radius: 4px;
        background: #3C3C3C;
        color: {color};
        border: 1px solid #555555;
        font-size: 12px;
        text-align: left;
    }}
    QPushButton:hover {{ background: #4A4A4A; }}
    QPushButton:pressed {{ background: #2A2A2A; }}
    QPushButton:disabled {{ color: #555555; border-color: #444; }}
"""


def _btn(label: str, color: str = "#CCCCCC") -> QPushButton:
    b = QPushButton(label)
    b.setStyleSheet(_BTN_BASE.format(color=color))
    return b


class _ControlPanel(QGroupBox):
    """Top section of the sidebar — macro operation buttons."""

    record_requested = Signal()
    stop_requested   = Signal()
    play_requested   = Signal()
    clear_requested  = Signal()
    save_requested   = Signal()
    load_requested   = Signal()

    def __init__(self) -> None:
        super().__init__("操作")
        self.setStyleSheet("""
            QGroupBox {
                color: #AAAAAA; border: 1px solid #3C3C3C;
                border-radius: 4px; margin-top: 6px; font-size: 11px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; }
        """)
        self._build_ui()
        self.set_state("idle")

    def _build_ui(self) -> None:
        grid = QGridLayout(self)
        grid.setSpacing(4)
        grid.setContentsMargins(6, 14, 6, 6)

        self._rec  = _btn("⏺  記録",  "#F48771")
        self._stop = _btn("⏹  停止",  "#CCCCCC")
        self._play = _btn("▶  再生",  "#4EC9B0")
        self._clr  = _btn("✕  クリア","#CCCCCC")
        self._save = _btn("💾  保存",  "#CCCCCC")
        self._load = _btn("📂  読込",  "#CCCCCC")

        grid.addWidget(self._rec,  0, 0)
        grid.addWidget(self._stop, 0, 1)
        grid.addWidget(self._play, 1, 0)
        grid.addWidget(self._clr,  1, 1)
        grid.addWidget(self._save, 2, 0)
        grid.addWidget(self._load, 2, 1)

        self._rec.clicked.connect(self.record_requested)
        self._stop.clicked.connect(self.stop_requested)
        self._play.clicked.connect(self.play_requested)
        self._clr.clicked.connect(self.clear_requested)
        self._save.clicked.connect(self.save_requested)
        self._load.clicked.connect(self.load_requested)

    def set_state(self, state: str) -> None:
        """Enable/disable buttons based on 'idle' | 'recording' | 'playing'."""
        idle      = (state == "idle")
        recording = (state == "recording")
        playing   = (state == "playing")

        self._rec.setEnabled(idle)
        self._stop.setEnabled(recording or playing)
        self._play.setEnabled(idle)
        self._clr.setEnabled(idle)
        self._save.setEnabled(idle)
        self._load.setEnabled(idle)

        # Visual cue: pulse red border on record button when active
        if recording:
            self._rec.setStyleSheet(
                self._rec.styleSheet() +
                "QPushButton { border: 1px solid #F44747; }"
            )
        else:
            self._rec.setStyleSheet(_BTN_BASE.format(color="#F48771"))


class Sidebar(QWidget):
    """Left sidebar combining the control panel and the file tree."""

    record_requested    = Signal()
    stop_requested      = Signal()
    play_requested      = Signal()
    clear_requested     = Signal()
    save_requested      = Signal()
    load_requested      = Signal()
    file_open_requested = Signal(Path)

    def __init__(self, macros_dir: Path) -> None:
        super().__init__()
        self.setMinimumWidth(190)
        self.setMaximumWidth(320)
        self.setStyleSheet("background-color: #252526;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self._ctrl = _ControlPanel()
        layout.addWidget(self._ctrl)

        self._tree = MacroFileTree(macros_dir)
        layout.addWidget(self._tree, stretch=1)

        # Forward signals
        self._ctrl.record_requested.connect(self.record_requested)
        self._ctrl.stop_requested.connect(self.stop_requested)
        self._ctrl.play_requested.connect(self.play_requested)
        self._ctrl.clear_requested.connect(self.clear_requested)
        self._ctrl.save_requested.connect(self.save_requested)
        self._ctrl.load_requested.connect(self.load_requested)
        self._tree.file_open_requested.connect(self.file_open_requested)

    def set_state(self, state: str) -> None:
        self._ctrl.set_state(state)

    def refresh_tree(self) -> None:
        self._tree.refresh()
