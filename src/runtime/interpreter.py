from src.compiler.ast_nodes import *


class ReturnSignal(Exception):
    """Used to unwind the call stack when a return statement is hit."""
    def __init__(self, value):
        self.value = value


class Interpreter:
    def __init__(self):
        self.globals = {}
        self.functions = {}
        self.output = []

    def execute(self, node):
        self.output = []
        self.globals = {}
        self.functions = {}
        try:
            self.visit(node)
        except ReturnSignal as r:
            pass  # top-level return is fine
        except Exception as e:
            self.output.append(f"Runtime Error: {str(e)}")
        result = "\n".join(self.output)
        return result if result else "(no output)"

    def visit(self, node):
        if node is None:
            return None
        if isinstance(node, list):
            result = None
            for item in node:
                result = self.visit(item)
            return result
        method_name = f'visit_{type(node).__name__.lower()}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        return None

    # ── Program ──────────────────────────────────────────────────────────────
    def visit_program(self, node):
        # First pass: register all function definitions
        for stmt in node.statements:
            if isinstance(stmt, FunctionDefinition):
                self.functions[stmt.name] = stmt
        # Second pass: execute non-function declarations at top level
        for stmt in node.statements:
            if not isinstance(stmt, FunctionDefinition):
                self.visit(stmt)
        # If there is a 'main' function, call it
        if "main" in self.functions:
            self._call_function("main", [])

    # ── Declarations ─────────────────────────────────────────────────────────
    def visit_vardeclaration(self, node):
        for name, val in zip(node.names, node.values):
            self.globals[name] = self.visit(val) if val is not None else 0

    # ── Assignment ───────────────────────────────────────────────────────────
    def visit_assignment(self, node):
        val = self.visit(node.value)
        current = self.globals.get(node.name, 0)
        if node.operator == '=':
            self.globals[node.name] = val
        elif node.operator == '+=':
            self.globals[node.name] = current + val
        elif node.operator == '-=':
            self.globals[node.name] = current - val
        elif node.operator == '*=':
            self.globals[node.name] = current * val
        elif node.operator == '/=':
            self.globals[node.name] = current / val if val != 0 else 0
        return self.globals[node.name]

    # ── Expressions ──────────────────────────────────────────────────────────
    def visit_binaryop(self, node):
        l = self.visit(node.left)
        r = self.visit(node.right)
        ops = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b if b != 0 else 0,
            '%': lambda a, b: a % b if b != 0 else 0,
            '**': lambda a, b: a ** b,
            '==': lambda a, b: 1 if a == b else 0,
            '!=': lambda a, b: 1 if a != b else 0,
            '>':  lambda a, b: 1 if a > b else 0,
            '<':  lambda a, b: 1 if a < b else 0,
            '>=': lambda a, b: 1 if a >= b else 0,
            '<=': lambda a, b: 1 if a <= b else 0,
            '&&': lambda a, b: 1 if a and b else 0,
            '||': lambda a, b: 1 if a or b else 0,
        }
        return ops.get(node.op, lambda a, b: 0)(l, r)

    def visit_unaryop(self, node):
        val = self.visit(node.operand)
        if node.op == '-': return -val
        if node.op == '!': return 0 if val else 1
        if node.op == '++': return val + 1
        if node.op == '--': return val - 1
        return val

    def visit_number(self, node):
        return node.value

    def visit_stringliteral(self, node):
        return node.value

    def visit_identifier(self, node):
        if node.name in self.globals:
            return self.globals[node.name]
        return 0

    # ── Statements ───────────────────────────────────────────────────────────
    def visit_printstatement(self, node):
        val = self.visit(node.expression)
        self.output.append(str(val))

    def visit_ifstatement(self, node):
        if self.visit(node.condition):
            self.visit(node.then_branch)
        elif node.else_branch is not None:
            self.visit(node.else_branch)

    def visit_whilestatement(self, node):
        iterations = 0
        while self.visit(node.condition):
            self.visit(node.body)
            iterations += 1
            if iterations > 10000:
                self.output.append("Warning: Infinite loop detected, stopping.")
                break

    def visit_returnstatement(self, node):
        val = self.visit(node.expression) if node.expression else None
        raise ReturnSignal(val)

    # ── Functions ────────────────────────────────────────────────────────────
    def visit_functiondefinition(self, node):
        self.functions[node.name] = node

    def visit_functioncall(self, node):
        func = self.functions.get(node.name)
        if func is None:
            self.output.append(f"Error: Undefined function '{node.name}'")
            return 0
        return self._call_function(node.name, [self.visit(a) for a in node.args])

    def _call_function(self, name, arg_values):
        func = self.functions[name]
        saved_globals = dict(self.globals)
        for (_, p_name), val in zip(func.params, arg_values):
            self.globals[p_name] = val
        ret = None
        try:
            self.visit(func.body)
        except ReturnSignal as r:
            ret = r.value
        self.globals = saved_globals
        return ret
