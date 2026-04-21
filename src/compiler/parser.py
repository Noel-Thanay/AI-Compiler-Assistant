import ply.yacc as yacc
from src.compiler.lexer import tokens
from src.compiler.ast_nodes import *

# Module-level diagnostics engine reference (replaced by UI at runtime)
_diagnostics = None

def get_line(p):
    for i in range(1, len(p)):
        if p.lineno(i): return p.lineno(i)
    return p.lexer.lineno

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'EQ', 'NEQ'),
    ('left', 'LT', 'GT', 'LE', 'GE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE', 'MOD'),
    ('right', 'POWER'),
    ('right', 'UMINUS'),
)

def p_program(p):
    '''program : external_declaration_list'''
    p[0] = Program(p[1], line=get_line(p))

def p_external_declaration_list(p):
    '''external_declaration_list : external_declaration_list external_declaration
                                 | external_declaration'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_external_declaration(p):
    '''external_declaration : declaration
                            | function_definition'''
    p[0] = p[1]

def p_declaration(p):
    '''declaration : type_specifier init_declarator_list SEMICOLON'''
    p[0] = VarDeclaration(p[1], [d[0] for d in p[2]], [d[1] for d in p[2]], line=get_line(p))

def p_init_declarator_list(p):
    '''init_declarator_list : init_declarator_list COMMA init_declarator
                            | init_declarator'''
    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]

def p_init_declarator(p):
    '''init_declarator : ID ASSIGN expression
                       | ID'''
    p[0] = (p[1], p[3]) if len(p) == 4 else (p[1], None)

def p_type_specifier(p):
    '''type_specifier : INT
                      | FLOAT
                      | STRING_TYPE
                      | VOID'''
    p[0] = p[1]

def p_function_definition(p):
    '''function_definition : type_specifier ID LPAREN parameter_list RPAREN compound_statement
                           | type_specifier ID LPAREN RPAREN compound_statement'''
    if len(p) == 7:
        p[0] = FunctionDefinition(p[1], p[2], p[4], p[6], line=get_line(p))
    else:
        p[0] = FunctionDefinition(p[1], p[2], [], p[5], line=get_line(p))

def p_parameter_list(p):
    '''parameter_list : parameter_list COMMA parameter_declaration
                      | parameter_declaration'''
    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]

def p_parameter_declaration(p):
    '''parameter_declaration : type_specifier ID'''
    p[0] = (p[1], p[2])

def p_statement(p):
    '''statement : compound_statement
                 | expression_statement
                 | selection_statement
                 | iteration_statement
                 | jump_statement
                 | print_statement
                 | local_declaration'''
    p[0] = p[1]

def p_local_declaration(p):
    '''local_declaration : type_specifier init_declarator_list SEMICOLON'''
    p[0] = VarDeclaration(p[1], [d[0] for d in p[2]], [d[1] for d in p[2]], line=get_line(p))

def p_compound_statement(p):
    '''compound_statement : LBRACE statement_list RBRACE
                          | LBRACE RBRACE'''
    p[0] = p[2] if len(p) == 4 else []

def p_statement_list(p):
    '''statement_list : statement_list statement
                      | statement'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_expression_statement(p):
    '''expression_statement : expression SEMICOLON
                            | SEMICOLON'''
    p[0] = p[1] if len(p) == 3 else None

def p_selection_statement(p):
    '''selection_statement : IF LPAREN expression RPAREN statement
                           | IF LPAREN expression RPAREN statement ELSE statement'''
    if len(p) == 6:
        p[0] = IfStatement(p[3], p[5], line=get_line(p))
    else:
        p[0] = IfStatement(p[3], p[5], p[7], line=get_line(p))

def p_iteration_statement(p):
    '''iteration_statement : WHILE LPAREN expression RPAREN statement'''
    p[0] = WhileStatement(p[3], p[5], line=get_line(p))

def p_jump_statement(p):
    '''jump_statement : RETURN expression SEMICOLON
                      | RETURN SEMICOLON'''
    p[0] = ReturnStatement(p[2], line=get_line(p)) if len(p) == 4 else ReturnStatement(None, line=get_line(p))

def p_print_statement(p):
    '''print_statement : PRINT LPAREN expression RPAREN SEMICOLON'''
    p[0] = PrintStatement(p[3], line=get_line(p))

def p_expression(p):
    '''expression : assignment_expression
                  | binary_expression
                  | unary_expression
                  | primary_expression
                  | function_call'''
    p[0] = p[1]

def p_assignment_expression(p):
    '''assignment_expression : ID ASSIGN expression
                             | ID ADD_ASSIGN expression
                             | ID SUB_ASSIGN expression
                             | ID MUL_ASSIGN expression
                             | ID DIV_ASSIGN expression'''
    p[0] = Assignment(p[1], p[3], p[2], line=get_line(p))

def p_binary_expression(p):
    '''binary_expression : expression PLUS expression
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
    p[0] = BinaryOp(p[1], p[2], p[3], line=get_line(p))

def p_unary_expression(p):
    '''unary_expression : MINUS expression %prec UMINUS
                        | NOT expression
                        | INCREMENT ID
                        | DECREMENT ID'''
    if p[1] in ['++', '--']:
        p[0] = UnaryOp(p[1], Identifier(p[2], line=get_line(p)), line=get_line(p))
    else:
        p[0] = UnaryOp(p[1], p[2], line=get_line(p))

def p_primary_expression(p):
    '''primary_expression : ID
                          | NUMBER
                          | STRING
                          | TRUE
                          | FALSE
                          | LPAREN expression RPAREN'''
    if len(p) == 4:
        p[0] = p[2]
    elif p.slice[1].type == 'ID':
        p[0] = Identifier(p[1], line=get_line(p))
    elif p.slice[1].type == 'NUMBER':
        p[0] = Number(p[1], line=get_line(p))
    elif p.slice[1].type == 'STRING':
        p[0] = StringLiteral(p[1], line=get_line(p))
    elif p.slice[1].type in ('TRUE', 'FALSE'):
        p[0] = Number(1 if p.slice[1].type == 'TRUE' else 0, line=get_line(p))

def p_function_call(p):
    '''function_call : ID LPAREN argument_list RPAREN
                     | ID LPAREN RPAREN'''
    p[0] = FunctionCall(p[1], p[3], line=get_line(p)) if len(p) == 5 else FunctionCall(p[1], [], line=get_line(p))

def p_argument_list(p):
    '''argument_list : argument_list COMMA expression
                     | expression'''
    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]

def p_error(p):
    global _diagnostics
    if p:
        msg = f"Syntax error at '{p.value}'"
        line = p.lineno
    else:
        msg = "Syntax error at end of file"
        line = None
    if _diagnostics:
        _diagnostics.report("SyntaxError", "E100", msg, line=line)

parser = yacc.yacc()

def parse(source, diag=None):
    """Safe parse entry point that wires diagnostics and resets lexer state."""
    global _diagnostics
    from src.compiler.lexer import lexer
    import re
    _diagnostics = diag
    lexer.diagnostics = diag
    lexer.lineno = 1
    lexer.input("")  # flush internal state
    return parser.parse(source, lexer=lexer)
