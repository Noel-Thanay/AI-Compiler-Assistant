import ply.yacc as yacc
from lexer import tokens
from ast_nodes import *

# Operator Precedence (Important!)
precedence = (
    ('left', 'OR'),                 # ||
    ('left', 'AND'),                # &&
    ('right', 'NOT'),               # !
    ('left', 'EQ', 'NEQ'),
    ('left', 'LT', 'GT', 'LE', 'GE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE', 'MOD'),
    ('right', 'POWER'),             # ^
    ('right', 'UMINUS'),            # unary minus
)

# Grammar Rules

def p_program(p):
    '''program : statement_list'''
    p[0] = Program(p[1])


def p_statement_list(p):
    '''statement_list : statement statement_list
                      | statement'''
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
    else:
        p[0] = [p[1]]


def p_statement(p):
    '''statement : declaration
                 | assignment_statement
                 | if_statement
                 | while_statement
                 | print_statement
                 | for_statement'''
    p[0] = p[1]


# Declarations (int and float)

def p_declaration(p):
    '''declaration : INT ID SEMICOLON
                   | FLOAT ID SEMICOLON'''
    p[0] = Declaration(p[1], p[2])


# Assignment

def p_assignment(p):
    '''assignment : ID ASSIGN expression'''
    p[0] = Assignment(p[1], p[3])

def p_assignment_statement(p):
    '''assignment_statement : assignment SEMICOLON'''
    p[0] = p[1]

# Print Statement

def p_print_statement(p):
    '''print_statement : PRINT LPAREN expression RPAREN SEMICOLON'''
    p[0] = PrintStatement(p[3])


# If Statement
def p_if_statement(p):
    '''if_statement : IF LPAREN expression RPAREN block
                    | IF LPAREN expression RPAREN block ELSE block'''
    if len(p) == 6:
        # IF (cond) block
        p[0] = IfStatement(p[3], p[5], None)
    else:
        # IF (cond) block ELSE block
        p[0] = IfStatement(p[3], p[5], p[7])

# While Statement

def p_while_statement(p):
    '''while_statement : WHILE LPAREN expression RPAREN block'''
    p[0] = WhileStatement(p[3], p[5])


# For Statement
def p_for_statement(p):
    '''for_statement : FOR LPAREN for_init SEMICOLON for_condition SEMICOLON for_update RPAREN block'''
    p[0] = ForLoop(p[3], p[5], p[7], p[9])

def p_for_init(p):
    '''for_init : assignment_statement
                | empty'''
    p[0] = p[1]

def p_for_condition(p):
    '''for_condition : expression
                     | empty'''
    p[0] = p[1]

def p_for_update(p):
    '''for_update : assignment_statement
                  | expression
                  | empty'''
    p[0] = p[1]

def p_empty(p):
    'empty :'
    p[0] = None

# Block

def p_block(p):
    '''block : LBRACE statement_list RBRACE'''
    p[0] = Block(p[2])



# --------------------
# EXPRESSIONS
# --------------------

def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression MOD expression
                  | expression POWER expression
                  | expression EQ expression
                  | expression NEQ expression
                  | expression LT expression
                  | expression GT expression
                  | expression LE expression
                  | expression GE expression
                  | expression AND expression
                  | expression OR expression'''
    p[0] = BinaryOp(p[1], p[2], p[3])


# Unary minus
def p_expression_uminus(p):
    '''expression : MINUS expression %prec UMINUS'''
    p[0] = UnaryOp('-', p[2])


# Logical NOT
def p_expression_not(p):
    '''expression : NOT expression'''
    p[0] = UnaryOp('!', p[2])


def p_expression_group(p):
    '''expression : LPAREN expression RPAREN'''
    p[0] = p[2]


def p_expression_number(p):
    '''expression : NUMBER'''
    p[0] = Number(p[1])


def p_expression_boolean(p):
    '''expression : TRUE
                  | FALSE'''
    p[0] = Boolean(p[1])


def p_expression_id(p):
    '''expression : ID'''
    p[0] = Identifier(p[1])


# Syntax Error Handling
def find_column(input, token):
    line_start = input.rfind('\n', 0, token.lexpos) + 1
    return (token.lexpos - line_start) + 1

syntax_errors = []

def p_error(p):
    if p:
        column = find_column(p.lexer.lexdata, p)
        error_msg = {
            "type": "SyntaxError",
            "line": p.lineno,
            "column": column,
            "token": p.value,
            "message": f"Unexpected token '{p.value}'"
        }
    else:
        error_msg = {
            "type": "SyntaxError",
            "message": "Unexpected end of input"
        }

    syntax_errors.append(error_msg)

def p_statement_error(p):
    'statement : error SEMICOLON'
    syntax_errors.append({
        "type": "SyntaxError",
        "line": p.lineno(1),
        "message": "Invalid statement"
    })
    p[0] = None

# Build Parser


parser = yacc.yacc()


# Driver Code

if __name__ == "__main__":
    from lexer import lexer

    data = """
    int x;
    float y;

    x = 10 + 20;

    if (x > 5) {
        print(x);
    }

    while (x != 0) {
        x = x - 1;
    }
    """
    syntax_errors.clear()
    result = parser.parse(data, lexer=lexer)

    print("\nAST OUTPUT:\n")
    print(result)
