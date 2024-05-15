' Simple example of jumping to labels and the use
' of PRINT and INKEY$

CLS
PRINT "Select Yes or No (Y/N)?"

mainloop:
'    a$=INKEY$

'    IF a$="" THEN mainloop
'    IF a$="y" OR a$="Y" THEN endyes
'    IF a$="N" OR a$="n" THEN endno
'    GOTO mainloop

endyes:
'    PRINT "You have selected YES"
'    END

endno:
'    PRINT "You have selected NO"
'    END

' original code
' 10 CLS
' 20 PRINT "Select Yes or No (Y/N)?"
' 30 a$=INKEY$
' 40 IF a$="" THEN 30
' 50 IF a$="y" OR a$="Y" THEN 80
' 60 IF a$="N" OR a$="n" THEN 90
' 70 GOTO 30
' 80 PRINT "You have selected YES": END
' 90 PRINT "You have selected NO":
