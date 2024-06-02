' This is small variation of the BASIC test
' created by Noel Llopis to measure the speed of 
' different BASIC version in 8 bit machines
' Amstrad usually takes around 28s when using real numbers
' and 17s when using integers.
' This is a good way to measure if the compiler produces
' speed improvements at all.

CLS
FOR i=1 to 10
    FOR j=1 to 1000
        s = 1000 + j
    NEXT j
    PRINT ".";
NEXT i
PRINT " END!"

loop:
    goto loop

