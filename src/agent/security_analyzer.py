from src.compiler.ast_nodes import *

dangerous_identifiers = [
    "system", "exec", "popen", "gets", "fork",
    "strcpy", "strcat", "sprintf", "vsprintf", "malloc"
]

suspicious_strings = [
    "password", "admin", "root", "api_key",
    "secret", "token", "credentials"
]

class SecurityAnalyzer:
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        self.has_warnings = False

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

    def report(self, msg, line):
        self.diagnostics.report("Security", "S001", msg, line=line)
        self.has_warnings = True

    def visit_assignment(self, node):
        if hasattr(node, 'name') and isinstance(node.name, str) and node.name in dangerous_identifiers:
            self.report(f"dangerous identifier '{node.name}' detected (possible command execution)", getattr(node, 'line', None))
        self.generic_visit(node)

    def visit_identifier(self, node):
        if node.name == "gets":
            self.report("use of 'gets' detected (buffer overflow risk)", getattr(node, 'line', None))
        elif node.name in dangerous_identifiers:
            self.report(f"suspicious identifier '{node.name}' detected", getattr(node, 'line', None))
        self.generic_visit(node)

    def visit_functioncall(self, node):
        if node.name in dangerous_identifiers:
            self.report(f"use of dangerous function '{node.name}' (potential vulnerability)", getattr(node, 'line', None))
        self.generic_visit(node)

    def visit_stringliteral(self, node):
        content = node.value.lower()
        for suspicious in suspicious_strings:
            if suspicious in content:
                self.report(f"hardcoded sensitive information '{suspicious}' detected in string", getattr(node, 'line', None))
        if len(node.value) > 256:
            self.report("Extremely long string literal (Potential overflow risk)", getattr(node, 'line', None))
        self.generic_visit(node)

    def visit_binaryop(self, node):
        # Division by zero
        if node.op == '/':
            if isinstance(node.right, Number) and node.right.value == 0:
                self.report("division by zero detected", getattr(node, 'line', None))

        # Integer overflow detection
        if node.op == '*':
            if isinstance(node.left, Number) and isinstance(node.right, Number):
                if node.left.value > 10**9 or node.right.value > 10**9:
                    self.report("possible integer overflow", getattr(node, 'line', None))

        self.generic_visit(node)

    def visit_ifstatement(self, node):
        # Suspicious logic (always true)
        if isinstance(node.condition, Number) and node.condition.value == 1:
            self.report("condition always true (suspicious logic)", getattr(node, 'line', None))
        self.generic_visit(node)

    def visit_whilestatement(self, node):
        # Infinite loop detection
        if isinstance(node.condition, Number) and node.condition.value == 1:
            self.report("possible infinite loop detected (while true)", getattr(node, 'line', None))
        self.generic_visit(node)

    def visit_vardeclaration(self, node):
        for name in node.names:
            lower_name = name.lower()
            if "password" in lower_name or "secret" in lower_name:
                self.report(f"Potential sensitive data in variable '{name}'", getattr(node, 'line', None))
            if name in dangerous_identifiers:
                self.report(f"dangerous identifier '{name}' detected as variable", getattr(node, 'line', None))
        self.generic_visit(node)
