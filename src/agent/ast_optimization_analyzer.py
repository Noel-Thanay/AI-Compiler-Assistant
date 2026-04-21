from src.compiler.ast_nodes import *

class ASTOptimizationAnalyzer:
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        self._scope_stack = []
        self._declarations = []

    def analyze(self, ast):
        self.visit(ast)
        for details in self._declarations:
            if not details["used"]:
                line = details["line"]
                is_param = details.get("is_param", False)
                prefix = "Parameter" if is_param else "Variable"
                self.diagnostics.report(
                    "OptimizationHint",
                    "O001",
                    f"{prefix} '{details['name']}' is declared but never read or used.",
                    line=line
                )

    def _push_scope(self):
        self._scope_stack.append({})

    def _pop_scope(self):
        if self._scope_stack:
            self._scope_stack.pop()

    def _declare(self, name, line=None, is_param=False):
        if not self._scope_stack:
            self._push_scope()
        decl = {
            "name": name,
            "line": line,
            "is_param": is_param,
            "used": False,
        }
        self._scope_stack[-1][name] = decl
        self._declarations.append(decl)

    def _mark_used(self, name):
        for scope in reversed(self._scope_stack):
            if name in scope:
                scope[name]["used"] = True
                return

    def visit(self, node):
        if not node: return
        method = getattr(self, f"visit_{type(node).__name__.lower()}", self.generic_visit)
        method(node)

    def generic_visit(self, node):
        if isinstance(node, list):
            for item in node: self.visit(item)
        elif hasattr(node, '__dict__'):
            for val in vars(node).values():
                if isinstance(val, (Node, list)): self.visit(val)

    def visit_program(self, node):
        self._push_scope()
        self.generic_visit(node)
        self._pop_scope()

    def visit_vardeclaration(self, node):
        for name in node.names:
            self._declare(name, line=getattr(node, "line", None), is_param=False)
        self.generic_visit(node)

    def visit_functiondefinition(self, node):
        self._push_scope()
        for param_type, param_name in node.params:
            self._declare(param_name, line=getattr(node, "line", None), is_param=True)
        self.generic_visit(node)
        self._pop_scope()

    def visit_identifier(self, node):
        self._mark_used(node.name)

    def visit_ifstatement(self, node):
        if isinstance(node.condition, Number):
            self.diagnostics.report(
                "OptimizationHint", "O002",
                f"Redundant branch condition: if({node.condition.value}) is static.",
                line=getattr(node.condition, 'line', None)
            )
        elif isinstance(node.condition, BinaryOp) and node.condition.op == '==':
            if isinstance(node.condition.left, Identifier) and isinstance(node.condition.right, Identifier):
                if node.condition.left.name == node.condition.right.name:
                    self.diagnostics.report(
                        "OptimizationHint", "O002",
                        f"Redundant condition: '{node.condition.left.name} == {node.condition.right.name}' is always true.",
                        line=getattr(node.condition, 'line', None)
                    )
        self.generic_visit(node)

    def visit_whilestatement(self, node):
        if isinstance(node.condition, Number) and node.condition.value == 0:
            self.diagnostics.report(
                "OptimizationHint", "O002",
                "Redundant loop condition: while(false) will never execute.",
                line=getattr(node.condition, 'line', None)
            )
        self.generic_visit(node)

    def visit_binaryop(self, node):
        left_val = node.left.value if isinstance(node.left, Number) else None
        right_val = node.right.value if isinstance(node.right, Number) else None

        if node.op == '+':
            if left_val == 0 or right_val == 0:
                self.diagnostics.report("OptimizationHint", "O003", "Redundant addition with 0.", line=getattr(node, 'line', None))
        elif node.op == '*':
            if left_val == 1 or right_val == 1:
                self.diagnostics.report("OptimizationHint", "O003", "Redundant multiplication by 1.", line=getattr(node, 'line', None))
            elif left_val == 0 or right_val == 0:
                self.diagnostics.report("OptimizationHint", "O003", "Multiplication by 0 is always 0.", line=getattr(node, 'line', None))
        elif node.op == '-':
            if right_val == 0:
                self.diagnostics.report("OptimizationHint", "O003", "Redundant subtraction of 0.", line=getattr(node, 'line', None))
        elif node.op == '/':
            if right_val == 1:
                self.diagnostics.report("OptimizationHint", "O003", "Redundant division by 1.", line=getattr(node, 'line', None))

        self.generic_visit(node)
