' Simple example of jumping to labels and the use
' of PRINT and INKEY$

CLS
PRINT "Select Yes or No (Y/N)?"
tries = 0
mainloop:
    a$=INKEY$
    IF a$="" THEN mainloop
    IF a$="y" OR a$="Y" THEN endyes
    IF a$="N" OR a$="n" THEN endno
    PRINT "You typed ";a$
    tries = tries + 1
    GOTO mainloop

endyes:
    PRINT "You have selected YES ";
    PRINT "after ";tries;" tries"
    tries = 0
    GOTO mainloop

endno:
    PRINT "You have selected NO ";
    PRINT "after ";tries;" tries"
    tries = 0
    GOTO mainloop


