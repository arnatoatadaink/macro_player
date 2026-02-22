"""Tests for src.core.constants — verify documented values and types."""
from src.core import constants


class TestRecorderConstants:
    def test_click_max_ms(self):
        assert isinstance(constants.CLICK_MAX_MS, int)
        assert constants.CLICK_MAX_MS > 0

    def test_click_max_px(self):
        assert isinstance(constants.CLICK_MAX_PX, int)
        assert constants.CLICK_MAX_PX > 0

    def test_move_min_px(self):
        assert isinstance(constants.MOVE_MIN_PX, int)
        assert constants.MOVE_MIN_PX > 0

    def test_move_min_ms(self):
        assert isinstance(constants.MOVE_MIN_MS, int)
        assert constants.MOVE_MIN_MS > 0

    def test_wait_min_ms(self):
        assert isinstance(constants.WAIT_MIN_MS, int)
        assert constants.WAIT_MIN_MS > 0


class TestRunnerConstants:
    def test_max_iterations(self):
        assert isinstance(constants.MAX_ITERATIONS, int)
        assert constants.MAX_ITERATIONS >= 1000

    def test_max_call_depth(self):
        assert isinstance(constants.MAX_CALL_DEPTH, int)
        assert constants.MAX_CALL_DEPTH > 0


class TestExecutorConstants:
    def test_sleep_chunk(self):
        assert isinstance(constants.SLEEP_CHUNK_S, float)
        assert 0 < constants.SLEEP_CHUNK_S < 1.0
