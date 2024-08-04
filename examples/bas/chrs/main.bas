' CHR$ Example of use

MODE 2
FOR x=32 TO 255
    PRINT x;" ";CHR$(x);" ";
NEXT

LABEL loop
    GOTO loop