#!/usr/bin/env python3
"""
ASMPRJ.PY by Javier Garcia

ASMPRJ is a simple utility to generate a basic ABASM project.
It creates a make.bat or make.sh file and a main.asm source file.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation in its version 3.

This program is distributed in the hope that it will be useful
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
__author__='Javier "Dwayne Hicks" Garcia'
__version__='1.4.4'

import argparse
import os
import platform
import stat
import re
import sys
from typing import Tuple

WINDOWS_TEMPLATE: str = r"""@echo off

REM *
REM * This file is just an example of how ABASM and DSK/CDT utilities can be called to assemble programs
REM * and generate files that can be used in emulators or real hardware for the Amstrad CPC
REM *
REM * USAGE: make [clear]

@setlocal

set ASM=python3 "{ASM}"
set DSK=python3 "{DSK}"

set LOADADDR=0x1200
set SOURCE=main
set TARGET={TARGET}

set RUNASM=%ASM% --start=%LOADADDR% %SOURCE%.asm
set RUNDSK=%DSK% %TARGET%.dsk --new --put-bin %SOURCE%.bin --load-addr %LOADADDR% --map-file %SOURCE%.map --start-addr MAIN

IF "%1"=="clear" (
    del %SOURCE%.bin
    del %SOURCE%.lst
    del %SOURCE%.map
    del %TARGET%.dsk
) ELSE (
    call %RUNASM% && call %RUNDSK%
)

@endlocal
@echo on
"""

UNIX_TEMPLATE: str = """#!/bin/sh

#
# This file is just an example of how ABASM and DSK/CDT utilities can be called to assemble programs
# and generate files that can be used in emulators or real  hardware for the Amstrad CPC
#
# USAGE: ./make.sh [clear]
#

ASM="python3 {ASM}"
DSK="python3 {DSK}"

LOADADDR=0x1200
SOURCE=main
TARGET={TARGET}

RUNASM="$ASM --start=$LOADADDR $SOURCE.asm"
RUNDSK="$DSK $TARGET.dsk --new --put-bin $SOURCE.bin --load-addr $LOADADDR --map-file $SOURCE.map --start-addr MAIN"

if [ "$1" = "clear" ]; then
    rm -f "$SOURCE.bin"
    rm -f "$SOURCE.lst"
    rm -f "$SOURCE.map"
    rm -f "$TARGET.dsk"
else
    $RUNASM && $RUNDSK
fi
"""

MAIN_ASM: str = """OUT_CHAR equ &BB5A    ; Amstrad Firmware routine for char printing

; Main entry point. Make file will search for this symbol and
; set its address as the starting point for the program.

org &1200

main:
    ld   hl, message
    call print_string
    call new_line
loop:
    jp   loop

message: db "Hello world!",0
 
print_string:
    ld   a,(hl)
    or   a
    ret  z
    inc  hl
    call OUT_CHAR
    jr   print_string

new_line:
    ld   a,13
    call OUT_CHAR
    ld   a,10
    jp   OUT_CHAR
"""

def script_tools_paths() -> Tuple[str, str]:
    script_dir: str = os.path.dirname(os.path.abspath(__file__))
    return (
        os.path.join(script_dir, "abasm.py"),
        os.path.join(script_dir, "dsk.py"),
    )

def target_name_from_dir(path: str) -> str:
    return os.path.basename(os.path.normpath(path))

def update_project_win(content: str, asm_path: str, dsk_path: str) -> str:
    """
    We have to use lamda functions to avoid the problem with Windows paths and re.sub calls
    raising errors like 're.error: bad escape'
    """
    content = re.sub(
        r'^set ASM=.*$',
        lambda _: f'set ASM=python3 "{asm_path}"',
        content,
        flags=re.MULTILINE,
    )

    content = re.sub(
        r'^set DSK=.*$',
        lambda _: f'set DSK=python3 "{dsk_path}"',
        content,
        flags=re.MULTILINE,
    )
    return content

def update_project_unix(content: str, asm_path: str, dsk_path: str) -> str:
    """ 
    Linux shouldn't have the same problem than Windows with bars in the path, but
    lets use the lambda workaround just in case.
    """
    content = re.sub(
        r'^ASM=.*$',
        lambda _: f'ASM="python3 {asm_path}"',
        content,
        flags=re.MULTILINE,
    )

    content = re.sub(
        r'^DSK=.*$',
        lambda _: f'DSK="python3 {dsk_path}"',
        content,
        flags=re.MULTILINE,
    )
    return content

def update_project(target_dir: str, is_windows: bool) -> None:
    make_name: str = "make.bat" if is_windows else "make.sh"
    make_path: str = os.path.join(target_dir, make_name)

    if not os.path.isfile(make_path):
        print(f"{make_name} was not found in {target_dir}", file=sys.stderr)
        sys.exit(1)

    asm_path, dsk_path = script_tools_paths()

    with open(make_path, "r", encoding="utf-8") as f:
        content: str = f.read()
    if is_windows:
        content = update_project_win(content, asm_path, dsk_path)
    else:
        content = update_project_unix(content, asm_path, dsk_path)
    with open(make_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"{make_name} was sucessfully updated")

def create_project(target_dir: str, is_windows: bool) -> None:
    target_name: str = target_name_from_dir(target_dir)
    asm_path, dsk_path = script_tools_paths()

    if is_windows:
        make_name: str = "make.bat"
        make_content: str = WINDOWS_TEMPLATE.format(
            ASM=asm_path,
            DSK=dsk_path,
            TARGET=target_name,
        )
    else:
        make_name = "make.sh"
        make_content = UNIX_TEMPLATE.format(
            ASM=asm_path,
            DSK=dsk_path,
            TARGET=target_name,
        )
        
    make_path: str = os.path.join(target_dir, make_name)
    with open(make_path, "w", newline="\n") as f:
        f.write(make_content)

    if not is_windows:
        st = os.stat(make_path)
        os.chmod(make_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Project initialized: {target_dir}")
    print(f"- {make_name} created")
    main_asm_path: str = os.path.join(target_dir, "main.asm")
    if not os.path.exists(main_asm_path):
        with open(main_asm_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(MAIN_ASM)
        print(f"- main.asm created")

def create_argv_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Creates or updates an ABASM project skeleton"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-n", "--new", metavar="TARGET DIRECTORY",
        help="Generates a new project folder with a make file (use '.' for current directory)",
    )
    group.add_argument(
        "-u", "--update", metavar="TARGET DIRECTORY",
        help="Updates paths to ABASM and DSK tools",
    )
    parser.add_argument(
        "-v", "--version", action='version', version=f' Asmprj Version {__version__}',
        help = "Shows program's version and exits")
    return parser

def main() -> None:
    parser = create_argv_parser()
    args = parser.parse_args()
    is_windows: bool = platform.system().lower().startswith("win")

    if args.update is not None:
        target_dir: str = (
            os.getcwd() if args.update == "." else os.path.abspath(args.update)
        )
        update_project(target_dir, is_windows)
        sys.exit(0)

    if args.new == ".":
        target_dir = os.getcwd()
    else:
        target_dir = os.path.abspath(args.new)
        os.makedirs(target_dir, exist_ok=True)
    create_project(target_dir, is_windows)
    sys.exit(0)

if __name__ == "__main__":
    main()
