' Simple example of incbas usage
mode 1
incbas "simple.bas"
y=10
main:
for x=2 to 25
    locate x-1,y: print " "
    locate x,y
    print "Hello World!"
next
cls
y=10
goto main