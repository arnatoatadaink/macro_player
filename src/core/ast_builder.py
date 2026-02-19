"""AST builder — converts a flat list of token-lines into an AST.

Entry point
-----------
    from src.core.ast_builder import build_ast, ParseError
    nodes = build_ast(token_lines)   # list[Node]

Nested structures are parsed recursively.  Unmatched block keywords
(ENDLOOP without LOOP, etc.) raise ParseError.

Phase 5 hooks
-------------
The count_expr field of LoopNode and condition fields of If/While/Repeat
are stored as raw token lists so Phase 5 can evaluate variables/expressions.
"""
from __future__ import annotations

from src.core.prefix import VARIABLE_PREFIX

from src.core.ast_nodes import (
    Node, CmdNode, CallNode, AssignNode,
    IfNode, LoopNode, WhileNode, RepeatNode, TryCatchNode,
)

# Commands that end a block — _Builder._parse_block() stops when one is seen.
_BLOCK_TERMINATORS = frozenset({
    "ENDLOOP", "ENDWHILE", "UNTIL",
    "ELSEIF", "ELSE", "ENDIF",
    "CATCH", "ENDTRY",
})


class ParseError(Exception):
    """Raised for mismatched block keywords or other syntax errors."""


class _Builder:
    def __init__(self, token_lines: list[list[str]]) -> None:
        self._lines = token_lines
        self._pos   = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _at_end(self) -> bool:
        return self._pos >= len(self._lines)

    def _peek(self) -> str:
        return self._lines[self._pos][0].upper() if not self._at_end else ""

    def _consume(self, expected: str) -> None:
        got = self._peek()
        if got != expected:
            raise ParseError(
                f"Expected {expected!r}, got {got!r} at source line {self._pos + 1}"
            )
        self._pos += 1

    # ------------------------------------------------------------------
    # Core parsing
    # ------------------------------------------------------------------

    def build(self) -> list[Node]:
        nodes = self._parse_block(stop=frozenset())
        if not self._at_end:
            # Something left over — likely an unmatched ENDLOOP etc.
            orphan = self._peek()
            raise ParseError(f"Unexpected {orphan!r} at source line {self._pos + 1}")
        return nodes

    def _parse_block(self, stop: frozenset[str]) -> list[Node]:
        """Parse nodes until we hit a stop keyword or end-of-input."""
        nodes: list[Node] = []
        while not self._at_end and self._peek() not in stop:
            node = self._dispatch()
            if node is not None:
                nodes.append(node)
        return nodes

    def _dispatch(self) -> Node | None:
        cmd = self._peek()
        if cmd == "LOOP":    return self._parse_loop()
        if cmd == "WHILE":   return self._parse_while()
        if cmd == "REPEAT":  return self._parse_repeat()
        if cmd == "IF":      return self._parse_if()
        if cmd == "TRY":     return self._parse_try()
        if cmd == "CALL":    return self._parse_call()
        if cmd in _BLOCK_TERMINATORS:
            # Reached inside _parse_block with wrong stop set → programming error
            raise ParseError(
                f"Unexpected block terminator {cmd!r} at source line {self._pos + 1}"
            )
        # Variable assignment:  #varname = rhs…
        tokens = self._lines[self._pos]
        if (tokens[0].startswith(VARIABLE_PREFIX) and len(tokens) >= 2 and tokens[1] == "="):
            return self._parse_assign()
        # Plain command
        lnum = self._pos
        self._pos += 1
        return CmdNode(tokens, lnum)

    def _parse_assign(self) -> AssignNode:
        tokens   = self._lines[self._pos]
        lnum     = self._pos
        var_name = tokens[0]          # e.g. "$count"
        rhs      = tokens[2:]         # everything after "="
        self._pos += 1
        return AssignNode(var_name=var_name, rhs_tokens=rhs, line_num=lnum)

    # ------------------------------------------------------------------
    # Block-structured commands
    # ------------------------------------------------------------------

    def _parse_loop(self) -> LoopNode:
        tokens = self._lines[self._pos]
        count  = tokens[1] if len(tokens) > 1 else "1"
        self._pos += 1                                      # consume LOOP
        body = self._parse_block(stop=frozenset({"ENDLOOP"}))
        if not self._at_end and self._peek() == "ENDLOOP":
            self._pos += 1                                  # consume ENDLOOP
        return LoopNode(count_expr=count, body=body)

    def _parse_while(self) -> WhileNode:
        tokens = self._lines[self._pos]
        cond   = tokens[1:]                                 # rest of line = condition
        self._pos += 1
        body = self._parse_block(stop=frozenset({"ENDWHILE"}))
        if not self._at_end and self._peek() == "ENDWHILE":
            self._pos += 1
        return WhileNode(condition=cond, body=body)

    def _parse_repeat(self) -> RepeatNode:
        self._pos += 1                                      # consume REPEAT
        body = self._parse_block(stop=frozenset({"UNTIL"}))
        cond: list[str] = []
        if not self._at_end and self._peek() == "UNTIL":
            cond = self._lines[self._pos][1:]
            self._pos += 1                                  # consume UNTIL
        return RepeatNode(body=body, condition=cond)

    def _parse_if(self) -> IfNode:
        branches: list[tuple[list[str], list[Node]]] = []

        # Initial IF branch
        tokens = self._lines[self._pos]
        cond   = tokens[1:]
        self._pos += 1
        body   = self._parse_block(stop=frozenset({"ELSEIF", "ELSE", "ENDIF"}))
        branches.append((cond, body))

        # Zero or more ELSEIF branches
        while not self._at_end and self._peek() == "ELSEIF":
            tokens = self._lines[self._pos]
            cond   = tokens[1:]
            self._pos += 1
            body   = self._parse_block(stop=frozenset({"ELSEIF", "ELSE", "ENDIF"}))
            branches.append((cond, body))

        # Optional ELSE branch
        else_body: list[Node] = []
        if not self._at_end and self._peek() == "ELSE":
            self._pos += 1                                  # consume ELSE
            else_body = self._parse_block(stop=frozenset({"ENDIF"}))

        # ENDIF
        if not self._at_end and self._peek() == "ENDIF":
            self._pos += 1

        return IfNode(branches=branches, else_body=else_body)

    def _parse_call(self) -> CallNode:
        tokens  = self._lines[self._pos]
        lnum    = self._pos
        filename = tokens[1].strip("\"'") if len(tokens) > 1 else ""
        self._pos += 1
        return CallNode(filename=filename, line_num=lnum)

    def _parse_try(self) -> TryCatchNode:
        self._pos += 1                                      # consume TRY
        try_body = self._parse_block(stop=frozenset({"CATCH", "ENDTRY"}))

        catch_body: list[Node] = []
        if not self._at_end and self._peek() == "CATCH":
            self._pos += 1                                  # consume CATCH
            catch_body = self._parse_block(stop=frozenset({"ENDTRY"}))

        if not self._at_end and self._peek() == "ENDTRY":
            self._pos += 1                                  # consume ENDTRY

        return TryCatchNode(try_body=try_body, catch_body=catch_body)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_ast(token_lines: list[list[str]]) -> list[Node]:
    """Convert flat token_lines into a list of AST nodes.

    Raises ParseError on mismatched block keywords.
    """
    return _Builder(token_lines).build()


def count_leaf_commands(nodes: list[Node]) -> int:
    """Recursively count CmdNode/AssignNode leaves (for progress estimation)."""
    total = 0
    for node in nodes:
        if isinstance(node, (CmdNode, AssignNode)):
            total += 1
        elif isinstance(node, (IfNode,)):
            for _, body in node.branches:
                total += count_leaf_commands(body)
            total += count_leaf_commands(node.else_body)
        elif isinstance(node, (LoopNode, WhileNode)):
            total += count_leaf_commands(node.body)
        elif isinstance(node, RepeatNode):
            total += count_leaf_commands(node.body)
        elif isinstance(node, TryCatchNode):
            total += count_leaf_commands(node.try_body)
            total += count_leaf_commands(node.catch_body)
        elif isinstance(node, CallNode):
            total += 1
    return total
