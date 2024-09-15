' Example of how to see the real representation of a number in memory

a! = 43.375
PRINT a!     ' prints the actual value
PRINT @a!    ' prints the memory address

FOR i=0 TO 4
    PRINT HEX$(PEEK(@a!+i), 2);
NEXT

LABEL LOOP
    GOTO LOOP
