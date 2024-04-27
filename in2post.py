"""
Expresionies aritmeticas a notacion postfija
Gramatica:

expr -> expr + termino { print('+')}
expr -> expr - termino { print('-')}
expr -> termino
termino -> 0 {print('0')}
...
termino -> 9 {print('9')}
"""
import sys

g_cadena = "9-5+2" + '\n'
g_output = ""
g_char = 0

def get_char():
    global g_char
    c = g_cadena[g_char]
    g_char = g_char + 1
    return c

def put_char(c):
    global g_output
    g_output = g_output + c

def view_next():
    return g_cadena[g_char]

def error(text):
    print("Error:", text)
    sys.exit(1)

def match(c, sym):
    if c != sym:
        error("got symbol %s but %s was expected" % (c, sym))

def termino(c):
    if c.isdigit():
        put_char(c)
        return get_char()
    else:
        error("got %s but a digit was expected" % (c))

def expr(c):
    c = termino(c)
    while(1):
        if c == '+':
            c = get_char()
            c = termino(c)
            put_char('+')
        elif c == '-':
            c = get_char()
            c = termino(c)
            put_char('-')
        else:
            break

def main():
    c = get_char()
    expr(c)
    print("Result:", g_output)

if __name__ == "__main__":
    main()
