' Simple example of jumping to labels and the use
' of PRINT and INKEY$

CLS
PRINT "Select Yes or No (Y/N)?"

mainloop:
    a$=INKEY$
    IF a$="" THEN mainloop
    IF a$="y" OR a$="Y" THEN endyes
    IF a$="N" OR a$="n" THEN endno
    print a$
    GOTO mainloop

endyes:
    PRINT "You have selected YES"
    GOTO mainloop

endno:
    PRINT "You have selected NO"
    GOTO mainloop


