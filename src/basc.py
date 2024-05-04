import sys
import argparse
import baspp
import baslex
import basparse
import basemit

"""
def main():
    print("Teeny Tiny Compiler")

    if len(sys.argv) != 2:
        sys.exit("Error: Compiler needs source file as argument.")
    with open(sys.argv[1], 'r') as inputFile:
        source = inputFile.read()

    # Initialize the lexer, emitter, and parser.
    lexer = Lexer(source)
    emitter = Emitter("out.c")
    parser = Parser(lexer, emitter)

    parser.program() # Start the parser.
    emitter.writeFile() # Write the output to file.
    print("Compiling completed.")
"""

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
        emitter = basemit.BASEmitter(args.out + '.asm')
        parser = basparse.BASParser(lexer, emitter)
        parser.parse()
        emitter.save_output()
    except Exception as e:
        print(str(e))

if __name__ == "__main__":
    main()
