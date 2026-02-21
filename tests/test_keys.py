"""Tests for src.core.keys — shared key/button mappings."""
import pytest

pynput = pytest.importorskip("pynput", reason="pynput requires display server", exc_type=ImportError)
from pynput import keyboard, mouse

from src.core.keys import (
    SPECIAL_KEYS, BUTTON_MAP, MODIFIERS, MOD_NAMES,
    KEY_NAMES, BUTTON_CMDS,
    parse_key, parse_combo, key_name,
)


class TestSpecialKeys:
    def test_ctrl(self):
        assert SPECIAL_KEYS["CTRL"] == keyboard.Key.ctrl

    def test_enter(self):
        assert SPECIAL_KEYS["ENTER"] == keyboard.Key.enter
        assert SPECIAL_KEYS["RETURN"] == keyboard.Key.enter

    def test_function_keys(self):
        for n in range(1, 13):
            assert f"F{n}" in SPECIAL_KEYS
            assert SPECIAL_KEYS[f"F{n}"] == getattr(keyboard.Key, f"f{n}")

    def test_esc_aliases(self):
        assert SPECIAL_KEYS["ESC"] == SPECIAL_KEYS["ESCAPE"]


class TestButtonMap:
    def test_left(self):
        assert BUTTON_MAP["LEFT"] == mouse.Button.left

    def test_right(self):
        assert BUTTON_MAP["RIGHT"] == mouse.Button.right

    def test_middle(self):
        assert BUTTON_MAP["MIDDLE"] == mouse.Button.middle


class TestModifiers:
    def test_ctrl_in_modifiers(self):
        assert keyboard.Key.ctrl in MODIFIERS
        assert keyboard.Key.ctrl_l in MODIFIERS

    def test_shift_in_modifiers(self):
        assert keyboard.Key.shift in MODIFIERS

    def test_alt_in_modifiers(self):
        assert keyboard.Key.alt in MODIFIERS


class TestModNames:
    def test_ctrl_name(self):
        assert MOD_NAMES[keyboard.Key.ctrl] == "ctrl"
        assert MOD_NAMES[keyboard.Key.ctrl_l] == "ctrl"

    def test_shift_name(self):
        assert MOD_NAMES[keyboard.Key.shift] == "shift"


class TestButtonCmds:
    def test_left_button(self):
        click, down, up = BUTTON_CMDS[mouse.Button.left]
        assert click == "MOUSE_LEFT_CLICK"
        assert down == "MOUSE_LEFT_DOWN"
        assert up == "MOUSE_LEFT_UP"


class TestParseKey:
    def test_special_key(self):
        assert parse_key("enter") == keyboard.Key.enter

    def test_single_char(self):
        k = parse_key("a")
        assert k == keyboard.KeyCode.from_char("a")

    def test_unknown(self):
        assert parse_key("NONEXISTENT_KEY_NAME_XYZ") is None


class TestParseCombo:
    def test_combo(self):
        keys = parse_combo("ctrl+shift+a")
        assert len(keys) == 3
        assert keyboard.Key.ctrl in keys
        assert keyboard.Key.shift in keys


class TestKeyName:
    def test_known_key(self):
        assert key_name(keyboard.Key.enter) == "enter"
        assert key_name(keyboard.Key.space) == "space"

    def test_char_key(self):
        k = keyboard.KeyCode.from_char("x")
        assert key_name(k) == "x"
