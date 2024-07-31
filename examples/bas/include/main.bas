' Simple example of incbas usage
MODE 1
INCBAS "simple.bas"
y=10
LABEL main
FOR x=2 TO 25
    LOCATE x-1,y: PRINT " "
    LOCATE x,y
    PRINT "Hello World!"
NEXT
CLS
y=10
GOTO main