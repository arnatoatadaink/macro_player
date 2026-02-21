# Macro Player リファクタリング計画

## 概要
全17ファイル（約3,863行）のコードベースを対象に、DRY原則の徹底・関心の分離・テスト追加を行う。
動作の変更は行わず、構造のみを改善する。

---

## Phase 1: 共有キーマッピングの統合 (`src/core/keys.py` 新規作成)

**課題**: `executor.py` (L34-78) と `recorder.py` (L30-81) にキー/ボタンのマッピングテーブルが重複している。

**変更内容**:
1. `src/core/keys.py` を新規作成し、以下を統合:
   - `_SPECIAL_KEYS` (executor.py L34-72) — 名前→pynput Key マッピング
   - `_BUTTON_MAP` (executor.py L74-78) — ボタン名→pynput Button マッピング
   - `_parse_key()` / `_parse_combo()` (executor.py L81-93) — ヘルパー関数
   - `_MODIFIERS` (recorder.py L30-35) — 修飾キーセット
   - `_MOD_NAMES` (recorder.py L37-46) — 修飾キー→名前マッピング
   - `_KEY_NAMES` (recorder.py L48-73) — pynput Key→マクロ名マッピング
   - `_BUTTON_CMDS` (recorder.py L77-81) — ボタン→コマンド名マッピング
   - `_key_name()` (recorder.py L98-106) — pynput Key→文字列変換

2. `executor.py` を更新: `from src.core.keys import ...` に変更
3. `recorder.py` を更新: `from src.core.keys import ...` に変更

---

## Phase 2: オプション依存の一元管理 (`src/utils/optional_deps.py` 新規作成)

**課題**: `cv2`, `mss`, `numpy`, `win32gui`, `win32con`, `pyperclip` の import が `executor.py`, `condition.py`, `expression.py` に散在し、try/except が重複。

**変更内容**:
1. `src/utils/optional_deps.py` を新規作成:
   ```python
   # 各オプションライブラリを一回だけ import し、成功/失敗フラグを公開
   try:
       import cv2
       import numpy as np
       HAS_CV = True
   except ImportError:
       cv2 = None
       np = None
       HAS_CV = False
   # 同様に mss, win32gui, win32con, pyperclip
   ```
2. `src/utils/__init__.py` を更新（空→必要な re-export を追加）
3. `condition.py` を更新: L34-46 のローカル import を除去し、`optional_deps` から import
4. `executor.py` を更新: L279, L286-289, L301, L312-313, L328, L377-380 の散在 import を除去
5. `expression.py` を更新: L159, L180-181 の散在 import を除去

---

## Phase 3: `executor.py` の分割 (462行 → ~200行 + サブモジュール)

**課題**: CommandExecutor が マウス/キーボード/タイミング/クリップボード/スクリーンショット/ウィンドウ管理 を全て含むモノリシック構造。

**変更内容**:
1. `src/core/commands/` ディレクトリを新規作成
2. `src/core/commands/__init__.py` を作成
3. `src/core/commands/window.py` を作成 — ウィンドウ管理コマンドを抽出:
   - `_cmd_window_focus` (L309-323)
   - `_cmd_window_move` (L325-348)
   - `_cmd_window_resize` (L350-373)
   - `_cmd_window_close` (L375-388)
4. `src/core/commands/clipboard.py` を作成 — クリップボード/スクリーンショットを抽出:
   - `_cmd_clipboard_set` (L275-282)
   - `_cmd_screenshot` (L284-307)
5. `executor.py` に残す — マウス/キーボード/タイミング/ディスパッチテーブル(コア機能)
6. ディスパッチテーブル `_DISPATCH` は `executor.py` に残し、抽出したコマンド関数を import して登録

**設計方針**: 抽出するコマンド関数はスタンドアロン関数 (`self` の代わりに必要な引数を受け取る) またはミックスインとして実装。ディスパッチテーブルとの互換性を維持するため、`CommandExecutor` のメソッドとして登録可能な形式にする。

---

## Phase 4: `condition.py` の分離 (236行 → ~60行 + 関数モジュール)

**課題**: 条件評価ロジックと個別関数の実装 (IMAGE_MATCH, PIXEL_COLOR, WINDOW_EXISTS, FILE_EXISTS) が混在。

**変更内容**:
1. `src/core/condition_funcs.py` を新規作成:
   - `_image_match()` (condition.py L110-172) を移動
   - `_pixel_color()` (condition.py L179-206) を移動
   - `_window_exists()` (condition.py L213-224) を移動
   - `_file_exists()` (condition.py L231-236) を移動
2. `condition.py` を更新:
   - `eval_condition()` のみ残す（~60行）
   - `from src.core.condition_funcs import ...` で各関数を参照

---

## Phase 5: `editor.py` の分割 (382行 → 3ファイル)

**課題**: `_LineNumberArea`, `CodeEditor`, `EditorTab`, `EditorArea` の4クラスが1ファイルに混在。

**変更内容**:
1. `src/gui/code_editor.py` を新規作成:
   - `_LineNumberArea` クラス (L22-33)
   - `CodeEditor` クラス (L36-167) — 行番号、現在行ハイライト、再生行ハイライト
2. `src/gui/editor_tab.py` を新規作成:
   - `EditorTab` クラス (L174-241) — 単一タブの管理
3. `src/gui/editor_area.py` を新規作成:
   - `EditorArea` クラス (L248-382) — タブ管理
4. `src/gui/editor.py` を互換性のために残す:
   - 各サブモジュールから re-export: `from src.gui.code_editor import CodeEditor` 等
   - 既存の import (`from src.gui.editor import EditorArea, EditorTab`) が壊れないようにする

---

## Phase 6: マジックナンバーの定数化 (`src/core/constants.py` 新規作成)

**課題**: チューニングパラメータが各ファイルにハードコードされている。

**変更内容**:
1. `src/core/constants.py` を新規作成し、以下の定数を集約:
   - `recorder.py` L87-91: `CLICK_MAX_MS`, `CLICK_MAX_PX`, `MOVE_MIN_PX`, `MOVE_MIN_MS`, `WAIT_MIN_MS`
   - `runner.py` L49-50: `MAX_ITERATIONS`, `MAX_CALL_DEPTH`
   - `executor.py` L142: `SLEEP_CHUNK_MS = 50` (チャンクサイズ)
2. 各ファイルを更新: `from src.core.constants import ...` に変更

---

## Phase 7: `main_window.py` の整理 (381行 → ~300行)

**課題**: UI構築・メニュー定義・シグナル接続・アクションハンドラが1クラスに集中。

**変更内容**:
1. スタイルシート `_STYLE` を `src/gui/styles.py` に抽出
2. メニュー構築 `_build_menu()` の内容を宣言的なデータ構造に変換し、ループで生成
   - メニュー項目のリスト化により行数を削減
3. `MainWindow` クラス自体は分割せず（Qt の QMainWindow は単一クラスが慣例）、代わりに内部メソッドのスリム化で対応

---

## Phase 8: テストの追加 (`tests/` ディレクトリ)

**課題**: テストが一切存在しない。リファクタリング後の動作保証が必要。

**変更内容**:
1. `pyproject.toml` に pytest を dev 依存に追加
2. `tests/` ディレクトリ構造:
   ```
   tests/
   ├── __init__.py
   ├── conftest.py            # 共有フィクスチャ
   ├── test_parser.py         # tokenize, strip_comment, expand_sugar, parse_lines
   ├── test_ast_builder.py    # build_ast, ParseError ケース
   ├── test_ast_nodes.py      # dataclass の基本テスト
   ├── test_expression.py     # eval_expr, _coerce, _sub_vars
   ├── test_variable_store.py # VariableStore の get/set/as_dict
   ├── test_condition.py      # eval_condition (TRUE/FALSE/FILE_EXISTS等)
   ├── test_keys.py           # Phase 1 で作成した keys.py のマッピング検証
   └── test_constants.py      # Phase 6 で作成した constants.py の値検証
   ```
3. テスト方針:
   - pynput/PySide6/win32 に依存しないユニットテストを中心とする
   - 外部依存はモック (`unittest.mock`) で置き換え
   - parser と ast_builder は純粋関数のためモック不要で網羅的にテスト可能

---

## 実行順序と依存関係

```
Phase 1 (keys.py)  ─────────┐
Phase 2 (optional_deps.py) ─┤
Phase 6 (constants.py) ─────┤
                             ├→ Phase 3 (executor分割) ─→ Phase 4 (condition分離)
Phase 5 (editor分割) ───────┤
Phase 7 (main_window整理) ──┘
                             └→ Phase 8 (テスト追加) ← 全Phase完了後
```

Phase 1, 2, 5, 6, 7 は相互に独立して並行実施可能。
Phase 3 は Phase 1, 2, 6 に依存。
Phase 4 は Phase 2 に依存。
Phase 8 は全Phase完了後に実施（リファクタリング後のコードに対してテストを書く）。

---

## リスク軽減策
- 各Phase完了時にコミット（ロールバック可能）
- re-export パターンで既存 import パスの互換性を維持
- 動作変更なし — 構造リファクタリングのみ
