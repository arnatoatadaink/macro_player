"""Code editor widget with line numbers and syntax highlighting."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QPlainTextEdit, QTextEdit
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QColor, QPainter, QFont, QTextCursor, QTextFormat


# ---------------------------------------------------------------------------
# Line-number gutter
# ---------------------------------------------------------------------------

class _LineNumberArea(QWidget):
    """Painted gutter widget that lives inside CodeEditor."""

    def __init__(self, editor: "CodeEditor") -> None:
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
