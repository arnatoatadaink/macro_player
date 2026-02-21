"""Tabbed editor area managing multiple EditorTab instances."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QTabWidget, QMessageBox, QPushButton
from PySide6.QtCore import Qt, Signal

from src.gui.editor_tab import EditorTab


class EditorArea(QTabWidget):
    """QTabWidget managing multiple EditorTab instances."""

    current_file_changed = Signal(object)   # Path | None

    def __init__(self, macros_dir: Path) -> None:
        super().__init__()
        self._macros_dir = macros_dir

        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)

        # "+" corner button
        new_btn = QPushButton("+")
        new_btn.setFixedSize(26, 24)
        new_btn.setToolTip("新しいタブ (Ctrl+N)")
        new_btn.setStyleSheet(
            "QPushButton { border:none; font-weight:bold; color:#CCCCCC;"
            " background:transparent; font-size:16px; }"
            "QPushButton:hover { color:#FFFFFF; }"
        )
        new_btn.clicked.connect(lambda: self.new_tab())
        self.setCornerWidget(new_btn, Qt.Corner.TopRightCorner)

        self.setStyleSheet("""
            QTabWidget::pane { border: none; background: #1E1E1E; }
            QTabBar::tab {
                background: #2D2D2D; color: #AAAAAA;
                padding: 5px 14px; border: 1px solid #3C3C3C;
                min-width: 80px; max-width: 200px;
            }
            QTabBar::tab:selected {
                background: #1E1E1E; color: #FFFFFF; border-bottom-color: #1E1E1E;
            }
            QTabBar::tab:hover:!selected { background: #3C3C3C; }
            QTabBar::close-button {
                image: none; /* rely on default × */
                subcontrol-position: right;
            }
        """)

        self.tabCloseRequested.connect(self._close_tab)
        self.currentChanged.connect(self._on_current_changed)

        self.new_tab()  # Start with one empty tab

    # ------------------------------------------------------------------
    def new_tab(self, file_path: Path | None = None) -> EditorTab:
        tab = EditorTab(file_path)
        idx = self.addTab(tab, tab.display_name)
        tab.modified_changed.connect(lambda: self._refresh_title(tab))
        self.setCurrentIndex(idx)
        return tab

    def open_file(self, file_path: Path) -> None:
        # If already open, focus that tab
        for i in range(self.count()):
            w = self.widget(i)
            if isinstance(w, EditorTab) and w.file_path == file_path:
                self.setCurrentIndex(i)
                return
        self.new_tab(file_path)

    def save_current(self) -> None:
        tab = self.current_tab()
        if tab:
            tab.save()
            self._refresh_title(tab)

    def save_current_as(self) -> None:
        tab = self.current_tab()
        if tab:
            tab.save_as()
            self._refresh_title(tab)

    def current_tab(self) -> EditorTab | None:
        w = self.currentWidget()
        return w if isinstance(w, EditorTab) else None

    def get_current_text(self) -> str:
        tab = self.current_tab()
        return tab.get_text() if tab else ""

    def append_text(self, line: str) -> None:
        """Append a recorded command line to the current tab."""
        tab = self.current_tab()
        if tab:
            tab.append_line(line)

    # ------------------------------------------------------------------
    def _refresh_title(self, tab: EditorTab) -> None:
        idx = self.indexOf(tab)
        if idx >= 0:
            self.setTabText(idx, tab.display_name)

    def _close_tab(self, idx: int) -> None:
        tab = self.widget(idx)
        if isinstance(tab, EditorTab) and tab.is_modified:
            name = tab.display_name.lstrip("* ")
            reply = QMessageBox.question(
                self, "保存確認",
                f"'{name}' への変更を保存しますか？",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                if not tab.save():
                    return       # save-as was cancelled
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self.removeTab(idx)
        if self.count() == 0:
            self.new_tab()      # Always keep at least one tab

    def _on_current_changed(self, idx: int) -> None:
        tab = self.widget(idx)
        path = tab.file_path if isinstance(tab, EditorTab) else None
        self.current_file_changed.emit(path)

    # ------------------------------------------------------------------
    # Playback line tracking (delegated to current tab's editor)
    # ------------------------------------------------------------------

    def highlight_playback_line(self, line_num: int) -> None:
        tab = self.current_tab()
        if tab:
            tab.editor.highlight_playback_line(line_num)

    def clear_playback_highlight(self) -> None:
        tab = self.current_tab()
        if tab:
            tab.editor.clear_playback_highlight()
