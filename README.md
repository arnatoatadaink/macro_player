# Macro Player

Windows 11 向けマクロレコーダー / プレイヤー。
マウス・キーボード操作を記録してファイルに保存し、テキスト形式のマクロスクリプトとして編集・再生できます。

---

## 目次

1. [起動方法](#起動方法)
2. [画面構成](#画面構成)
3. [基本操作](#基本操作)
4. [マクロファイルの書き方](#マクロファイルの書き方)
   - [コメント](#コメント)
   - [マウス操作コマンド](#マウス操作コマンド)
   - [キーボード操作コマンド](#キーボード操作コマンド)
   - [タイミング制御](#タイミング制御)
   - [制御フロー](#制御フロー)
   - [変数](#変数)
   - [組み込み関数](#組み込み関数)
   - [その他コマンド](#その他コマンド)
5. [エラーハンドリング (TRY/CATCH)](#エラーハンドリング-trycatch)
6. [ファイル分割と呼び出し (CALL)](#ファイル分割と呼び出し-call)
7. [シンタックスシュガー (コマンドエイリアス)](#シンタックスシュガー-コマンドエイリアス)
8. [グローバルホットキー](#グローバルホットキー)
9. [設定項目](#設定項目)
10. [フォルダ構成](#フォルダ構成)

---

## 起動方法

```
python main.py
```

または配布された `macro_player.exe` をダブルクリックしてください。

---

## 画面構成

```
┌──────────────────────────────────────────────────────────────┐
│  メニューバー  ファイル / マクロ / ツール / ヘルプ              │
├──────────────┬───────────────────────────────────────────────┤
│              │  タブエディタ                                   │
│  サイドバー  │  (マクロスクリプトを編集)                        │
│  ─────────   │                                               │
│  [⏺記録]    │                                               │
│  [⏹停止]    │                                               │
│  [▶再生]    │                                               │
│  [✕クリア]  │                                               │
│  [💾保存]   │                                               │
│  [📂読込]   │                                               │
│  ─────────   │                                               │
│  ファイルツリー│                                              │
│  macros/     │                                               │
│    foo.macro │                                               │
│    bar.macro │                                               │
├──────────────┴───────────────────────────────────────────────┤
│  ログパネル  [INFO] [SUCCESS] [WARNING] [ERROR]               │
├──────────────────────────────────────────────────────────────┤
│  ステータスバー   状態表示           カーソル位置 / 進捗        │
└──────────────────────────────────────────────────────────────┘
```

右側に **変数ウォッチパネル**（ドック）が表示されます。再生開始時に自動表示され、`$var` の値をリアルタイムで確認できます。

---

## 基本操作

### 記録

1. エディタで新しいタブ（または既存ファイル）を開く
2. サイドバーの **[⏺記録]** ボタン、またはホットキー `Ctrl+Shift+R` を押す
3. 記録したいマウス・キーボード操作を実行する
4. **[⏹停止]** ボタン、またはホットキー `Ctrl+Shift+X` を押して停止
5. 記録されたコマンドがエディタに追記されます

> ホットキーはアプリがバックグラウンドでも動作します（グローバルホットキー）。

### 再生

1. エディタに再生したいマクロを開く（またはそのまま記録内容を使う）
2. サイドバーの **[▶再生]** ボタン、またはホットキー `Ctrl+Shift+P` を押す
3. 現在再生中の行がエディタ上でハイライト表示されます
4. 再生中に **[⏹停止]** ボタンで中断できます

### ファイル操作

| 操作 | 方法 |
|---|---|
| 新規タブ | `Ctrl+N` / サイドバー [📂読込] |
| ファイルを開く | `Ctrl+O` / サイドバー [📂読込] / ファイルツリーをダブルクリック |
| 上書き保存 | `Ctrl+S` / サイドバー [💾保存] |
| 名前を付けて保存 | `Ctrl+Shift+S` |

---

## マクロファイルの書き方

マクロファイル（`.macro`）は 1 行 1 コマンドのテキストファイルです。
コマンド名は**大文字・小文字を区別しません**。引数はスペース区切り、空白を含む文字列は `"ダブルクォート"` で囲みます。

### コメント

`#` から行末までがコメントになります。

```
# これはコメントです
WAIT 500   # 行末コメントも有効
```

---

### マウス操作コマンド

#### 移動

```
MOUSE_POS x y
```
マウスカーソルを画面座標 (x, y) に移動します。

```
MOUSE_GET_POS $x $y
```
現在のマウスカーソル座標を変数 `$x`、`$y` に取得します。

#### クリック

```
MOUSE_LEFT_CLICK   [x y]
MOUSE_RIGHT_CLICK  [x y]
MOUSE_MIDDLE_CLICK [x y]
```
`x y` を指定した場合はその座標に移動してからクリックします。省略時は現在位置でクリックします。

#### 押下 / 解放

```
MOUSE_LEFT_DOWN    [x y]
MOUSE_LEFT_UP      [x y]
MOUSE_RIGHT_DOWN   [x y]
MOUSE_RIGHT_UP     [x y]
MOUSE_MIDDLE_DOWN  [x y]
MOUSE_MIDDLE_UP    [x y]
```

#### スクロール

```
WHEEL delta
WHEEL x y delta
```
`delta` に正の値で上スクロール、負の値で下スクロールします。

---

### キーボード操作コマンド

#### 1 キー押下

```
KEY キー名
```
指定したキーを押して離します。

```
KEY_DOWN キー名
KEY_UP   キー名
```

#### コンビネーションキー（同時押し）

```
KEYS ctrl+c
KEYS ctrl+shift+s
KEYS alt+F4
```

```
KEYS_DOWN ctrl+shift
KEYS_UP   ctrl+shift
```

#### テキスト入力

```
TYPE "Hello, World!"
TYPE 入力したいテキスト
```

#### 使用できるキー名

| キー名 | 説明 |
|---|---|
| `ctrl` `ctrl_l` `ctrl_r` | Ctrl キー |
| `shift` `shift_l` `shift_r` | Shift キー |
| `alt` `alt_l` `alt_r` | Alt キー |
| `win` / `super` | Windows キー |
| `enter` / `return` | Enter |
| `space` | スペース |
| `backspace` | BackSpace |
| `tab` | Tab |
| `esc` / `escape` | Escape |
| `delete` / `del` | Delete |
| `home` `end` | Home / End |
| `pageup` `pagedown` | Page Up / Down |
| `up` `down` `left` `right` | 矢印キー |
| `insert` | Insert |
| `capslock` | CapsLock |
| `f1` ～ `f12` | ファンクションキー |
| `a` ～ `z` `0` ～ `9` | 文字・数字キー |

---

### タイミング制御

```
WAIT ミリ秒
```

```
WAIT 1000      # 1 秒待機
WAIT 500       # 0.5 秒待機
WAIT $delay    # 変数で指定
```

---

### 制御フロー

#### IF / ELSEIF / ELSE / ENDIF

```
IF 条件
    # 条件が真のとき実行
ELSEIF 別の条件
    # 別条件が真のとき実行
ELSE
    # すべて偽のとき実行
ENDIF
```

**条件の書き方:**

```
IF TRUE
IF FALSE
IF $count > 5
IF $count == 0
IF $flag AND $x > 100
IF NOT $done
IF WINDOW_EXISTS "Notepad"
IF IMAGE_MATCH "button.png" threshold 0.9
IF PIXEL_COLOR 500 300 255 0 0 10
IF FILE_EXISTS "C:\data\log.txt"
```

#### LOOP / ENDLOOP（回数繰り返し）

```
LOOP 10
    MOUSE_LEFT_CLICK 100 200
    WAIT 100
ENDLOOP

LOOP $count        # 変数で回数指定
    WAIT 50
ENDLOOP
```

#### WHILE / ENDWHILE（前判定ループ）

```
WHILE $i < 10
    $i = $i + 1
    WAIT 100
ENDWHILE

WHILE WINDOW_EXISTS "Notepad"
    WAIT 500
ENDWHILE
```

#### REPEAT / UNTIL（後判定ループ）

```
REPEAT
    MOUSE_LEFT_CLICK 100 200
    WAIT 200
UNTIL IMAGE_MATCH "ok_button.png"
```

#### BREAK / CONTINUE

ループの中でのみ使用できます。

```
LOOP 100
    IF $done
        BREAK       # ループを抜ける
    ENDIF
    IF $skip
        CONTINUE    # 次のイテレーションへ
    ENDIF
    WAIT 10
ENDLOOP
```

#### RETURN / EXIT

```
RETURN    # 現在のマクロファイルから呼び出し元へ戻る (CALL 先で使用)
EXIT      # マクロ全体を終了する
```

---

### 変数

変数名は `$` で始まります。英数字とアンダースコアが使えます（例: `$count`、`$my_value`）。

#### 代入

```
$count = 0
$name  = "hello"
$x     = $y + 10
$total = $a * $b - 1
```

#### 数式・比較

代入の右辺、および条件式では Python の演算子が使えます。

| 演算子 | 例 |
|---|---|
| 加減乗除 | `$a + $b` / `$a - 1` / `$x * 2` / `$n / 4` |
| 余り | `$n % 3` |
| 比較 | `$x == 5` / `$x != 0` / `$x >= 10` |
| 論理 | `$a > 0 AND $b < 10` / `NOT $flag` / `$x OR $y` |

#### 関数を使った代入

```
$t     = GET_TIME              # Unix タイムスタンプ (float)
$r     = RANDOM 1 100          # 1 〜 100 のランダム整数
$clip  = CLIPBOARD_GET         # クリップボードの文字列
$color = GET_PIXEL_COLOR 500 300   # "R G B" 文字列
$found = IMAGE_MATCH "logo.png" threshold 0.85
$win   = WINDOW_EXISTS "Notepad"
$exists = FILE_EXISTS "C:\data.txt"
```

---

### 組み込み関数

| 関数 | 書き方 | 戻り値 |
|---|---|---|
| `GET_TIME` | `$t = GET_TIME` | Unix タイムスタンプ (float) |
| `RANDOM` | `$r = RANDOM 最小 最大` | 指定範囲の整数 |
| `CLIPBOARD_GET` | `$s = CLIPBOARD_GET` | クリップボードの文字列 |
| `GET_PIXEL_COLOR` | `$c = GET_PIXEL_COLOR x y` | `"R G B"` 形式の文字列 |
| `IMAGE_MATCH` | `$b = IMAGE_MATCH ファイル名 [threshold 値] [region x y w h]` | `True` / `False` |
| `PIXEL_COLOR` | `$b = PIXEL_COLOR x y R G B [tolerance]` | `True` / `False` |
| `WINDOW_EXISTS` | `$b = WINDOW_EXISTS "タイトル"` | `True` / `False` |
| `FILE_EXISTS` | `$b = FILE_EXISTS "パス"` | `True` / `False` |

> `IMAGE_MATCH` には OpenCV と mss が必要です。`WINDOW_EXISTS` には pywin32 が必要です。

---

### その他コマンド

#### 出力

```
PRINT "メッセージ"
PRINT $count
```
ログパネルに出力します。

#### クリップボード

```
CLIPBOARD_SET "コピーするテキスト"
CLIPBOARD_SET $var
```

#### スクリーンショット

```
SCREENSHOT                         # screenshots/YYYYMMDD_HHMMSS.png に保存
SCREENSHOT "C:\images\snap.png"    # パス指定
```

#### ウィンドウ操作

```
WINDOW_FOCUS  "Notepad"            # ウィンドウをフォアグラウンドにする
WINDOW_MOVE   "Notepad" 100 100    # ウィンドウを移動
WINDOW_RESIZE "Notepad" 800 600    # ウィンドウをリサイズ
WINDOW_CLOSE  "Notepad"            # ウィンドウを閉じる (WM_CLOSE 送信)
```

---

## エラーハンドリング (TRY/CATCH)

コマンド実行中にエラーが発生した場合、`CATCH` ブロックで処理を継続できます。

```
TRY
    WINDOW_FOCUS "存在しないウィンドウ"
    TYPE "Hello"
CATCH
    PRINT "ウィンドウが見つかりませんでした"
ENDTRY
```

`CATCH` ブロックを省略した場合、エラーはログパネルに出力されて次の行に進みます。

```
TRY
    SCREENSHOT "output.png"
ENDTRY
```

---

## ファイル分割と呼び出し (CALL)

長いマクロは複数ファイルに分割して管理できます。

```
# メインマクロ (main.macro)
CALL "login.macro"
CALL "process.macro"
CALL "logout.macro"
```

- 呼び出し先のファイルは `macros/` フォルダからの相対パスで指定します
- 変数スコープは呼び出し元と共有されます
- 呼び出し先で `RETURN` を実行すると呼び出し元に戻ります
- 最大再帰深度は 16 です

---

## シンタックスシュガー (コマンドエイリアス)

`settings.ini` の `[COMMANDS]` セクションにエイリアスを定義できます。

```ini
[COMMANDS]
POS          = MOUSE_POS
MOUSE_MOVE   = MOUSE_POS
LEFT_BUTTON  = MOUSE_LEFT_CLICK
RIGHT_BUTTON = MOUSE_RIGHT_CLICK
```

定義したエイリアスはコマンドとして使用でき、構文ハイライトも適用されます。

```
POS 500 300          # MOUSE_POS 500 300 と同じ
LEFT_BUTTON 500 300  # MOUSE_LEFT_CLICK 500 300 と同じ
```

---

## グローバルホットキー

アプリケーションがバックグラウンドにある状態でも以下のホットキーが機能します。

| 操作 | デフォルト |
|---|---|
| 記録開始 | `Ctrl+Shift+R` |
| 記録停止 | `Ctrl+Shift+X` |
| 再生 | `Ctrl+Shift+P` |

ホットキーは **ツール → 設定 → ホットキー** タブで変更できます。変更後は設定ダイアログの OK ボタンを押すと即座に反映されます。

---

## 設定項目

**ツール → 設定** から変更できます。`settings.ini` を直接編集することもできます。

### 入力タブ

| 項目 | デフォルト | 説明 |
|---|---|---|
| マウスクリック待機時間 | 50 ms | クリック押下と解放の間の待機時間 |
| キー押下待機時間 | 30 ms | キー押下と解放の間の待機時間 |
| 再生速度 | 1.0 | 1.0 が等倍速。2.0 で 2 倍速、0.5 で半速 |

### ホットキータブ

グローバルホットキーのキー組み合わせを変更できます。

---

## マクロの実例

### 例 1 — クリック連打

```
LOOP 10
    MOUSE_LEFT_CLICK 500 400
    WAIT 100
ENDLOOP
```

### 例 2 — テキストのコピー & 加工

```
KEYS ctrl+a
KEYS ctrl+c
$text = CLIPBOARD_GET
PRINT $text
CLIPBOARD_SET "prefix_" + $text
KEYS ctrl+v
```

### 例 3 — 画像が見つかるまで待機してクリック

```
$found = FALSE
REPEAT
    $found = IMAGE_MATCH "ok_button.png" threshold 0.85
    WAIT 500
UNTIL $found

MOUSE_LEFT_CLICK 500 400
```

### 例 4 — ウィンドウが存在する間ループ

```
WHILE WINDOW_EXISTS "ダウンロード中"
    WAIT 1000
ENDWHILE
PRINT "ダウンロード完了"
```

### 例 5 — カウンタ付きループ

```
$i = 1
WHILE $i <= 5
    PRINT $i
    $i = $i + 1
    WAIT 200
ENDWHILE
```

### 例 6 — マウス座標の記録と再利用

```
# 現在のマウス位置を保存
MOUSE_GET_POS $saved_x $saved_y

# 別の操作
MOUSE_LEFT_CLICK 100 200
TYPE "Hello"

# 元の位置に戻る
MOUSE_POS $saved_x $saved_y
```

### 例 7 — エラー時のフォールバック処理

```
TRY
    WINDOW_FOCUS "MyApp"
    WAIT 500
    TYPE "Hello"
CATCH
    PRINT "MyApp が見つかりません。起動します..."
    # アプリを起動する処理など
ENDTRY
```

---

## フォルダ構成

```
macro_player/
├── macro_player.exe      (または main.py)
├── settings.ini          設定ファイル
├── macros/               マクロファイルの保存先
│   └── *.macro
├── templates/            IMAGE_MATCH 用テンプレート画像
│   └── *.png
└── screenshots/          SCREENSHOT コマンドの保存先 (自動作成)
```

---

## 動作環境

| 項目 | 要件 |
|---|---|
| OS | Windows 10 / 11 (64bit) |
| Python | 3.11 以上 (ソースから実行する場合) |
| 主要ライブラリ | PySide6, pynput, mss, opencv-python, pywin32, pyperclip |
