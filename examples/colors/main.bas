' Simple example using the main commands to control
' screen and text colors

MODE 1
BORDER 0
PAPER 3
INK 0,1,2

CLS
PEN 0
PRINT "Hello world"

LABEL main
    GOTO main