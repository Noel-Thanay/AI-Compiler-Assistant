# Mini-C Lexer using PLY

import ply.lex as lex

# Reserved Keywords 
reserved = {
    'if': 'IF',
    'else': 'ELSE',
    'while': 'WHILE',
    'for': 'FOR',
    'int': 'INT',
    'float': 'FLOAT',
    'print': 'PRINT',
    'true': 'TRUE',
    'false': 'FALSE',
}

# Token List 
tokens = [

    # Identifiers & Constants
    'ID',
    'NUMBER',

    # Arithmetic Operators
    'PLUS',
    'MINUS',
    'TIMES',
    'DIVIDE',

    # Assignment & Relational Operators
    'ASSIGN',
    'EQ',
    'NEQ',
    'LT',
    'GT',
    'LE',
    'GE',

    # Delimiters
    'LPAREN',
    'RPAREN',
    'LBRACE',
    'RBRACE',
    'SEMICOLON',

    'AND', 
    'OR',
    'NOT',
    'MOD',
    'POWER'

] + list(reserved.values())

# Regular Expression Rules


# Order matters for multi-character operators
t_EQ        = r'=='
t_NEQ       = r'!='
t_LE        = r'<='
t_GE        = r'>='
t_LT        = r'<'
t_GT        = r'>'
t_ASSIGN    = r'='

t_PLUS      = r'\+'
t_MINUS     = r'-'
t_TIMES     = r'\*'
t_DIVIDE    = r'/'

t_LPAREN    = r'\('
t_RPAREN    = r'\)'
t_LBRACE    = r'\{'
t_RBRACE    = r'\}'
t_SEMICOLON = r';'

t_AND    = r'&&'
t_OR     = r'\|\|'
t_NOT    = r'!'
t_MOD    = r'%'
t_POWER  = r'\^'


# Ignored Characters
t_ignore = ' \t'

# Identifier Rule (Variables & Keywords)
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value, 'ID')
    return t

# Number Rule (Supports int and float)
def t_NUMBER(t):
    r'\d+(\.\d+)?'
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

# Line Number Tracking
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Column Calculation (Professional Error Reporting)
def find_column(input_data, token):
    line_start = input_data.rfind('\n', 0, token.lexpos) + 1
    return (token.lexpos - line_start) + 1


# Lexical Error Handling
def t_error(t):
    column = find_column(t.lexer.lexdata, t)
    print(f"Illegal character '{t.value[0]}' at line {t.lineno}, column {column}")
    t.lexer.skip(1)


# Build the Lexer
lexer = lex.lex()

# Driver Code (Token Stream Generator)
def run_lexer(input_data):
    lexer.input(input_data)

    print("\nTOKEN STREAM:\n")
    while True:
        tok = lexer.token()
        if not tok:
            break
        print(f"Line {tok.lineno:<3} Type: {tok.type:<10} Value: {tok.value}")

# Main Function (Updated Sample Program)
if __name__ == "__main__":

    sample_program = """
    int x;
    float y;

    x = 10 + 20;
    y = 5.5;

    if (x >= 5) {
        print(x);
    }

    while (x != 0) {
        x = x - 1;
    }

    x = x @ 2;
    """

    run_lexer(sample_program)
