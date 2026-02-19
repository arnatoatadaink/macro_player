"""Bottom log panel — displays timestamped execution messages."""
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel,
)
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QFont

_LEVEL_COLORS: dict[str, str] = {
    "INFO":    "#D4D4D4",
    "SUCCESS": "#4EC9B0",
    "WARNING": "#CE9178",
    "ERROR":   "#F44747",
    "DEBUG":   "#858585",
}


class LogPanel(QWidget):
    """Read-only text area for execution logs with colour-coded levels."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(2)

        # Header
        header = QHBoxLayout()
        title = QLabel("実行ログ")
        title.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        header.addWidget(title)
        header.addStretch()
        clear_btn = QPushButton("クリア")
        clear_btn.setFixedWidth(56)
        clear_btn.setStyleSheet(
            "QPushButton { background:#3C3C3C; color:#CCCCCC; border:none;"
            " border-radius:3px; padding:2px 6px; }"
            "QPushButton:hover { background:#4A4A4A; }"
        )
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        # Log text area
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text.setFont(font)
        self._text.setStyleSheet(
            "QTextEdit { background:#0C0C0C; color:#CCCCCC; border:none; }"
        )
        layout.addWidget(self._text)

    def log(self, level: str, message: str) -> None:
        """Append a timestamped, colour-coded log entry."""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color = _LEVEL_COLORS.get(level.upper(), "#D4D4D4")

        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        ts_fmt = QTextCharFormat()
        ts_fmt.setForeground(QColor("#858585"))
        cursor.setCharFormat(ts_fmt)
        cursor.insertText(f"[{ts}] ")

        lvl_fmt = QTextCharFormat()
        lvl_fmt.setForeground(QColor(color))
        cursor.setCharFormat(lvl_fmt)
        cursor.insertText(f"[{level.upper():7}] {message}\n")

        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def clear(self) -> None:
        self._text.clear()
