"""Syntax highlighter for the macro language."""
from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

from src.core.prefix import VARIABLE_REGPREFIX, COMMENT_REGPREFIX

# ---------------------------------------------------------------------------
# Keyword sets
# ---------------------------------------------------------------------------
_MOUSE_CMDS = {
    "MOUSE_POS", "MOUSE_MOVE", "MOUSE_LEFT_CLICK", "MOUSE_RIGHT_CLICK",
    "MOUSE_MIDDLE_CLICK", "MOUSE_LEFT_DOWN", "MOUSE_RIGHT_DOWN",
    "MOUSE_MIDDLE_DOWN", "MOUSE_LEFT_UP", "MOUSE_RIGHT_UP",
    "MOUSE_MIDDLE_UP", "WHEEL",
    "POS", "LEFT_BUTTON", "RIGHT_BUTTON", "MIDDLE_BUTTON",
    "LEFT_BUTTON_DOWN", "RIGHT_BUTTON_DOWN", "MIDDLE_BUTTON_DOWN",
    "LEFT_BUTTON_UP", "RIGHT_BUTTON_UP", "MIDDLE_BUTTON_UP",
}

_KEY_CMDS = {
    "KEY", "KEYS", "KEY_DOWN", "KEY_UP", "KEYS_DOWN", "KEYS_UP", "TYPE",
}

_CTRL_KEYWORDS = {
    "IF", "ELSEIF", "ELSE", "ENDIF",
    "LOOP", "ENDLOOP",
    "WHILE", "ENDWHILE",
    "REPEAT", "UNTIL",
    "CALL", "FUNCTION",
    "BREAK", "CONTINUE", "RETURN", "EXIT",
    "TRY", "CATCH", "ENDTRY",
}

_MISC_CMDS = {
    "WAIT", "PRINT", "SCREENSHOT",
    "CLIPBOARD_SET", "CLIPBOARD_GET",
    "WINDOW_FOCUS", "WINDOW_MOVE", "WINDOW_RESIZE", "WINDOW_CLOSE",
    "MOUSE_GET_POS",
}

# ---------------------------------------------------------------------------
# Colour palette (VS Code Dark+ inspired)
# ---------------------------------------------------------------------------
_COL_COMMENT  = "#6A9955"   # green-grey
_COL_STRING   = "#CE9178"   # orange
_COL_VARIABLE = "#9CDCFE"   # light blue
_COL_CTRL     = "#C586C0"   # purple
_COL_MOUSE    = "#4FC1FF"   # cyan
_COL_KEY      = "#DCDCAA"   # yellow
_COL_MISC     = "#4EC9B0"   # teal
_COL_NUMBER   = "#B5CEA8"   # light green
_COL_OPERATOR = "#D4D4D4"   # near-white


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


def _keyword_pattern(words: set[str]) -> str:
    escaped = sorted(words, key=len, reverse=True)
    return r"\b(" + "|".join(escaped) + r")\b"


class MacroSyntaxHighlighter(QSyntaxHighlighter):
    """QSyntaxHighlighter for .macro files."""

    def __init__(self, document) -> None:
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self._build_rules()

    def _build_rules(self) -> None:
        add = self._rules.append

        # 1. Strings (before comments so "#" inside strings is not a comment)
        add((QRegularExpression(r'"[^"]*"'), _fmt(_COL_STRING)))

        # 2. Variables: $varname — must start with letter/underscore after $
        add((QRegularExpression(VARIABLE_REGPREFIX + r"[A-Za-z_]\w*"), _fmt(_COL_VARIABLE)))

        # 3. Control keywords (highest priority)
        add((QRegularExpression(_keyword_pattern(_CTRL_KEYWORDS)), _fmt(_COL_CTRL, bold=True)))

        # 4. Mouse commands
        add((QRegularExpression(_keyword_pattern(_MOUSE_CMDS)), _fmt(_COL_MOUSE, bold=True)))

        # 5. Key/keyboard commands
        add((QRegularExpression(_keyword_pattern(_KEY_CMDS)), _fmt(_COL_KEY, bold=True)))

        # 6. Misc commands
        add((QRegularExpression(_keyword_pattern(_MISC_CMDS)), _fmt(_COL_MISC, bold=True)))

        # 7. Numbers
        add((QRegularExpression(r"\b\d+(\.\d+)?\b"), _fmt(_COL_NUMBER)))

        # 8. Operators
        add((QRegularExpression(r"[+\-*/=<>!&|]+"), _fmt(_COL_OPERATOR)))

        # 9. Comments: # to end of line ($ prefix means variables, so # is always comment)
        add((QRegularExpression(COMMENT_REGPREFIX + r".*$"), _fmt(_COL_COMMENT, italic=True)))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
