"""Tests for src.core.variable_store — VariableStore."""
from src.core.variable_store import VariableStore


class TestVariableStore:
    def test_set_and_get(self):
        vs = VariableStore()
        vs.set("$x", 42)
        assert vs.get("$x") == 42

    def test_get_default(self):
        vs = VariableStore()
        assert vs.get("$missing") == 0
        assert vs.get("$missing", "default") == "default"

    def test_overwrite(self):
        vs = VariableStore()
        vs.set("$x", 1)
        vs.set("$x", 2)
        assert vs.get("$x") == 2

    def test_as_dict(self):
        vs = VariableStore()
        vs.set("$a", 1)
        vs.set("$b", "hello")
        d = vs.as_dict()
        assert d == {"$a": 1, "$b": "hello"}
        # Returned dict should be a copy
        d["$c"] = 99
        assert vs.get("$c") == 0

    def test_different_types(self):
        vs = VariableStore()
        vs.set("$int", 10)
        vs.set("$float", 3.14)
        vs.set("$str", "hello")
        vs.set("$bool", True)
        assert isinstance(vs.get("$int"), int)
        assert isinstance(vs.get("$float"), float)
        assert isinstance(vs.get("$str"), str)
        assert isinstance(vs.get("$bool"), bool)

    def test_repr(self):
        vs = VariableStore()
        vs.set("$x", 1)
        assert "VariableStore" in repr(vs)
        assert "$x" in repr(vs)
