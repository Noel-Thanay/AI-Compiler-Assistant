from src.compiler.ast_nodes import *

class SymbolTable:
    def __init__(self):
        self.scopes = [{}]

    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        self.scopes.pop()

    def define(self, name, type_info):
        self.scopes[-1][name] = type_info

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

class SemanticAnalyzer:
    def __init__(self, diagnostics):
        self.symbol_table = SymbolTable()
        self.diagnostics = diagnostics

    def visit(self, node):
        method_name = f'visit_{type(node).__name__.lower()}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        if hasattr(node, 'statements'):
            for stmt in node.statements: self.visit(stmt)
        elif isinstance(node, list):
            for item in node: self.visit(item)

    def visit_program(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_vardeclaration(self, node):
        for name, val in zip(node.names, node.values):
            if self.symbol_table.lookup(name) is not None:
                self.diagnostics.report("SemanticError", "S101", f"Variable '{name}' already declared", line=getattr(node, 'line', None))
            self.symbol_table.define(name, {"type": node.type_name})
            if val: self.visit(val)

    def visit_assignment(self, node):
        if self.symbol_table.lookup(node.name) is None:
            self.diagnostics.report("SemanticError", "S102", f"Variable '{node.name}' used before declaration", line=getattr(node, 'line', None))
        self.visit(node.value)

    def visit_identifier(self, node):
        if self.symbol_table.lookup(node.name) is None:
            self.diagnostics.report("SemanticError", "S102", f"Variable '{node.name}' used before declaration", line=getattr(node, 'line', None))

    def visit_functiondefinition(self, node):
        self.symbol_table.define(node.name, {"type": node.return_type, "signature": node.params})
        self.symbol_table.push_scope()
        for p_type, p_name in node.params:
            self.symbol_table.define(p_name, {"type": p_type})
        self.visit(node.body)
        self.symbol_table.pop_scope()

    def visit_functioncall(self, node):
        func = self.symbol_table.lookup(node.name)
        if func is None:
            self.diagnostics.report("SemanticError", "S103", f"Function '{node.name}' not defined", line=getattr(node, 'line', None))
        for arg in node.args: self.visit(arg)
