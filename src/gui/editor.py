"""Tabbed code editor with line numbers and syntax highlighting."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QPlainTextEdit, QTextEdit,
    QFileDialog, QMessageBox, QPushButton,
)
from PySide6.QtCore import Qt, QRect, QSize, Signal
from PySide6.QtGui import (
    QColor, QPainter, QFont, QTextCursor,
    QTextCharFormat, QTextFormat,
)

from src.gui.syntax_highlighter import MacroSyntaxHighlighter

# ---------------------------------------------------------------------------
# Line-number gutter
# ---------------------------------------------------------------------------

class _LineNumberArea(QWidget):
    """Painted gutter widget that lives inside CodeEditor."""

    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """QPlainTextEdit with line numbers, current-line highlight, dark theme."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._gutter = _LineNumberArea(self)

        # Font
        font = QFont("Cascadia Code", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        if not font.exactMatch():
            font = QFont("Consolas", 11)
        self.setFont(font)

        # No word wrap
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Tab stop = 4 spaces
        metrics = self.fontMetrics()
        self.setTabStopDistance(4 * metrics.horizontalAdvance(" "))

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                selection-background-color: #264F78;
            }
        """)

        self.blockCountChanged.connect(self._update_gutter_width)
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_gutter_width(0)
        self._highlight_current_line()

    # ------------------------------------------------------------------
    def line_number_width(self) -> int:
        digits = max(3, len(str(max(1, self.blockCount()))))
        return 8 + self.fontMetrics().horizontalAdvance("9") * digits

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self._gutter)
        painter.fillRect(event.rect(), QColor("#252526"))

        block = self.firstVisibleBlock()
        block_num = block.blockNumber()
        offset = self.contentOffset()
        top = self.blockBoundingGeometry(block).translated(offset).top()
        bottom = top + self.blockBoundingRect(block).height()
        current = self.textCursor().blockNumber()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                color = QColor("#C6C6C6") if block_num == current else QColor("#858585")
                painter.setPen(color)
                painter.drawText(
                    0, int(top),
                    self._gutter.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_num + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_num += 1

    # ------------------------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._gutter.setGeometry(QRect(cr.left(), cr.top(), self.line_number_width(), cr.height()))

    def _update_gutter_width(self, _block_count: int) -> None:
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_gutter(self, rect: QRect, dy: int) -> None:
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width(0)

    def _highlight_current_line(self) -> None:
        extras: list[QTextEdit.ExtraSelection] = self._playback_selections()
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor("#2A2D2E"))
            sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extras.append(sel)
        self.setExtraSelections(extras)

    # ------------------------------------------------------------------
    # Playback line highlight
    # ------------------------------------------------------------------

    _playback_line: int = -1   # -1 = no highlight

    def highlight_playback_line(self, line_num: int) -> None:
        """Highlight a 0-based source line during playback (yellow-ish bg)."""
        self._playback_line = line_num
        self._highlight_current_line()
        # Scroll to the highlighted line
        block = self.document().findBlockByNumber(line_num)
        if block.isValid():
            cursor = QTextCursor(block)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()

    def clear_playback_highlight(self) -> None:
        """Remove the playback line highlight."""
        self._playback_line = -1
        self._highlight_current_line()

    def _playback_selections(self) -> list[QTextEdit.ExtraSelection]:
        """Return extra selections for the current playback line."""
        if self._playback_line < 0:
            return []
        block = self.document().findBlockByNumber(self._playback_line)
        if not block.isValid():
            return []
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor("#3A3A00"))
        sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.cursor = QTextCursor(block)
        sel.cursor.clearSelection()
        return [sel]


# ---------------------------------------------------------------------------
# Single editor tab
# ---------------------------------------------------------------------------

class EditorTab(QWidget):
    """One tab: a CodeEditor with syntax highlighting, backed by an optional file."""

    modified_changed = Signal(bool)

    def __init__(self, file_path: Path | None = None) -> None:
        super().__init__()
        self.file_path = file_path
        self._modified = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.editor = CodeEditor()
        MacroSyntaxHighlighter(self.editor.document())
        layout.addWidget(self.editor)

        if file_path and file_path.exists():
            text = file_path.read_text(encoding="utf-8")
            self.editor.setPlainText(text)
            self.editor.document().setModified(False)

        self.editor.document().modificationChanged.connect(self._on_modified)

    # ------------------------------------------------------------------
    def _on_modified(self, modified: bool) -> None:
        self._modified = modified
        self.modified_changed.emit(modified)

    @property
    def is_modified(self) -> bool:
        return self._modified

    @property
    def display_name(self) -> str:
        name = self.file_path.name if self.file_path else "新規マクロ"
        return ("* " if self._modified else "") + name

    def get_text(self) -> str:
        return self.editor.toPlainText()

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text)

    def append_line(self, line: str) -> None:
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(line.rstrip("\n") + "\n")
        self.editor.setTextCursor(cursor)

    def save(self) -> bool:
        if not self.file_path:
            return self.save_as()
        self.file_path.write_text(self.get_text(), encoding="utf-8")
        self.editor.document().setModified(False)
        return True

    def save_as(self) -> bool:
        start = str(self.file_path) if self.file_path else ""
        path, _ = QFileDialog.getSaveFileName(
            self, "名前を付けて保存", start,
            "Macro Files (*.macro);;All Files (*)"
        )
        if path:
            self.file_path = Path(path)
            return self.save()
        return False


# ---------------------------------------------------------------------------
# Tabbed editor area
# ---------------------------------------------------------------------------

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
