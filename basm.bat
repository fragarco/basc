@echo off
call python3 src/basm.py examples/bas/%1/main.asm
call python3 src/dsk.py --new --put-bin examples/bas/%1/main.bin %1.dsk
@echo on