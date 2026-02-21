"""Tests for src.core.ast_builder — AST construction from token lists."""
import pytest

from src.core.ast_builder import build_ast, count_leaf_commands, ParseError
from src.core.ast_nodes import (
    CmdNode, CallNode, AssignNode,
    IfNode, LoopNode, WhileNode, RepeatNode, TryCatchNode,
)


# ---------------------------------------------------------------------------
# Flat commands
# ---------------------------------------------------------------------------

class TestFlatCommands:
    def test_single_command(self):
        nodes = build_ast([["WAIT", "500"]])
        assert len(nodes) == 1
        assert isinstance(nodes[0], CmdNode)
        assert nodes[0].tokens == ["WAIT", "500"]

    def test_multiple_commands(self):
        lines = [["MOUSE_POS", "100", "200"], ["WAIT", "50"], ["KEY", "enter"]]
        nodes = build_ast(lines)
        assert len(nodes) == 3
        assert all(isinstance(n, CmdNode) for n in nodes)

    def test_empty_input(self):
        assert build_ast([]) == []


# ---------------------------------------------------------------------------
# Variable assignment
# ---------------------------------------------------------------------------

class TestAssignNode:
    def test_simple_assignment(self):
        nodes = build_ast([["$count", "=", "10"]])
        assert len(nodes) == 1
        assert isinstance(nodes[0], AssignNode)
        assert nodes[0].var_name == "$count"
        assert nodes[0].rhs_tokens == ["10"]

    def test_expression_assignment(self):
        nodes = build_ast([["$x", "=", "$x", "+", "1"]])
        assert isinstance(nodes[0], AssignNode)
        assert nodes[0].rhs_tokens == ["$x", "+", "1"]


# ---------------------------------------------------------------------------
# CALL
# ---------------------------------------------------------------------------

class TestCallNode:
    def test_call(self):
        nodes = build_ast([["CALL", "sub.macro"]])
        assert isinstance(nodes[0], CallNode)
        assert nodes[0].filename == "sub.macro"


# ---------------------------------------------------------------------------
# LOOP / ENDLOOP
# ---------------------------------------------------------------------------

class TestLoopNode:
    def test_simple_loop(self):
        lines = [["LOOP", "3"], ["WAIT", "100"], ["ENDLOOP"]]
        nodes = build_ast(lines)
        assert len(nodes) == 1
        loop = nodes[0]
        assert isinstance(loop, LoopNode)
        assert loop.count_expr == "3"
        assert len(loop.body) == 1
        assert isinstance(loop.body[0], CmdNode)

    def test_nested_loop(self):
        lines = [
            ["LOOP", "2"],
            ["LOOP", "3"],
            ["KEY", "a"],
            ["ENDLOOP"],
            ["ENDLOOP"],
        ]
        nodes = build_ast(lines)
        assert len(nodes) == 1
        outer = nodes[0]
        assert isinstance(outer, LoopNode)
        assert len(outer.body) == 1
        inner = outer.body[0]
        assert isinstance(inner, LoopNode)
        assert inner.count_expr == "3"

    def test_default_count(self):
        lines = [["LOOP"], ["WAIT", "10"], ["ENDLOOP"]]
        nodes = build_ast(lines)
        assert nodes[0].count_expr == "1"


# ---------------------------------------------------------------------------
# WHILE / ENDWHILE
# ---------------------------------------------------------------------------

class TestWhileNode:
    def test_while(self):
        lines = [["WHILE", "TRUE"], ["KEY", "a"], ["ENDWHILE"]]
        nodes = build_ast(lines)
        assert isinstance(nodes[0], WhileNode)
        assert nodes[0].condition == ["TRUE"]
        assert len(nodes[0].body) == 1


# ---------------------------------------------------------------------------
# REPEAT / UNTIL
# ---------------------------------------------------------------------------

class TestRepeatNode:
    def test_repeat(self):
        lines = [["REPEAT"], ["KEY", "b"], ["UNTIL", "FALSE"]]
        nodes = build_ast(lines)
        assert isinstance(nodes[0], RepeatNode)
        assert nodes[0].condition == ["FALSE"]
        assert len(nodes[0].body) == 1


# ---------------------------------------------------------------------------
# IF / ELSEIF / ELSE / ENDIF
# ---------------------------------------------------------------------------

class TestIfNode:
    def test_simple_if(self):
        lines = [["IF", "TRUE"], ["KEY", "a"], ["ENDIF"]]
        nodes = build_ast(lines)
        assert isinstance(nodes[0], IfNode)
        assert len(nodes[0].branches) == 1
        cond, body = nodes[0].branches[0]
        assert cond == ["TRUE"]
        assert len(body) == 1

    def test_if_else(self):
        lines = [
            ["IF", "TRUE"], ["KEY", "a"],
            ["ELSE"], ["KEY", "b"],
            ["ENDIF"],
        ]
        nodes = build_ast(lines)
        ifn = nodes[0]
        assert isinstance(ifn, IfNode)
        assert len(ifn.branches) == 1
        assert len(ifn.else_body) == 1

    def test_if_elseif_else(self):
        lines = [
            ["IF", "$x", "==", "1"], ["KEY", "a"],
            ["ELSEIF", "$x", "==", "2"], ["KEY", "b"],
            ["ELSE"], ["KEY", "c"],
            ["ENDIF"],
        ]
        nodes = build_ast(lines)
        ifn = nodes[0]
        assert len(ifn.branches) == 2
        assert len(ifn.else_body) == 1


# ---------------------------------------------------------------------------
# TRY / CATCH / ENDTRY
# ---------------------------------------------------------------------------

class TestTryCatchNode:
    def test_try_catch(self):
        lines = [
            ["TRY"], ["KEY", "a"],
            ["CATCH"], ["KEY", "b"],
            ["ENDTRY"],
        ]
        nodes = build_ast(lines)
        assert isinstance(nodes[0], TryCatchNode)
        assert len(nodes[0].try_body) == 1
        assert len(nodes[0].catch_body) == 1

    def test_try_without_catch(self):
        lines = [["TRY"], ["KEY", "a"], ["ENDTRY"]]
        nodes = build_ast(lines)
        tc = nodes[0]
        assert isinstance(tc, TryCatchNode)
        assert len(tc.try_body) == 1
        assert tc.catch_body == []


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestParseError:
    def test_orphan_endloop(self):
        with pytest.raises(ParseError):
            build_ast([["ENDLOOP"]])

    def test_orphan_endif(self):
        with pytest.raises(ParseError):
            build_ast([["ENDIF"]])


# ---------------------------------------------------------------------------
# count_leaf_commands
# ---------------------------------------------------------------------------

class TestCountLeafCommands:
    def test_flat(self):
        nodes = build_ast([["KEY", "a"], ["WAIT", "100"]])
        assert count_leaf_commands(nodes) == 2

    def test_nested(self):
        lines = [
            ["LOOP", "2"],
            ["KEY", "a"],
            ["IF", "TRUE"], ["KEY", "b"], ["ENDIF"],
            ["ENDLOOP"],
        ]
        nodes = build_ast(lines)
        # LOOP body: 1 CmdNode + 1 IfNode(1 branch with 1 CmdNode) = 2
        assert count_leaf_commands(nodes) == 2

    def test_call_counted(self):
        nodes = build_ast([["CALL", "sub.macro"]])
        assert count_leaf_commands(nodes) == 1
