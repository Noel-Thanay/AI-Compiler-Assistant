class Node:
    """Base AST node. All nodes carry an optional line number for diagnostics."""
    line = None


class Program(Node):
    def __init__(self, statements, line=None):
        self.statements = statements
        self.line = line

class VarDeclaration(Node):
    def __init__(self, type_name, names, values=None, line=None):
        self.type_name = type_name
        self.names = names
        self.values = values
        self.line = line

class Assignment(Node):
    def __init__(self, name, value, operator='=', line=None):
        self.name = name
        self.value = value
        self.operator = operator
        self.line = line

class BinaryOp(Node):
    def __init__(self, left, op, right, line=None):
        self.left = left
        self.op = op
        self.right = right
        self.line = line

class UnaryOp(Node):
    def __init__(self, op, operand, line=None):
        self.op = op
        self.operand = operand
        self.line = line

class Identifier(Node):
    def __init__(self, name, line=None):
        self.name = name
        self.line = line

class Number(Node):
    def __init__(self, value, line=None):
        self.value = value
        self.line = line

class StringLiteral(Node):
    def __init__(self, value, line=None):
        self.value = value
        self.line = line

class IfStatement(Node):
    def __init__(self, condition, then_branch, else_branch=None, line=None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch
        self.line = line

class WhileStatement(Node):
    def __init__(self, condition, body, line=None):
        self.condition = condition
        self.body = body
        self.line = line

class PrintStatement(Node):
    def __init__(self, expression, line=None):
        self.expression = expression
        self.line = line

class FunctionDefinition(Node):
    def __init__(self, return_type, name, params, body, line=None):
        self.return_type = return_type
        self.name = name
        self.params = params
        self.body = body
        self.line = line

class ReturnStatement(Node):
    def __init__(self, expression, line=None):
        self.expression = expression
        self.line = line

class FunctionCall(Node):
    def __init__(self, name, args, line=None):
        self.name = name
        self.args = args
        self.line = line
