' Simple example of jumping to labels and the use
' of PRINT and INKEY$
a = 5
if a = 4 goto loop
end
loop:
print "hola"
goto loop

'CLS
'a$ = "Select Yes or No (Y/N)?"
'PRINT a$

'mainloop:
'    a$=INKEY$
'    IF a$="" GOTO mainloop
'    print A$
'    IF a$="y" OR a$="Y" THEN endyes
'    IF a$="N" OR a$="n" THEN endno
'pause:
''    GOTO pause

'endyes:
'    PRINT "You have selected YES"
'    END

'endno:
'    PRINT "You have selected NO"
'    END
