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

import sys
import argparse
import baspp
import baslex
import basparse
import basemit
import basm

def process_args():
    parser = argparse.ArgumentParser(
        prog='basc.py',
        description='A Locomotive BASIC compiler for the Amstrad CPC'
    )
    parser.add_argument('infile', help="BAS file with pseudo Locomotive Basic code.")
    parser.add_argument('-o', '--out', help="Target file name without extension. If missing, <infile> name will be used.")
    args = parser.parse_args()
    return args

def main():
    args = process_args()
    if args.out == None:
        args.out = args.infile.rsplit('.')[0]
    try:
        pp = baspp.BASPreprocessor()
        code = pp.preprocess(args.infile, 10)
        pp.save_output(args.out + '.bpp', [c for _, _, c in code])
        
        lexer = baslex.BASLexer(code)
        emitter = basemit.ASMEmitter(args.out + '.asm')
        parser = basparse.BASParser(lexer, emitter)
        parser.parse()
        asmfile = emitter.save_output()
        basm.assemble(asmfile)
    except Exception as e:
        print(str(e))

if __name__ == "__main__":
    main()
