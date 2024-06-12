' Simple WHILE example that also introduces
' the use of INPUT

answer$ = ""
password$ = "please"
WHILE answer$ <> password$
    PRINT "Introduce your password: ";
    INPUT answer$
WEND
PRINT "Access granted"

endloop:
    GOTO endloop