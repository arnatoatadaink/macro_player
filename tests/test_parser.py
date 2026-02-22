"""Tests for src.core.parser — tokenizer, comment stripping, sugar expansion."""
import pytest

pynput = pytest.importorskip("pynput", reason="pynput (parser→executor) requires display server", exc_type=ImportError)
from src.core.parser import strip_comment, tokenize, expand_sugar, parse_lines


# ---------------------------------------------------------------------------
# strip_comment
# ---------------------------------------------------------------------------

class TestStripComment:
    def test_no_comment(self):
        assert strip_comment("MOUSE_POS 100 200") == "MOUSE_POS 100 200"

    def test_trailing_comment(self):
        assert strip_comment("WAIT 500 # pause").rstrip() == "WAIT 500 "

    def test_hash_inside_string(self):
        assert strip_comment('TYPE "hello # world"') == 'TYPE "hello # world"'

    def test_comment_only(self):
        assert strip_comment("# full line comment") == ""

    def test_empty(self):
        assert strip_comment("") == ""


# ---------------------------------------------------------------------------
# tokenize
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_simple(self):
        assert tokenize("MOUSE_POS 100 200") == ["MOUSE_POS", "100", "200"]

    def test_quoted_string(self):
        assert tokenize('TYPE "hello world"') == ["TYPE", "hello world"]

    def test_blank_line(self):
        assert tokenize("") == []
        assert tokenize("   ") == []

    def test_comment_line(self):
        assert tokenize("# this is a comment") == []

    def test_trailing_comment(self):
        tokens = tokenize("WAIT 300 # pause")
        assert tokens == ["WAIT", "300"]

    def test_malformed_quotes(self):
        # Falls back to simple split
        tokens = tokenize('TYPE "unclosed')
        assert len(tokens) > 0


# ---------------------------------------------------------------------------
# expand_sugar
# ---------------------------------------------------------------------------

class TestExpandSugar:
    def test_alias_replaced(self):
        sugar = {"POS": "MOUSE_POS"}
        assert expand_sugar(["POS", "100", "200"], sugar) == ["MOUSE_POS", "100", "200"]

    def test_alias_case_insensitive(self):
        sugar = {"POS": "MOUSE_POS"}
        assert expand_sugar(["pos", "100", "200"], sugar) == ["MOUSE_POS", "100", "200"]

    def test_no_alias(self):
        sugar = {"POS": "MOUSE_POS"}
        assert expand_sugar(["WAIT", "500"], sugar) == ["WAIT", "500"]

    def test_empty_tokens(self):
        sugar = {"POS": "MOUSE_POS"}
        assert expand_sugar([], sugar) == []


# ---------------------------------------------------------------------------
# parse_lines
# ---------------------------------------------------------------------------

class TestParseLines:
    def test_multi_line(self):
        text = "MOUSE_POS 100 200\nWAIT 500\n# comment\nKEY enter"
        result = parse_lines(text, {})
        assert len(result) == 3
        assert result[0][0] == "MOUSE_POS"
        assert result[1] == ["WAIT", "500"]
        assert result[2] == ["KEY", "enter"]

    def test_blank_lines_skipped(self):
        text = "\n\n   \nMOUSE_POS 0 0\n\n"
        result = parse_lines(text, {})
        assert len(result) == 1

    def test_sugar_applied(self):
        text = "POS 100 200"
        result = parse_lines(text, {"POS": "MOUSE_POS"})
        assert result[0][0] == "MOUSE_POS"
