"""
Preprocesses an ASCII BAS input file to insert other BASIC files

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
import sys
import os
import argparse
from dataclasses import dataclass
from baserror import BasError
from baslex import LocBasLexer, TokenType

@dataclass
class CodeLine:
    source: str
    line: int
    code: str

class LocBasPreprocessor:

    def _raise_error(self, ecode: int, info: str, srcfile: str = "", line: int = -1, code: str= "") -> None:
        raise BasError(
            ecode = ecode,
            source = srcfile,
            info = info,
            code = code,
            line = line
        )

    def _insert_file(self, basedir, line: int, code: str, lines: list[CodeLine]) -> list[CodeLine]:
        parser = LocBasLexer(code)
        tokens = list(parser.tokens())
        for i,t in enumerate(tokens):
            if t.type == TokenType.KEYWORD and t.lexeme=="CHAIN MERGE":
                if tokens[i+1].type != TokenType.STRING:
                    self._raise_error(
                        5,
                        f"CHAIN MERGE file must appear between double quotes",
                        os.path.basename(lines[line].source),
                        lines[line].line,
                        lines[line].code
                    )
                infile = os.path.join(basedir, tokens[i+1].value) # type: ignore [arg-type]
                if not os.path.exists(infile):
                    # may be a library
                    infile = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "lib",
                        tokens[i+1].value # type: ignore [arg-type]
                    )
                try:
                    with open(infile, 'r') as f:
                        filecontent = f.read()
                        newlines, _ = self.ascodelines(infile, filecontent)
                        lines = lines[0:line+1] + newlines + lines[line+1:]
                except IOError:
                    self._raise_error(
                        25,
                        f"cannot access {tokens[i+1].value}",
                        lines[line].source,
                        lines[line].line,
                        lines[line].code
                    )
        return lines
        

    def extract_linenum(self, line: str) -> int | None:
        if len(line) > 0:
            numend = 0
            while line[numend].isdigit(): numend += 1
            if numend != 0:
                return int(line[0:numend])
        return None

    def preprocess(self, inputfile: str, code: str, increment: int = 10) -> tuple[list[CodeLine],str]:
        print("Preprocessing source files...")
        srclines, _ = self.ascodelines(inputfile, code)
        srcline = 0
        autonum = 0
        lastnum = 0
        outlines: list[CodeLine] = []
        while srcline < len(srclines):
            codeline = srclines[srcline]
            line = codeline.code.strip()
            compactstr = line.replace(' ', "").upper()
            if "CHAINMERGE" in compactstr:
                # insert content from another BAS file
                basedir = os.path.dirname(inputfile)
                srclines = self._insert_file(basedir, srcline, line, srclines)
            elif line != "":
                num = self.extract_linenum(line)
                if num is None:
                    autonum = autonum + increment
                    line = str(autonum) + ' ' + line
                    lastnum = autonum
                else:
                    if num < lastnum:
                        self._raise_error(
                            ecode=2,
                            info=f"explicit line number {num} is under last auto value {lastnum}",
                            line=srcline+1,
                            srcfile=inputfile)
                    lastnum = num
                    autonum = num + increment
                    
                outlines.append(CodeLine(codeline.source, codeline.line, line))
                
            srcline = srcline + 1
        finalcode = "\n".join([c.code for c in outlines]) + '\n'
        return outlines, finalcode
    
    def preprocess_file(self, inputf: str, lineinc: int) -> tuple[list[CodeLine], str]:
        if not os.path.isfile(inputf):
            self._raise_error(25, info = f"{inputf} doesn't exist")
        if lineinc < 1:
            self._raise_error(5, info="Line increments must be equal or greater than 1")
        try:
            with open(inputf, 'r') as f:
                code = f.read()
        except IOError:
            self._raise_error(25, f"Couldn't read from file {inputf}")
        output, finalcode = self.preprocess(inputf, code, lineinc)
        if len(output) == 0:
            self._raise_error(25, f"{inputf} seems empty")
        return output, finalcode

    def ascodelines(self, inputfile: str, code: str) -> tuple[list[CodeLine],str]:
        lines: list[str] = code.replace('\r\n', '\n').replace('\r','\n').split('\n')
        codelines = [CodeLine(inputfile, i+1, line) for i, line in enumerate(lines)]
        finalcode = "\n".join([c.code for c in codelines]) + '\n'
        return codelines, finalcode

    def save_output(self, output: str, code: str) -> None:
        try:
            with open(output, 'w') as f:
                f.write(code)
        except IOError:
            self._raise_error(25, info=f"couldn't write file {output}")

def process_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='baspp.py',
        description="""
        Utility to parser a pseudo Locomotive .BAS file adding line numbers.
        This utility also removes lines that start with ' symbol and strips spaces at the 
        beginning and the end of each line. For example, baspp.py MYFILE.BAS CPCFILE.BAS --inc=10
        will generate CPCFILE.BAS with lines going 10 by 10.
       """
    )
    parser.add_argument('infile', help="Text file with pseudo Locomotive Basic code.")
    parser.add_argument('outfile', help="Resulting Locomotive Basic code after processing the input file.")
    parser.add_argument('--inc', type=int, default=10, help='Line increment used to generate the output file. By defaul is 10.')
    args = parser.parse_args()
    return args

def main() -> None:
    args = process_args()
    try:
        pp = LocBasPreprocessor()
        _, code = pp.preprocess_file(args.infile, args.inc)
        pp.save_output(args.outfile, code)
        sys.exit(0)
    except Exception as e:
        print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()