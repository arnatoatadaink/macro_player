"""Single editor tab — CodeEditor + syntax highlighting + file I/O."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog
from PySide6.QtCore import Signal
from PySide6.QtGui import QTextCursor

from src.gui.code_editor import CodeEditor
from src.gui.syntax_highlighter import MacroSyntaxHighlighter


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
