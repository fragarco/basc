' Simple example of jumping to labels and the use
' of PRINT and INKEY$

CLS
PRINT "Select Yes or No (Y/N)?"

mainloop:
'    a$=INKEY$

'    IF a$="" THEN mainloop
'    IF a$="y" OR a$="Y" THEN endyes
'    IF a$="N" OR a$="n" THEN endno
GOTO mainloop

endyes:
'    PRINT "You have selected YES"
'    END

endno:
'    PRINT "You have selected NO"
'    END
