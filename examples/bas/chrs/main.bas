' CHR$ Example of use with special transparency mode
' This example is taken from the Fremos old webpage and
' its series of tutorials about printing sprites in BASIC
' http://fremos.cheesetea.com/2014/03/06/sprites-con-caracteres-en-basic-amstrad-cpc

MODE 1
LOCATE 10,20
PEN 2: PRINT CHR$(233)
PRINT CHR$(22)+CHR$(1)
LOCATE 10,20
PEN 3: PRINT CHR$(232)

LABEL loop
    GOTO loop