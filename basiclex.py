"""
La gramática independiente del contexto (GIC) representada por el analizador 
léxico anteriormente proporcionado describe la estructura sintáctica básica del 
lenguaje BASIC desarrollado por Locomotive para los Amstrad CPC. Aquí está una 
representación simplificada de la GIC:

programa -> sentencia programa | sentencia
sentencia -> PRINT expr |
            LET identificador ASSIGN expr |
            IF expr THEN bloque_sentencias ENDIF |
            WHILE expr DO bloque_sentencias ENDWHILE

bloque_sentencias -> sentencia bloque_sentencias | ε
expr -> termino operador_aritmetico expr | termino
termino -> NUMBER | STRING | IDENTIFIER
operador_aritmetico -> PLUS | MINUS | TIMES | DIVIDE
identificador -> IDENTIFIER | IDENTIFIER_ASSIGN

Esta GIC describe las reglas básicas de formación de sentencias y expresiones en
el lenguaje BASIC para Amstrad CPC. Las producciones `programa`, `sentencia`,
`bloque_sentencias`, `expr`, `termino`, `operador_aritmetico` e `identificador`
definen la estructura general del programa, las sentencias, las expresiones,
los términos y los identificadores, mientras que las producciones específicas
como `PRINT`, `LET`, `IF`, `WHILE`, `THEN`, `ENDIF`, `DO`, `ENDWHILE`,
`NUMBER`, `STRING`, `IDENTIFIER_ASSIGN` y los operadores aritméticos
(`PLUS`, `MINUS`, `TIMES`, `DIVIDE`) representan las palabras clave y tokens
específicos del lenguaje.
"""

import re

# Definición de tokens
tokens = [
    ('NUMBER', r'\d+'),
    ('STRING', r'"([^"\\]|\\.)*"'),
    ('PLUS', r'\+'),
    ('MINUS', r'-'),
    ('TIMES', r'\*'),
    ('DIVIDE', r'/'),
    ('LPAREN', r'\('),
    ('RPAREN', r'\)'),
    ('IF', r'IF'),
    ('THEN', r'THEN'),
    ('ELSE', r'ELSE'),
    ('WHILE', r'WHILE'),
    ('END', r'END'),
    ('PRINT', r'PRINT'),
    ('IDENTIFIER', r'[A-Z][A-Z0-9]*'),
    ('NEWLINE', r'\n'),
    ('IGNORED', r'[ \t]+'),
]

# Función para analizar el código fuente
def lex(data):
    tokens_regex = '|'.join('(?P<%s>%s)' % pair for pair in tokens)
    line_number = 10  # Número de línea inicial
    for mo in re.finditer(tokens_regex, data):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'NUMBER':
            yield kind, int(value), line_number
        elif kind == 'NEWLINE':
            line_number += 10  # Incrementar el número de línea por 10
        elif kind != 'IGNORED':
            if kind == 'IDENTIFIER':
                # Verificar si el identificador está seguido de un operador de asignación
                next_char_index = mo.end()
                if next_char_index < len(data) and data[next_char_index] == '=':
                    kind = 'IDENTIFIER_ASSIGN'
            yield kind, value, line_number

# Ejemplo de uso
codigo_fuente = """
10 PRINT "HELLO WORLD"
20 X = 5
30 IF X > 0 THEN
40   PRINT "X is positive"
50 ELSE
60   PRINT "X is non-positive"
70 ENDIF
80 WHILE X > 0
90   PRINT X
100  X = X - 1
110 ENDWHILE
"""

for token in lex(codigo_fuente):
    print(token)
