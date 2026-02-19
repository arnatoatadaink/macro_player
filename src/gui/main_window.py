"""Main application window."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QDockWidget,
    QLabel, QFileDialog, QMessageBox, QApplication,
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence, QCloseEvent

from src.core.settings_manager import SettingsManager
from src.core.recorder import MacroRecorder
from src.core.player import MacroPlayer
from src.core.hotkey_manager import HotkeyManager
from src.gui.sidebar import Sidebar
from src.gui.editor import EditorArea, EditorTab
from src.gui.log_panel import LogPanel
from src.gui.settings_dialog import SettingsDialog
from src.gui.variable_panel import VariablePanel

_STYLE = """
    QMainWindow           { background: #1E1E1E; }
    QSplitter::handle     { background: #3C3C3C; }
    QMenuBar              { background: #3C3C3C; color: #CCCCCC; }
    QMenuBar::item        { padding: 4px 10px; }
    QMenuBar::item:selected { background: #094771; }
    QMenu                 { background: #252526; color: #CCCCCC; border: 1px solid #454545; }
    QMenu::item           { padding: 4px 20px; }
    QMenu::item:selected  { background: #094771; }
    QMenu::separator      { height: 1px; background: #3C3C3C; margin: 2px 0; }
    QDockWidget::title    {
        background: #333333; color: #CCCCCC;
        padding: 4px 6px; font-size: 12px;
    }
    QDockWidget           { color: #CCCCCC; }
    QStatusBar            { background: #007ACC; color: #FFFFFF; font-size: 12px; }
    QStatusBar::item      { border: none; }
"""


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsManager, base_dir: Path) -> None:
        super().__init__()
        self._settings  = settings
        self._base_dir  = base_dir
        self._macros_dir = base_dir / settings.macros_dir
        self._macros_dir.mkdir(parents=True, exist_ok=True)

        self._recorder = MacroRecorder(settings)
        self._player   = MacroPlayer(settings, base_dir)
        self._hotkeys  = HotkeyManager(settings, self)
        self._state    = "idle"   # "idle" | "recording" | "playing"

        self.setWindowTitle("Macro Player")
        self.setMinimumSize(920, 600)
        self.setStyleSheet(_STYLE)

        self._build_central()
        self._build_log_dock()
        self._build_variable_dock()
        self._build_menu()
        self._build_statusbar()
        self._connect_signals()
        self._restore_geometry()

        self._log("INFO", "Macro Player 起動完了")

    # ================================================================
    # UI construction
    # ================================================================

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        self._sidebar = Sidebar(self._macros_dir)
        splitter.addWidget(self._sidebar)

        self._editor = EditorArea(self._macros_dir)
        splitter.addWidget(self._editor)

        splitter.setSizes([220, 780])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

    def _build_log_dock(self) -> None:
        self._log_panel = LogPanel()

        dock = QDockWidget("ログ", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        dock.setWidget(self._log_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self._log_dock = dock
        # Set initial dock height after show
        self.resizeDocks([dock], [160], Qt.Orientation.Vertical)

    def _build_variable_dock(self) -> None:
        self._var_panel = VariablePanel()

        dock = QDockWidget("変数ウォッチ", self)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        dock.setWidget(self._var_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        dock.hide()              # hidden by default; shown when playback starts
        self._var_dock = dock

    def _build_menu(self) -> None:
        mb = self.menuBar()

        # ── File ────────────────────────────────────────────────────────
        file_menu = mb.addMenu("ファイル(&F)")
        self._a_new    = QAction("新規(&N)",           self, shortcut=QKeySequence.StandardKey.New)
        self._a_open   = QAction("開く(&O)...",         self, shortcut=QKeySequence.StandardKey.Open)
        self._a_save   = QAction("保存(&S)",            self, shortcut=QKeySequence.StandardKey.Save)
        self._a_saveas = QAction("名前を付けて保存(&A)...", self, shortcut=QKeySequence("Ctrl+Shift+S"))
        self._a_exit   = QAction("終了(&X)",            self, shortcut=QKeySequence("Alt+F4"))
        file_menu.addActions([self._a_new, self._a_open, self._a_save, self._a_saveas])
        file_menu.addSeparator()
        file_menu.addAction(self._a_exit)

        # ── Macro ───────────────────────────────────────────────────────
        macro_menu = mb.addMenu("マクロ(&M)")
        self._a_record = QAction("記録開始(&R)", self, shortcut="Ctrl+Shift+R")
        self._a_stop   = QAction("停止(&X)",     self, shortcut="Escape")
        self._a_play   = QAction("再生(&P)",     self, shortcut="Ctrl+Shift+P")
        self._a_clear  = QAction("クリア(&C)",   self)
        macro_menu.addActions([self._a_record, self._a_stop, self._a_play, self._a_clear])

        # ── Tools ───────────────────────────────────────────────────────
        tools_menu = mb.addMenu("ツール(&T)")
        a_settings = QAction("設定(&O)...", self)
        a_settings.triggered.connect(self._open_settings)
        log_toggle = self._log_dock.toggleViewAction()
        log_toggle.setText("ログパネル(&L)")
        var_toggle = self._var_dock.toggleViewAction()
        var_toggle.setText("変数ウォッチ(&V)")
        tools_menu.addActions([a_settings, log_toggle, var_toggle])

        # ── Help ────────────────────────────────────────────────────────
        help_menu = mb.addMenu("ヘルプ(&H)")
        a_about = QAction("バージョン情報(&A)", self)
        a_about.triggered.connect(self._show_about)
        help_menu.addAction(a_about)

    def _build_statusbar(self) -> None:
        self._status_label = QLabel("準備完了")
        self._cursor_label = QLabel("Ln 1, Col 1")
        sb = self.statusBar()
        sb.addWidget(self._status_label)
        sb.addPermanentWidget(self._cursor_label)

    # ================================================================
    # Signal wiring
    # ================================================================

    def _connect_signals(self) -> None:
        # Sidebar → actions
        self._sidebar.record_requested.connect(self._a_record.trigger)
        self._sidebar.stop_requested.connect(self._a_stop.trigger)
        self._sidebar.play_requested.connect(self._a_play.trigger)
        self._sidebar.clear_requested.connect(self._a_clear.trigger)
        self._sidebar.save_requested.connect(self._a_save.trigger)
        self._sidebar.load_requested.connect(self._a_open.trigger)
        self._sidebar.file_open_requested.connect(self._editor.open_file)

        # Menu actions
        self._a_new.triggered.connect(lambda: self._editor.new_tab())
        self._a_open.triggered.connect(self._open_file_dialog)
        self._a_save.triggered.connect(self._save_current)
        self._a_saveas.triggered.connect(self._save_current_as)
        self._a_exit.triggered.connect(self.close)
        self._a_record.triggered.connect(self._do_record)
        self._a_stop.triggered.connect(self._do_stop)
        self._a_play.triggered.connect(self._do_play)
        self._a_clear.triggered.connect(self._do_clear)

        # Recorder
        self._recorder.command_recorded.connect(self._editor.append_text)
        self._recorder.status_changed.connect(self._on_recorder_status)

        # Player
        self._player.log_message.connect(self._log)
        self._player.status_changed.connect(self._on_player_status)
        self._player.progress.connect(self._on_play_progress)
        self._player.line_changed.connect(self._editor.highlight_playback_line)
        self._player.vars_updated.connect(self._on_vars_updated)

        # Global hotkeys
        self._hotkeys.record_triggered.connect(self._do_record)
        self._hotkeys.stop_triggered.connect(self._do_stop)
        self._hotkeys.play_triggered.connect(self._do_play)
        self._hotkeys.start()

        # Editor: update cursor position in status bar
        self._editor.current_file_changed.connect(self._on_file_changed)
        self._editor.currentChanged.connect(self._reconnect_cursor_signal)

    # ================================================================
    # Action handlers
    # ================================================================

    def _do_record(self) -> None:
        if self._state != "idle":
            return
        self._recorder.start()

    def _do_stop(self) -> None:
        if self._state == "recording":
            self._recorder.stop()
        elif self._state == "playing":
            self._player.stop()

    def _do_play(self) -> None:
        if self._state != "idle":
            return
        text = self._editor.get_current_text()
        if not text.strip():
            self._log("WARNING", "再生するマクロが空です")
            return
        self._player.play(text)

    def _do_clear(self) -> None:
        tab = self._editor.current_tab()
        if tab:
            tab.editor.clear()

    def _save_current(self) -> None:
        self._editor.save_current()
        self._sidebar.refresh_tree()

    def _save_current_as(self) -> None:
        self._editor.save_current_as()
        self._sidebar.refresh_tree()

    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "マクロファイルを開く",
            str(self._macros_dir),
            "Macro Files (*.macro);;All Files (*)",
        )
        if path:
            self._editor.open_file(Path(path))

    def _open_settings(self) -> None:
        from PySide6.QtWidgets import QDialog
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Hotkeys may have changed — restart the global listener
            self._hotkeys.restart()

    # ================================================================
    # State callbacks
    # ================================================================

    def _on_recorder_status(self, status: str) -> None:
        if status == "recording":
            self._state = "recording"
            self._status_label.setText("⏺ 記録中...")
            self._sidebar.set_state("recording")
            self._log("INFO", "記録を開始しました")
        else:
            self._state = "idle"
            self._status_label.setText("準備完了")
            self._sidebar.set_state("idle")
            self._log("INFO", "記録を停止しました")
            self._sidebar.refresh_tree()

    def _on_player_status(self, status: str) -> None:
        if status == "playing":
            self._state = "playing"
            self._status_label.setText("▶ 再生中...")
            self._sidebar.set_state("playing")
            # Auto-show the variable watch panel when playback starts
            self._var_dock.show()
        else:
            self._state = "idle"
            self._status_label.setText("準備完了")
            self._sidebar.set_state("idle")
            self._cursor_label.setText("Ln 1, Col 1")
            self._editor.clear_playback_highlight()

    def _on_vars_updated(self, variables: dict) -> None:
        self._var_panel.update_vars(variables)

    def _on_play_progress(self, current: int, total: int) -> None:
        label = f"再生: {current} コマンド" if total == 0 else f"再生: {current} / {total}"
        self._cursor_label.setText(label)

    def _on_file_changed(self, path: Path | None) -> None:
        name = path.name if path else "新規マクロ"
        self.setWindowTitle(f"Macro Player  —  {name}")
        self._reconnect_cursor_signal()

    def _reconnect_cursor_signal(self, _idx: int = -1) -> None:
        """Connect cursor-position updates for the newly focused editor tab."""
        tab = self._editor.current_tab()
        if tab:
            # Disconnect old connections first (multiple connect calls accumulate)
            try:
                tab.editor.cursorPositionChanged.disconnect(self._update_cursor_label)
            except RuntimeError:
                pass
            tab.editor.cursorPositionChanged.connect(self._update_cursor_label)
            self._update_cursor_label()

    def _update_cursor_label(self) -> None:
        tab = self._editor.current_tab()
        if tab and self._state != "playing":
            cur = tab.editor.textCursor()
            ln  = cur.blockNumber() + 1
            col = cur.columnNumber() + 1
            self._cursor_label.setText(f"Ln {ln}, Col {col}")

    # ================================================================
    # Helpers
    # ================================================================

    def _log(self, level: str, message: str) -> None:
        self._log_panel.log(level, message)

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "バージョン情報",
            "<b>Macro Player</b> v0.1.0<br>"
            "Python 3 + PySide6<br><br>"
            "Windows 11 向けマクロレコーダー/プレイヤー",
        )

    # ================================================================
    # Geometry persistence
    # ================================================================

    def _restore_geometry(self) -> None:
        qs = QSettings("MacroPlayer", "MainWindow")
        geom = qs.value("geometry")
        state = qs.value("windowState")
        if geom:
            self.restoreGeometry(geom)
        else:
            self.resize(1280, 800)
        if state:
            self.restoreState(state)

    def closeEvent(self, event: QCloseEvent) -> None:
        # Check all tabs for unsaved changes
        for i in range(self._editor.count()):
            w = self._editor.widget(i)
            if isinstance(w, EditorTab) and w.is_modified:
                reply = QMessageBox.question(
                    self, "終了確認",
                    "保存されていない変更があります。終了しますか？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    event.ignore()
                    return
                break   # User confirmed once is enough for exit

        # Cleanup
        self._hotkeys.stop()

        # Persist window state
        qs = QSettings("MacroPlayer", "MainWindow")
        qs.setValue("geometry",    self.saveGeometry())
        qs.setValue("windowState", self.saveState())
        event.accept()
