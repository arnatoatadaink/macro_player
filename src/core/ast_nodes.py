"""AST node dataclasses for the macro language.

Each node type represents one syntactic construct.  The AST is built by
ast_builder.py and executed by runner.py.

Leaf nodes
----------
CmdNode    — a single executable command (MOUSE_POS, KEY, WAIT, …)
CallNode   — CALL "filename.macro"
AssignNode — #var = expression  /  #var = FUNCTION args

Branch nodes
------------
IfNode        — IF / ELSEIF / ELSE / ENDIF
LoopNode      — LOOP N / ENDLOOP
WhileNode     — WHILE condition / ENDWHILE
RepeatNode    — REPEAT / UNTIL condition
TryCatchNode  — TRY / CATCH / ENDTRY
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass
class CmdNode:
    """A single, flat macro command."""
    tokens:   list[str]     # [COMMAND, arg1, arg2, …]
    line_num: int = 0       # 0-based source line for error messages


@dataclass
class CallNode:
    """CALL "other_macro.macro" — delegate to another file."""
    filename: str
    line_num: int = 0


@dataclass
class AssignNode:
    """$var = expression  or  #var = FUNCTION args

    var_name  : the target variable including the leading '#'
    rhs_tokens: everything after the '=' sign, as a token list
    line_num  : 0-based source line for error messages
    """
    var_name:   str
    rhs_tokens: list[str]
    line_num:   int = 0


@dataclass
class IfNode:
    """IF / ELSEIF … / ELSE / ENDIF block.

    branches : list of (condition_tokens, body_nodes) for IF and each ELSEIF.
    else_body: nodes inside ELSE (empty list if no ELSE).
    """
    branches:  list[tuple[list[str], list["Node"]]] = field(default_factory=list)
    else_body: list["Node"]                          = field(default_factory=list)


@dataclass
class LoopNode:
    """LOOP count_expr / ENDLOOP — fixed iteration count.

    count_expr is a string so Phase 5 can evaluate it as a variable/expression.
    """
    count_expr: str = "1"
    body:       list["Node"] = field(default_factory=list)


@dataclass
class WhileNode:
    """WHILE condition / ENDWHILE — pre-test conditional loop."""
    condition: list[str]     = field(default_factory=list)
    body:      list["Node"]  = field(default_factory=list)


@dataclass
class RepeatNode:
    """REPEAT / UNTIL condition — post-test conditional loop."""
    body:      list["Node"]  = field(default_factory=list)
    condition: list[str]     = field(default_factory=list)


@dataclass
class TryCatchNode:
    """TRY / CATCH / ENDTRY — error handling block.

    try_body  : nodes inside TRY (executed normally)
    catch_body: nodes inside CATCH (executed if try_body raises an error)
    """
    try_body:   list["Node"] = field(default_factory=list)
    catch_body: list["Node"] = field(default_factory=list)


# Convenience union type (for type hints only; use isinstance() at runtime)
Node = Union[CmdNode, CallNode, AssignNode, IfNode, LoopNode, WhileNode, RepeatNode, TryCatchNode]
