"""Centralised tunables and magic numbers.

All numeric constants that control runtime behaviour are collected here
so they are easy to find, document, and adjust.
"""

# ---------------------------------------------------------------------------
# Recorder  (src/core/recorder.py)
# ---------------------------------------------------------------------------
CLICK_MAX_MS  = 400    # press→release within this → simple CLICK (not DOWN/UP)
CLICK_MAX_PX  = 5      # pixel drift within this    → simple CLICK
MOVE_MIN_PX   = 20     # minimum Euclidean distance  to emit MOUSE_POS
MOVE_MIN_MS   = 100    # minimum ms between MOUSE_POS events
WAIT_MIN_MS   = 10     # WAITs shorter than this are suppressed

# ---------------------------------------------------------------------------
# Runner  (src/core/runner.py)
# ---------------------------------------------------------------------------
MAX_ITERATIONS = 100_000   # hard limit for LOOP / WHILE / REPEAT
MAX_CALL_DEPTH = 16        # maximum CALL nesting depth

# ---------------------------------------------------------------------------
# Executor  (src/core/executor.py)
# ---------------------------------------------------------------------------
SLEEP_CHUNK_S = 0.05   # seconds between _stop_event polls during sleep
