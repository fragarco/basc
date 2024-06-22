@echo off
call python3 src/basc.py examples/bas/%1/main.bas --verbose && call python3 src/dsk.py --new --put-bin examples/bas/%1/main.bin %1.dsk
@echo on