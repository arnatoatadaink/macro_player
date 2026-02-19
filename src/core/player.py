"""Macro playback engine — Phase 5.

Architecture
------------
MacroPlayer (QObject, main thread)
  └─ _PlaybackThread (QThread, one instance per play() call)
       ├─ parser.parse_lines()    — tokenise + sugar-expand
       ├─ ast_builder.build_ast() — build control-flow AST
       ├─ condition.eval_condition — evaluates IF / WHILE / UNTIL conditions
       ├─ variable_store.VariableStore — #var scope for the session
       └─ runner.ASTRunner.run()  — execute AST with full control flow

Signals forwarded to the UI
---------------------------
log_message(level, msg)      → LogPanel
status_changed("playing" | "stopped")
progress(executed_cmd_count, 0)   — 0 = total unknown at start
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from src.core.executor       import CommandExecutor
from src.core.parser         import parse_lines
from src.core.ast_builder    import build_ast, ParseError
from src.core.condition      import eval_condition
from src.core.variable_store import VariableStore
from src.core.runner         import ASTRunner, _Exit


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class _PlaybackThread(QThread):
    log_msg      = Signal(str, str)   # (level, message)
    progress     = Signal(int, int)   # (commands_executed, 0)
    line_changed = Signal(int)        # 0-based source line being executed
    vars_updated = Signal(object)     # dict[str, Any] — current variable snapshot

    def __init__(
        self,
        token_lines:   list[list[str]],
        macros_dir:    Path,
        templates_dir: Path,
        settings,
    ) -> None:
        super().__init__()
        self._token_lines   = token_lines
        self._macros_dir    = macros_dir
        self._templates_dir = templates_dir
        self._settings      = settings
        self._executor      = CommandExecutor(settings,
                                              log_callback=self._emit_log)
        self._variables     = VariableStore()   # fresh scope per playback
        self._cmd_count     = 0

    def stop(self) -> None:
        self._executor.stop_event.set()

    # ------------------------------------------------------------------

    def _emit_log(self, level: str, msg: str) -> None:
        self.log_msg.emit(level, msg)

    def _on_cmd_executed(self, line_num: int = -1) -> None:
        self._cmd_count += 1
        self.progress.emit(self._cmd_count, 0)
        if line_num >= 0:
            self.line_changed.emit(line_num)

    def _cond_eval(self, tokens: list[str]) -> bool:
        return eval_condition(
            tokens,
            templates_dir = self._templates_dir,
            log           = self._emit_log,
            variables     = self._variables,
        )

    # ------------------------------------------------------------------

    def run(self) -> None:
        # Build AST
        try:
            ast_nodes = build_ast(self._token_lines)
        except ParseError as exc:
            self.log_msg.emit("ERROR", f"構文エラー: {exc}")
            return

        # Run
        runner = ASTRunner(
            executor         = self._executor,
            cond_fn          = self._cond_eval,
            macros_dir       = self._macros_dir,
            templates_dir    = self._templates_dir,
            settings         = self._settings,
            log_fn           = self._emit_log,
            on_cmd           = self._on_cmd_executed,
            variables        = self._variables,
            vars_changed_fn  = lambda d: self.vars_updated.emit(d),
        )

        try:
            runner.run(ast_nodes)
            self.log_msg.emit("SUCCESS", f"再生完了 ({self._cmd_count} コマンド実行)")
        except _Exit:
            self.log_msg.emit("INFO", f"再生中断 ({self._cmd_count} コマンド実行済)")
        except Exception as exc:          # noqa: BLE001
            self.log_msg.emit("ERROR", f"再生エラー: {exc!r}")


# ---------------------------------------------------------------------------
# Public player
# ---------------------------------------------------------------------------

class MacroPlayer(QObject):
    """Parses and plays back macro text via a background QThread.

    Parameters
    ----------
    settings : SettingsManager
    base_dir : Path
        Project root — used to resolve macros_dir and templates_dir.
    """

    log_message    = Signal(str, str)
    status_changed = Signal(str)
    progress       = Signal(int, int)
    line_changed   = Signal(int)
    vars_updated   = Signal(object)   # dict[str, Any]

    def __init__(self, settings, base_dir: Path) -> None:
        super().__init__()
        self._settings      = settings
        self._macros_dir    = base_dir / settings.macros_dir
        self._templates_dir = base_dir / settings.templates_dir
        self._thread: Optional[_PlaybackThread] = None

    # ------------------------------------------------------------------

    @property
    def is_playing(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def play(self, text: str) -> None:
        if self.is_playing:
            return

        token_lines = parse_lines(text, self._settings.syntax_sugar)
        if not token_lines:
            self.log_message.emit("WARNING", "実行できるコマンドが見つかりません")
            return

        self._thread = _PlaybackThread(
            token_lines   = token_lines,
            macros_dir    = self._macros_dir,
            templates_dir = self._templates_dir,
            settings      = self._settings,
        )
        self._thread.log_msg.connect(self.log_message)
        self._thread.progress.connect(self.progress)
        self._thread.line_changed.connect(self.line_changed)
        self._thread.vars_updated.connect(self.vars_updated)
        self._thread.finished.connect(self._on_finished)

        self._thread.start()
        self.status_changed.emit("playing")
        self.log_message.emit("INFO", f"再生開始: {len(token_lines)} コマンド行")

    def stop(self) -> None:
        if self._thread:
            self._thread.stop()
            self._thread.wait(3000)

    def _on_finished(self) -> None:
        self._thread = None
        self.status_changed.emit("stopped")
