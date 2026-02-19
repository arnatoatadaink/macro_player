"""Settings dialog — edit settings.ini via a form UI."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QDialogButtonBox, QGroupBox, QTabWidget, QWidget,
)
from PySide6.QtCore import Qt

from src.core.settings_manager import SettingsManager

_DARK = """
    QDialog, QWidget, QGroupBox {
        background-color: #252526; color: #CCCCCC;
    }
    QGroupBox { border: 1px solid #3C3C3C; border-radius: 4px; margin-top: 6px; padding-top: 6px; }
    QGroupBox::title { color: #AAAAAA; subcontrol-origin: margin; left: 8px; }
    QLineEdit, QSpinBox, QDoubleSpinBox {
        background: #3C3C3C; color: #CCCCCC;
        border: 1px solid #555; border-radius: 3px; padding: 3px;
    }
    QCheckBox { color: #CCCCCC; }
    QTabWidget::pane { border: 1px solid #3C3C3C; }
    QTabBar::tab { background:#2D2D2D; color:#CCCCCC; padding:5px 14px; }
    QTabBar::tab:selected { background:#252526; }
    QDialogButtonBox QPushButton {
        background:#3C3C3C; color:#CCCCCC; border:1px solid #555;
        border-radius:3px; padding:4px 14px; min-width:60px;
    }
    QDialogButtonBox QPushButton:hover { background:#4A4A4A; }
"""


class SettingsDialog(QDialog):
    def __init__(self, settings: SettingsManager, parent=None) -> None:
        super().__init__(parent)
        self._s = settings
        self.setWindowTitle("設定")
        self.setMinimumWidth(420)
        self.setStyleSheet(_DARK)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # ── Tab 1: Input ────────────────────────────────────────────────
        inp_widget = QWidget()
        inp_form = QFormLayout(inp_widget)
        inp_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._mousewait = QSpinBox(minimum=0, maximum=10_000, suffix=" ms")
        self._mousewait.setValue(self._s.mousewait)

        self._keywait = QSpinBox(minimum=0, maximum=10_000, suffix=" ms")
        self._keywait.setValue(self._s.keywait)

        self._speed = QDoubleSpinBox(minimum=0.1, maximum=10.0, singleStep=0.1, decimals=1)
        self._speed.setValue(self._s.playback_speed)

        self._relative = QCheckBox()
        self._relative.setChecked(self._s.getbool("INPUT", "relative_mode", False))

        self._timestamps = QCheckBox()
        self._timestamps.setChecked(self._s.getbool("INPUT", "record_timestamps", True))

        inp_form.addRow("マウスクリック待機時間:", self._mousewait)
        inp_form.addRow("キー押下待機時間:", self._keywait)
        inp_form.addRow("再生速度:", self._speed)
        inp_form.addRow("相対座標モード:", self._relative)
        inp_form.addRow("タイムスタンプ記録:", self._timestamps)
        tabs.addTab(inp_widget, "入力")

        # ── Tab 2: Hotkeys ───────────────────────────────────────────────
        hk_widget = QWidget()
        hk_form = QFormLayout(hk_widget)
        hk_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._hk_record = QLineEdit(self._s.get("HOTKEYS", "record_start", "Ctrl+Shift+R"))
        self._hk_stop   = QLineEdit(self._s.get("HOTKEYS", "record_stop",  "Ctrl+Shift+X"))
        self._hk_play   = QLineEdit(self._s.get("HOTKEYS", "play",         "Ctrl+Shift+P"))

        hk_form.addRow("記録開始:", self._hk_record)
        hk_form.addRow("記録停止:", self._hk_stop)
        hk_form.addRow("再生:", self._hk_play)
        tabs.addTab(hk_widget, "ホットキー")

        layout.addWidget(tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _save(self) -> None:
        self._s.set("INPUT", "mousewait",        str(self._mousewait.value()))
        self._s.set("INPUT", "keywait",          str(self._keywait.value()))
        self._s.set("INPUT", "playback_speed",   str(round(self._speed.value(), 1)))
        self._s.set("INPUT", "relative_mode",    str(self._relative.isChecked()).lower())
        self._s.set("INPUT", "record_timestamps",str(self._timestamps.isChecked()).lower())
        self._s.set("HOTKEYS", "record_start",   self._hk_record.text().strip())
        self._s.set("HOTKEYS", "record_stop",    self._hk_stop.text().strip())
        self._s.set("HOTKEYS", "play",           self._hk_play.text().strip())
        self.accept()
