#!/usr/bin/env python
"""
Amstrad Locomotive BASIC compiler.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation in its version 3.

This program is distributed in the hope that it will be useful
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
"""

from __future__ import annotations
from typing import Any
import sys
import os
import pathlib
import argparse
import time
import traceback
from dataclasses import dataclass
from baserror import WarningLevel as WL
from baspp import LocBasPreprocessor, CodeLine
from baslex import LocBasLexer, Token
from basparse import LocBasParser
from emitters.cpcemitter import CPCEmitter
from symbols import symsto_json, SymTable
import astlib as AST
import utils.abasm as ABASM
from basopt import BasOptimizer
import json

__author__='Javier "Dwayne Hicks" Garcia'
__version__= "1.2.6"


@dataclass
class AbascOptions:
    infile: str
    outfile: str
    startaddr: int = 0x0040
    dataaddr: int = 0x4000
    optlevel: int = 2
    warninglevel: WL = WL.ALL
    verbose: bool = False
    debug: bool = False
    strsz: int = 255

def aux_int(param: Any) -> int:
    """
    By default, int params are converted assuming base 10.
    To allow hex values we need to 'auto' detect the base.
    """
    return int(param, 0)

def process_args() -> AbascOptions:
    parser = argparse.ArgumentParser(
        prog='abasc.py',
        description='A Locomotive BASIC compiler for the Amstrad CPC'
    )
    parser.add_argument('infile', help="BAS file with pseudo Locomotive Basic code.")
    parser.add_argument('-O', type=int, default=2, help="Sets the level of optimization (0-disabled, 1-peephole, 2-all). It's set to 2 by default.")
    parser.add_argument('-W', type=int, default=WL.ALL, help="Sets the warning level (0-disabled, 1-only high level warnings, 2-high and medium, 3-high, medium and low).")
    parser.add_argument('--start', type=aux_int, default=0x0040, help="Program Start address (0x0040 by default).")
    parser.add_argument('--data', type=aux_int, default=0x4000, help="Start address for the data block (0x4000 by default).")
    parser.add_argument('-o', '--out', help="Target file name without extension. If missing, <infile> name will be used.")
    parser.add_argument('-v', '--verbose', action='store_true', help="Save to file the outputs of each compile step.")
    parser.add_argument('--version', action='version', version=f' ABASC (Locomotive BASIC Cross Compiler) Version {__version__}', help = "Shows program's version and exits")
    parser.add_argument('--debug', action='store_true', help="Shows some extra information when compilation fails")
    parser.add_argument('--strchars', type=int, default=254, help="Sets the maximum number of characters to preallocate for temporary strings (1–254). Default: 254.")
    args = parser.parse_args()

    outfile = args.out if args.out is not None else args.infile.rsplit('.')[0]
    infile = args.infile
    if ".bin" not in outfile.lower(): outfile = outfile + ".bin"
    if ".bas" not in infile.lower():  infile = infile + ".bas"
    opts = AbascOptions(infile, outfile)
    opts.optlevel = args.O if args.O in [0,1,2] else 2
    opts.warninglevel = args.W if args.W in [0,1,2,3] else WL.ALL
    opts.debug = args.debug
    opts.startaddr = args.start
    opts.dataaddr = args.data
    opts.verbose = args.verbose
    opts.strsz = min(max(1, args.strchars), 254) + 1
    return opts

def clear(srcfile: str) -> None:
    files: list[str] = [
        str(pathlib.Path(srcfile).with_suffix('.bpp')),
        str(pathlib.Path(srcfile).with_suffix('.lex')),
        str(pathlib.Path(srcfile).with_suffix('.ast')),
        str(pathlib.Path(srcfile).with_suffix('.sym'))
    ]
    for f in files:
        if os.path.exists(f):
            os.remove(f)

def readsourcefile(source: str) -> str:
    with open(source, "r", encoding="utf-8") as fd:
        return fd.read()

def preprocess(infile: str, content: str, verbose: bool) -> tuple[list[CodeLine], str]:
    pp = LocBasPreprocessor()
    codelines, code = pp.preprocess(infile, content, 10)
    if verbose:
        ppfile = str(pathlib.Path(infile).with_suffix('.bpp'))
        pp.save_output(ppfile, code)
    return (codelines, code)

def lexpass(infile: str, code: str, verbose: bool) -> list[Token]:
    lx = LocBasLexer(code)
    print("Parsing source files...")
    lexjson, tokens = lx.tokens_json()
    if verbose:
        lexfile: str = str(pathlib.Path(infile).with_suffix('.lex'))
        with open(lexfile, "w", encoding="utf-8") as fd:
            fd.write(lexjson)
    return tokens

def parse(infile: str, codelines: list[CodeLine], tokens: list[Token], verbose: bool, wlevel: WL) -> tuple[AST.Program, SymTable]:
    parser = LocBasParser(codelines, tokens, wlevel)
    ast, symtable = parser.parse_program()
    if verbose:
        astjson = ast.to_json()
        astfile: str = str(pathlib.Path(infile).with_suffix('.ast'))
        with open(astfile, "w") as fd:
            fd.write(json.dumps(astjson, indent=4))
        symfile: str = str(pathlib.Path(infile).with_suffix('.sym'))
        symjson = symsto_json(symtable.syms)
        with open(symfile, "w", encoding="utf-8") as fd:
            fd.write(json.dumps(symjson, indent=4))
    return (ast, symtable)

def emit(codelines: list[CodeLine], ast:AST.Program, symtable: SymTable, opts: AbascOptions) -> tuple[str,int]:
    emitter = CPCEmitter(codelines, ast, symtable)
    emitter.cfgset_wlevel(opts.warninglevel)
    emitter.cfgset_verbose(opts.verbose)
    emitter.cfgset_startaddr(opts.startaddr)
    emitter.cfgset_dataaddr(opts.dataaddr)
    emitter.cfgset_tmpstrsz(opts.strsz)
    return emitter.emit_program()
    
def assemble(infile: str, outfile: str, asmcode: str) -> None:
    asmfile: str = str(pathlib.Path(outfile).with_suffix('.asm'))
    with open(asmfile, "w", encoding="utf-8") as fd:
        fd.write(asmcode)
    # library path for read 'asmfile' directive
    # we add the src/lib directory and also
    # the path to the BAS source file because the output ASM
    # file may be placed in a different directory.
    basepath = os.path.dirname(os.path.abspath(__file__))
    libpaths = [
        os.path.join(basepath, "lib"),
        os.path.join(os.path.dirname(infile))
    ]
    ABASM.assemble(asmfile, outfile, libpaths=libpaths)

def compile(opts: AbascOptions) -> int:
    clear(opts.infile)
    bascontent = readsourcefile(opts.infile)
    codelines, code = preprocess(opts.infile, bascontent, opts.verbose)
    tokens = lexpass(opts.infile, code, opts.verbose)
    ast, symtable = parse(opts.infile, codelines, tokens, opts.verbose, opts.warninglevel)
    optimizer = BasOptimizer(codelines)
    if opts.optlevel > 1:
        ast, symtable = optimizer.optimize_ast(ast, symtable)
    asmcode, heapused = emit(codelines, ast, symtable, opts)
    if opts.optlevel > 0:
        asmcode = optimizer.optimize_peephole(asmcode)
    assemble(opts.infile, opts.outfile, asmcode)
    if opts.verbose:
        ABASM.dump_assembledcode()
    return heapused
    

def main() -> None:
    start_t = time.process_time()
    opts: AbascOptions = process_args()
    try:
        heapused = compile(opts)
    except Exception as e:
        print(str(e))
        if opts.debug:
            print(traceback.format_exc())
        sys.exit(1)
    print(f"Done in {time.process_time()-start_t:.2f} seconds ({heapused} bytes of heap memory used)")
    sys.exit(0)

if __name__ == "__main__":
    main()
    