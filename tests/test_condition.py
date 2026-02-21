"""Tests for src.core.condition — eval_condition (logic-level, no hardware)."""
import pytest
from pathlib import Path
from unittest.mock import patch

from src.core.condition import eval_condition
from src.core.variable_store import VariableStore


class TestLiterals:
    def test_true(self):
        assert eval_condition(["TRUE"], Path(".")) is True

    def test_false(self):
        assert eval_condition(["FALSE"], Path(".")) is False

    def test_one(self):
        assert eval_condition(["1"], Path(".")) is True

    def test_zero(self):
        assert eval_condition(["0"], Path(".")) is False

    def test_empty(self):
        assert eval_condition([], Path(".")) is False


class TestFileExists:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert eval_condition(["FILE_EXISTS", str(f)], Path(".")) is True

    def test_missing_file(self, tmp_path):
        assert eval_condition(["FILE_EXISTS", str(tmp_path / "nope.txt")], Path(".")) is False

    def test_no_args(self):
        logs = []
        result = eval_condition(["FILE_EXISTS"], Path("."), log=lambda l, m: logs.append(m))
        assert result is False
        assert any("path required" in m for m in logs)


class TestExpressionFallback:
    def test_variable_comparison(self):
        vs = VariableStore()
        vs.set("$x", 5)
        assert eval_condition(["$x", ">", "3"], Path("."), variables=vs) is True
        assert eval_condition(["$x", "<", "3"], Path("."), variables=vs) is False

    def test_invalid_expression(self):
        logs = []
        result = eval_condition(
            ["bogus", "!!"], Path("."),
            log=lambda l, m: logs.append(m),
        )
        # Should return False gracefully (possibly with a warning)
        assert result is False or result == 0


class TestWindowExistsMocked:
    @patch("src.core.condition_funcs.HAS_WIN32", False)
    def test_not_available(self):
        logs = []
        result = eval_condition(
            ["WINDOW_EXISTS", "Test"], Path("."),
            log=lambda l, m: logs.append(m),
        )
        assert result is False
        assert any("pywin32" in m for m in logs)


class TestImageMatchMocked:
    @patch("src.core.condition_funcs.HAS_CV", False)
    def test_not_available(self):
        logs = []
        result = eval_condition(
            ["IMAGE_MATCH", "test.png"], Path("."),
            log=lambda l, m: logs.append(m),
        )
        assert result is False

    @patch("src.core.condition_funcs.HAS_CV", True)
    @patch("src.core.condition_funcs.HAS_MSS", True)
    def test_missing_template(self):
        logs = []
        result = eval_condition(
            ["IMAGE_MATCH", "nonexistent.png"], Path("/tmp/empty_templates"),
            log=lambda l, m: logs.append(m),
        )
        assert result is False
        assert any("not found" in m for m in logs)
