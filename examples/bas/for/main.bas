' This is small variation of the BASIC test
' created by Noel Llopis to measure the speed of 
' different BASIC version in 8 bit machines
' Amstrad usually takes around 28s when using real numbers
' and 17s when using integers.
' This is a good way to measure if the compiler produces
' speed improvements at all.

s = 0
print "1"
print "2"
print "3";
print "4";
print "hola"
print "adios"
loop:
    goto loop
'CLS
'FOR i=1 to 10
''    s = 0
''    FOR j=1 to 1000
''        s=1000+j
''    NEXT j
''    PRINT "."
'NEXT i
'PRINT "s"

