@echo off

REM *
REM * This file is just an example of how BASC and DSK/CDT utilities can be called to compile programs
REM * and generate files that can be used in emulators or new hardware for the Amstrad CPC
REM *
REM * USAGE: make [clear]

@setlocal

set BAS=python3 ../../src/basc.py
set DSK=python3 ../../src/dsk.py
set CDT=python3 ../../src/cdt.py

set SOURCE=main
set TARGET=chars

set RUNBAS=%BAS% %SOURCE%.bas --verbose
set RUNDSK=%DSK% %TARGET%.dsk --new --put-bin %SOURCE%.bin
set RUNCDT=%CDT% %TARGET%.cdt --new --name %TARGET% --put-bin %SOURCE%.bin

IF "%1"=="clear" (
    del %SOURCE%.bpp
    del %SOURCE%.irc
    del %SOURCE%.asm
    del %SOURCE%.bin
    del %SOURCE%.lst
    del %SOURCE%.map
    del %TARGET%.dsk
    del %TARGET%.cdt
) ELSE (
    call %RUNBAS% && call %RUNDSK% && call %RUNCDT% 
)

@endlocal
@echo on
