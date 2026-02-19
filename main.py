"""Macro Player — Entry point."""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.core.settings_manager import SettingsManager
from src.gui.main_window import MainWindow

BASE_DIR = Path(__file__).parent


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Macro Player")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("MacroPlayer")
    app.setStyle("Fusion")

    settings = SettingsManager(BASE_DIR / "settings.ini")
    window = MainWindow(settings, BASE_DIR)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
