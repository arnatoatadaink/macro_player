"""AST runner — walks an AST and executes each node.

Control-flow exceptions (internal use only)
--------------------------------------------
_Break     — raised by BREAK, caught by LoopNode/WhileNode/RepeatNode handler
_Continue  — raised by CONTINUE, caught by loop handlers
_Return    — raised by RETURN, caught by CallNode handler
_Exit      — raised by EXIT or stop_event; propagates to top-level caller

Usage
-----
    runner = ASTRunner(executor, cond_fn, macros_dir, settings, log_fn)
    try:
        runner.run(ast_nodes)
    except _Exit:
        pass  # interrupted
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.core.ast_nodes import (
    Node, CmdNode, CallNode, AssignNode,
    IfNode, LoopNode, WhileNode, RepeatNode, TryCatchNode,
)
from src.core.executor import CommandExecutor
from src.core.variable_store import VariableStore
from src.core.prefix import VARIABLE_PREFIX
from src.core.constants import (
    MAX_ITERATIONS as _MAX_ITERATIONS,
    MAX_CALL_DEPTH as _MAX_CALL_DEPTH,
)

LogFn    = Callable[[str, str], None]       # (level, message)
CondFn   = Callable[[list[str]], bool]      # (condition_tokens) → bool


# ---------------------------------------------------------------------------
# Flow-control exceptions
# ---------------------------------------------------------------------------

class _Break(Exception):    pass
class _Continue(Exception): pass
class _Return(Exception):   pass
class _Exit(Exception):     pass


class ASTRunner:
    """Recursively executes an AST produced by ast_builder.build_ast()."""

    def __init__(
        self,
        executor:        CommandExecutor,
        cond_fn:         CondFn,
        macros_dir:      Path,
        settings,
        log_fn:          LogFn | None = None,
        depth:           int          = 0,
        on_cmd:          Callable[[int], None] | None = None,
        variables:       VariableStore | None = None,
        templates_dir:   Path | None = None,
        vars_changed_fn: Callable[[dict], None] | None = None,
    ) -> None:
        self._exec           = executor
        self._cond_fn        = cond_fn
        self._macros_dir     = macros_dir
        self._templates_dir  = templates_dir or macros_dir
        self._settings       = settings
        self._log            = log_fn or (lambda lvl, msg: None)
        self._depth          = depth
        self._on_cmd         = on_cmd or (lambda ln: None)  # progress tick
        self._vars           = variables if variables is not None else VariableStore()
        self._vars_changed_fn = vars_changed_fn             # notify UI of var updates

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, nodes: list[Node]) -> None:
        """Execute a list of AST nodes in order."""
        for node in nodes:
            if self._exec.stop_event.is_set():
                raise _Exit()
            self._run_node(node)

    # ------------------------------------------------------------------
    # Node dispatch
    # ------------------------------------------------------------------

    def _run_node(self, node: Node) -> None:
        if   isinstance(node, CmdNode):        self._run_cmd(node)
        elif isinstance(node, AssignNode):     self._run_assign(node)
        elif isinstance(node, IfNode):         self._run_if(node)
        elif isinstance(node, LoopNode):       self._run_loop(node)
        elif isinstance(node, WhileNode):      self._run_while(node)
        elif isinstance(node, RepeatNode):     self._run_repeat(node)
        elif isinstance(node, TryCatchNode):   self._run_try(node)
        elif isinstance(node, CallNode):       self._run_call(node)

    # ------------------------------------------------------------------
    # CmdNode
    # ------------------------------------------------------------------

    def _run_cmd(self, node: CmdNode) -> None:
        cmd  = node.tokens[0].upper()
        args = node.tokens[1:]

        # Resolve variable references in args before executing
        resolved = self._resolve_args(args)

        # Flow-control keywords → raise, not executor
        if cmd == "BREAK":    raise _Break()
        if cmd == "CONTINUE": raise _Continue()
        if cmd == "RETURN":   raise _Return()
        if cmd == "EXIT":     raise _Exit()

        # MOUSE_GET_POS $x $y — capture mouse position directly into variables
        if cmd == "MOUSE_GET_POS":
            self._run_mouse_get_pos(node, args)
            return

        try:
            self._exec.execute(cmd, resolved)
            self._on_cmd(node.line_num)
        except ValueError as exc:
            self._log("WARNING", f"Line {node.line_num + 1}: {exc}")
        except Exception as exc:          # noqa: BLE001
            self._log("ERROR", f"Line {node.line_num + 1}: {exc!r}")

    # ------------------------------------------------------------------
    # MOUSE_GET_POS helper
    # ------------------------------------------------------------------

    def _run_mouse_get_pos(self, node: CmdNode, args: list[str]) -> None:
        """MOUSE_GET_POS [$x] [$y] — store current cursor coords into variables.

        Both args are optional; you can pass only the first to capture just X.
        If an arg does not start with the variable prefix it is silently ignored.
        """
        from src.core.prefix import VARIABLE_PREFIX
        x, y = self._exec.get_mouse_pos()
        if len(args) >= 1 and args[0].startswith(VARIABLE_PREFIX):
            self._vars.set(args[0], x)
            self._log("INFO", f"{args[0]} = {x}")
        if len(args) >= 2 and args[1].startswith(VARIABLE_PREFIX):
            self._vars.set(args[1], y)
            self._log("INFO", f"{args[1]} = {y}")
        self._on_cmd(node.line_num)
        if self._vars_changed_fn:
            self._vars_changed_fn(self._vars.as_dict())

    # ------------------------------------------------------------------
    # AssignNode  (#var = expr  /  #var = FUNCTION args)
    # ------------------------------------------------------------------

    def _run_assign(self, node: AssignNode) -> None:
        from src.core.expression import eval_expr, call_function, FUNCTION_NAMES

        rhs = node.rhs_tokens
        if not rhs:
            self._vars.set(node.var_name, 0)
            self._on_cmd(node.line_num)
            return

        # Determine whether RHS is a FUNCTION call
        if rhs[0].upper() in FUNCTION_NAMES:
            value = call_function(
                func_name     = rhs[0],
                args          = rhs[1:],
                templates_dir = self._templates_dir,
                variables     = self._vars,
                log           = self._log,
            )
        else:
            value = eval_expr(rhs, self._vars, log=self._log)

        self._vars.set(node.var_name, value)
        self._log("INFO", f"{node.var_name} = {value!r}")
        self._on_cmd(node.line_num)
        if self._vars_changed_fn:
            self._vars_changed_fn(self._vars.as_dict())

    # ------------------------------------------------------------------
    # IfNode
    # ------------------------------------------------------------------

    def _run_if(self, node: IfNode) -> None:
        for cond_tokens, body in node.branches:
            if self._cond_fn(cond_tokens):
                self.run(body)
                return                      # skip remaining branches
        if node.else_body:
            self.run(node.else_body)

    # ------------------------------------------------------------------
    # LoopNode
    # ------------------------------------------------------------------

    def _run_loop(self, node: LoopNode) -> None:
        # Phase 5: evaluate count_expr as an expression (supports #vars)
        from src.core.expression import eval_expr
        try:
            count = int(eval_expr([node.count_expr], self._vars, log=self._log))
        except (ValueError, TypeError):
            self._log("WARNING", f"LOOP: invalid count {node.count_expr!r}, defaulting to 1")
            count = 1

        for _ in range(count):
            if self._exec.stop_event.is_set():
                raise _Exit()
            try:
                self.run(node.body)
            except _Break:
                return
            except _Continue:
                continue

    # ------------------------------------------------------------------
    # WhileNode
    # ------------------------------------------------------------------

    def _run_while(self, node: WhileNode) -> None:
        iterations = 0
        while self._cond_fn(node.condition):
            if self._exec.stop_event.is_set():
                raise _Exit()
            if iterations >= _MAX_ITERATIONS:
                self._log("WARNING", f"WHILE: iteration limit ({_MAX_ITERATIONS}) reached")
                return
            try:
                self.run(node.body)
            except _Break:
                return
            except _Continue:
                pass
            iterations += 1

    # ------------------------------------------------------------------
    # RepeatNode
    # ------------------------------------------------------------------

    def _run_repeat(self, node: RepeatNode) -> None:
        iterations = 0
        while True:
            if self._exec.stop_event.is_set():
                raise _Exit()
            if iterations >= _MAX_ITERATIONS:
                self._log("WARNING", f"REPEAT: iteration limit ({_MAX_ITERATIONS}) reached")
                return
            try:
                self.run(node.body)
            except _Break:
                return
            except _Continue:
                pass
            if self._cond_fn(node.condition):
                return                      # condition true → exit loop
            iterations += 1

    # ------------------------------------------------------------------
    # TryCatchNode
    # ------------------------------------------------------------------

    def _run_try(self, node: TryCatchNode) -> None:
        try:
            self.run(node.try_body)
        except (_Break, _Continue, _Return, _Exit):
            raise                           # control-flow exceptions pass through
        except Exception as exc:            # noqa: BLE001
            self._log("WARNING", f"TRY block caught: {exc!r}")
            if node.catch_body:
                self.run(node.catch_body)

    # ------------------------------------------------------------------
    # CallNode
    # ------------------------------------------------------------------

    def _run_call(self, node: CallNode) -> None:
        if self._depth >= _MAX_CALL_DEPTH:
            self._log("ERROR", f"CALL: depth limit ({_MAX_CALL_DEPTH}) exceeded")
            return

        if not node.filename:
            self._log("WARNING", "CALL: missing filename")
            return

        path = self._macros_dir / node.filename
        if not path.exists():
            self._log("WARNING", f"CALL: file not found: {node.filename!r}")
            return

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self._log("ERROR", f"CALL: cannot read {node.filename!r}: {exc}")
            return

        # Import here to avoid circular imports at module load time
        from src.core.parser     import parse_lines
        from src.core.ast_builder import build_ast, ParseError

        sugar_map   = self._settings.syntax_sugar
        token_lines = parse_lines(text, sugar_map)

        try:
            sub_nodes = build_ast(token_lines)
        except ParseError as exc:
            self._log("ERROR", f"CALL {node.filename!r}: parse error — {exc}")
            return

        sub_runner = ASTRunner(
            executor         = self._exec,
            cond_fn          = self._cond_fn,
            macros_dir       = self._macros_dir,
            templates_dir    = self._templates_dir,
            settings         = self._settings,
            log_fn           = self._log,
            depth            = self._depth + 1,
            on_cmd           = self._on_cmd,
            variables        = self._vars,   # shared variable scope
            vars_changed_fn  = self._vars_changed_fn,
        )
        self._log("INFO", f"CALL → {node.filename}")
        try:
            sub_runner.run(sub_nodes)
        except _Return:
            pass                            # RETURN exits callee, not caller
        self._log("INFO", f"CALL ← {node.filename}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_args(self, args: list[str]) -> list[str]:
        """Substitute $var references in a plain arg list."""
        result = []
        for a in args:
            if a.startswith(VARIABLE_PREFIX):
                result.append(str(self._vars.get(a, 0)))
            else:
                result.append(a)
        return result
