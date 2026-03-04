# AST Node Definitions for Mini-C

class ASTNode:
    pass


class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f"Program({self.statements})"


class Declaration(ASTNode):
    def __init__(self, datatype, name):
        self.datatype = datatype
        self.name = name

    def __repr__(self):
        return f"Declaration({self.datatype}, {self.name})"


class Assignment(ASTNode):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"Assignment({self.name}, {self.value})"


class PrintStatement(ASTNode):
    def __init__(self, expression):
        self.expression = expression

    def __repr__(self):
        return f"Print({self.expression})"


class IfStatement(ASTNode):
    def __init__(self, condition, then_block, else_block=None):
        self.condition = condition
        self.then_block = then_block
        self.else_block = else_block

    def __repr__(self):
        if self.else_block:
            return f"If({self.condition}, {self.then_block}, Else={self.else_block})"
        return f"If({self.condition}, {self.then_block})"


class WhileStatement(ASTNode):
    def __init__(self, condition, block):
        self.condition = condition
        self.block = block

    def __repr__(self):
        return f"While({self.condition}, {self.block})"


class Block(ASTNode):
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f"Block({self.statements})"


class Number(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Number({self.value})"


class Identifier(ASTNode):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"Identifier({self.name})"


class BinaryOp(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f"BinaryOp({self.left}, '{self.op}', {self.right})"

class UnaryOp(ASTNode):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

    def __repr__(self):
        return f"UnaryOp('{self.op}', {self.operand})"


class Boolean(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Boolean({self.value})"
    
class ForLoop(ASTNode):
    def __init__(self, init, condition, update, body):
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body

    def __repr__(self):
        return f"ForLoop(init={self.init}, cond={self.condition}, update={self.update}, body={self.body})"