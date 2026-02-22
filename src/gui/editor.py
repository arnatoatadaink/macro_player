"""Backward-compatible re-exports for the split editor modules.

Previously this file contained CodeEditor, EditorTab, and EditorArea
in a single 382-line module.  They now live in:
  - src/gui/code_editor.py  (CodeEditor)
  - src/gui/editor_tab.py   (EditorTab)
  - src/gui/editor_area.py  (EditorArea)

Existing ``from src.gui.editor import EditorArea, EditorTab`` imports
continue to work unchanged.
"""
from src.gui.code_editor import CodeEditor   # noqa: F401
from src.gui.editor_tab  import EditorTab    # noqa: F401
from src.gui.editor_area import EditorArea   # noqa: F401
