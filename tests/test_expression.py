"""Tests for src.core.expression — eval_expr, _coerce, _sub_vars."""
import pytest

from src.core.expression import eval_expr, _coerce, _sub_vars
from src.core.variable_store import VariableStore


# ---------------------------------------------------------------------------
# _coerce
# ---------------------------------------------------------------------------

class TestCoerce:
    def test_int(self):
        assert _coerce("42") == 42
        assert isinstance(_coerce("42"), int)

    def test_float(self):
        assert _coerce("3.14") == pytest.approx(3.14)
        assert isinstance(_coerce("3.14"), float)

    def test_bool_true(self):
        assert _coerce("true") is True
        assert _coerce("True") is True

    def test_bool_false(self):
        assert _coerce("false") is False
        assert _coerce("False") is False

    def test_string(self):
        assert _coerce("hello") == "hello"

    def test_negative_int(self):
        assert _coerce("-5") == -5


# ---------------------------------------------------------------------------
# _sub_vars
# ---------------------------------------------------------------------------

class TestSubVars:
    def test_substitute(self):
        vs = VariableStore()
        vs.set("$x", 10)
        result = _sub_vars("$x + 1", vs)
        assert "10" in result

    def test_no_var(self):
        vs = VariableStore()
        result = _sub_vars("1 + 2", vs)
        assert result == "1 + 2"

    def test_string_var(self):
        vs = VariableStore()
        vs.set("$name", "hello")
        result = _sub_vars("$name", vs)
        assert "'hello'" in result

    def test_bool_var(self):
        vs = VariableStore()
        vs.set("$flag", True)
        result = _sub_vars("$flag", vs)
        assert "True" in result

    def test_default_var(self):
        vs = VariableStore()
        result = _sub_vars("$missing", vs)
        # Default is 0
        assert "0" in result


# ---------------------------------------------------------------------------
# eval_expr
# ---------------------------------------------------------------------------

class TestEvalExpr:
    def test_single_int(self):
        vs = VariableStore()
        assert eval_expr(["42"], vs) == 42

    def test_single_float(self):
        vs = VariableStore()
        assert eval_expr(["3.14"], vs) == pytest.approx(3.14)

    def test_single_bool(self):
        vs = VariableStore()
        assert eval_expr(["true"], vs) is True

    def test_single_string(self):
        vs = VariableStore()
        assert eval_expr(["hello"], vs) == "hello"

    def test_variable(self):
        vs = VariableStore()
        vs.set("$count", 5)
        assert eval_expr(["$count"], vs) == 5

    def test_arithmetic(self):
        vs = VariableStore()
        vs.set("$a", 10)
        vs.set("$b", 3)
        result = eval_expr(["$a", "+", "$b"], vs)
        assert result == 13

    def test_comparison(self):
        vs = VariableStore()
        vs.set("$x", 5)
        result = eval_expr(["$x", ">", "3"], vs)
        assert result is True

    def test_logical_and(self):
        vs = VariableStore()
        vs.set("$a", 1)
        vs.set("$b", 2)
        result = eval_expr(["$a", ">", "0", "AND", "$b", ">", "0"], vs)
        assert result is True

    def test_logical_or(self):
        vs = VariableStore()
        vs.set("$a", 0)
        result = eval_expr(["$a", ">", "0", "OR", "1", "==", "1"], vs)
        assert result is True

    def test_logical_not(self):
        vs = VariableStore()
        vs.set("$flag", False)
        result = eval_expr(["NOT", "$flag"], vs)
        assert result is True

    def test_empty_tokens(self):
        vs = VariableStore()
        assert eval_expr([], vs) == 0

    def test_invalid_expr_returns_zero(self):
        vs = VariableStore()
        logs = []
        result = eval_expr(["$x", "!!", "bogus"], vs, log=lambda l, m: logs.append(m))
        assert result == 0
        assert len(logs) > 0
