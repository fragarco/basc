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
g_output = []
g_char = 0

def get_char():
    global g_char
    c = g_cadena[g_char]
    g_char = g_char + 1
    return c

def output(line):
    global g_output
    g_output.append(line + '\n')

def view_next():
    return g_cadena[g_char]

def error(text):
    print("Error:", text)
    sys.exit(1)

def match(c, sym):
    if c != sym:
        error("got symbol %s but %s was expected" % (c, sym))

def term(c, reg = 'a'):
    if c.isdigit():
        output('ld %s, %s' %(reg, c))
        return get_char()
    else:
        error("got %s but a digit was expected" % (c))

def expr(c):
    c = term(c)
    while(1):
        if c == '+':
            c = get_char()
            c = term(c, 'b')
            output("add b")
        elif c == '-':
            c = get_char()
            c = term(c, 'b')
            output('sub b')
        else:
            break

def main():
    c = get_char()
    expr(c)
    with open('output.asm', 'w') as fd:
        fd.writelines(g_output)

if __name__ == "__main__":
    main()
