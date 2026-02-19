"""Macro file tree — QTreeWidget listing *.macro files in macros/ dir."""
from pathlib import Path

from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu,
    QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QFileSystemWatcher
from PySide6.QtGui import QAction


class MacroFileTree(QTreeWidget):
    """Lists .macro files; emits file_open_requested on double-click."""

    file_open_requested = Signal(Path)

    def __init__(self, macros_dir: Path) -> None:
        super().__init__()
        self._macros_dir = macros_dir
        self._macros_dir.mkdir(parents=True, exist_ok=True)

        self.setHeaderLabel("マクロファイル")
        self.setColumnCount(1)
        self.setRootIsDecorated(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.setStyleSheet("""
            QTreeWidget {
                background-color: #252526;
                color: #CCCCCC;
                border: none;
                font-size: 12px;
            }
            QTreeWidget::item { padding: 3px 0; }
            QTreeWidget::item:selected { background-color: #094771; }
            QTreeWidget::item:hover:!selected { background-color: #2A2D2E; }
            QHeaderView::section {
                background: #333333;
                color: #AAAAAA;
                border: none;
                padding: 4px;
                font-size: 11px;
            }
        """)

        # Watch directory for changes (new/deleted files)
        self._watcher = QFileSystemWatcher([str(self._macros_dir)])
        self._watcher.directoryChanged.connect(self.refresh)

        self.itemDoubleClicked.connect(self._on_double_click)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Reload file list from macros directory."""
        self.clear()
        if not self._macros_dir.exists():
            return
        for f in sorted(self._macros_dir.glob("*.macro")):
            item = QTreeWidgetItem([f.name])
            item.setData(0, Qt.ItemDataRole.UserRole, f)
            item.setToolTip(0, str(f))
            self.addTopLevelItem(item)

    # ------------------------------------------------------------------
    def _on_double_click(self, item: QTreeWidgetItem, _col: int) -> None:
        path: Path | None = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self.file_open_requested.emit(path)

    # ------------------------------------------------------------------
    def _show_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background:#252526; color:#CCCCCC; border:1px solid #454545; }"
            "QMenu::item:selected { background:#094771; }"
        )

        if item:
            path: Path = item.data(0, Qt.ItemDataRole.UserRole)
            act_open = QAction("開く", self)
            act_open.triggered.connect(lambda: self.file_open_requested.emit(path))
            act_rename = QAction("名前変更...", self)
            act_rename.triggered.connect(lambda: self._rename(item, path))
            act_delete = QAction("削除", self)
            act_delete.triggered.connect(lambda: self._delete(path))
            menu.addActions([act_open, act_rename])
            menu.addSeparator()
            menu.addAction(act_delete)
            menu.addSeparator()

        act_new = QAction("新規マクロ...", self)
        act_new.triggered.connect(self._new_macro)
        menu.addAction(act_new)

        menu.exec(self.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    def _rename(self, _item: QTreeWidgetItem, path: Path) -> None:
        new_name, ok = QInputDialog.getText(
            self, "名前変更", "新しいファイル名（拡張子なし）:", text=path.stem
        )
        if ok and new_name.strip():
            new_path = path.parent / f"{new_name.strip()}.macro"
            try:
                path.rename(new_path)
            except OSError as e:
                QMessageBox.critical(self, "エラー", str(e))
            finally:
                self.refresh()

    def _delete(self, path: Path) -> None:
        reply = QMessageBox.question(
            self, "削除確認",
            f"'{path.name}' を削除しますか？\nこの操作は元に戻せません。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                path.unlink()
            except OSError as e:
                QMessageBox.critical(self, "エラー", str(e))
            finally:
                self.refresh()

    def _new_macro(self) -> None:
        name, ok = QInputDialog.getText(self, "新規マクロ", "マクロ名（拡張子なし）:")
        if ok and name.strip():
            new_path = self._macros_dir / f"{name.strip()}.macro"
            if new_path.exists():
                QMessageBox.warning(self, "警告", f"'{new_path.name}' は既に存在します。")
                return
            new_path.touch()
            self.refresh()
            self.file_open_requested.emit(new_path)
