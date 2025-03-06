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

__author__='Javier "Dwayne Hicks" Garcia'
__version__='0.0dev'

import argparse
import baspp
import baslex
import basparse
import basemit
import basz80
import abasm

def process_args():
    parser = argparse.ArgumentParser(
        prog='basc.py',
        description='A Locomotive BASIC compiler for the Amstrad CPC'
    )
    parser.add_argument('infile', help="BAS file with pseudo Locomotive Basic code.")
    parser.add_argument('-o', '--out', help="Target file name without extension. If missing, <infile> name will be used.")
    parser.add_argument('--verbose', action='store_true', help="Prints extra information during the compilation process.")
    parser.add_argument('-v', '--version', action='version', version=f' Basc (Locomotive BASIC Compiler) Version {__version__}', help = "Shows program's version and exits")

    args = parser.parse_args()
    return args

def main() -> None:
    args = process_args()
    if args.out == None:
        args.out = args.infile.rsplit('.')[0]

    pp = baspp.BASPreprocessor()
    code = pp.preprocess(args.infile, 10)
    pp.save_output(args.out + '.bpp', [c for _, _, c in code])
    
    lexer = baslex.BASLexer(code)
    emitter = basemit.SMEmitter()
    parser = basparse.BASParser(lexer, emitter, args.verbose)
    parser.parse()
    
    if args.verbose:
        # InteRmediate Code
        with open(args.out + '.irc', 'w') as fo:
            fo.writelines([f"{op}({param})\n" for op, param, _ in emitter.code])

    asmout = args.out + '.asm'
    backend = basz80.Z80Backend()
    backend.save_output(asmout, emitter.code, parser.symbols)
    abasm.create_opdict()
    abasm.assemble(asmout)


if __name__ == "__main__":
    main()
