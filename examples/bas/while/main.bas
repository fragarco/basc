' Simple WHILE example that also introduces
' the use of INPUT

answer$ = ""
password$ = "please"
WHILE answer$ <> password$
    INPUT "What is the password: ", answer$
WEND
PRINT "That is correct, access granted"

endloop:
    GOTO endloop