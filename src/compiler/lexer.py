import ply.lex as lex
import re

reserved = {
    'if': 'IF', 'else': 'ELSE', 'while': 'WHILE', 'for': 'FOR',
    'int': 'INT', 'float': 'FLOAT', 'string': 'STRING_TYPE',
    'print': 'PRINT', 'true': 'TRUE', 'false': 'FALSE',
    'return': 'RETURN', 'void': 'VOID'
}

tokens = [
    'ID', 'NUMBER', 'STRING', 'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD', 'POWER',
    'ASSIGN', 'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE', 'SEMICOLON', 'COMMA',
    'LT', 'GT', 'LE', 'GE', 'EQ', 'NEQ', 'AND', 'OR', 'NOT',
    'INCREMENT', 'DECREMENT', 'ADD_ASSIGN', 'SUB_ASSIGN', 'MUL_ASSIGN', 'DIV_ASSIGN'
] + list(reserved.values())

t_EQ, t_NEQ, t_LE, t_GE, t_LT, t_GT = r'==', r'!=', r'<=', r'>=', r'<', r'>'
t_ASSIGN, t_PLUS, t_MINUS, t_TIMES, t_DIVIDE = r'=', r'\+', r'-', r'\*', r'/'
t_LPAREN, t_RPAREN, t_LBRACE, t_RBRACE, t_SEMICOLON = r'\(', r'\)', r'\{', r'\}', r';'
t_AND, t_OR, t_NOT, t_MOD, t_POWER, t_COMMA = r'&&', r'\|\|', r'!', r'%', r'\^', r','
t_INCREMENT, t_DECREMENT = r'\+\+', r'--'
t_ADD_ASSIGN, t_SUB_ASSIGN, t_MUL_ASSIGN, t_DIV_ASSIGN = r'\+=', r'-=', r'\*=', r'/='

t_ignore = ' \t\r'

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_NUMBER(t):
    r'\d+(\.\d+)?'
    t.value = float(t.value) if '.' in t.value else int(t.value)
    return t

def t_STRING(t):
    r'\"([^\\\n]|(\\.))*?\"'
    t.value = t.value[1:-1]
    return t

def t_newline(t):
    r'(\r\n|\n)+'
    t.lexer.lineno += len(re.findall(r'\n', t.value))

def t_COMMENT(t):
    r'\//.*'
    pass

def find_column(input_data, token):
    line_start = input_data.rfind('\n', 0, token.lexpos) + 1
    return (token.lexpos - line_start) + 1

def t_error(t):
    if hasattr(t.lexer, "diagnostics"):
        t.lexer.diagnostics.report("LexicalError", "ELEX", f"Illegal character '{t.value[0]}'", line=t.lineno)
    t.lexer.skip(1)

lexer = lex.lex()
