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

import sys
import os
import re
import argparse
from typing import List, Any, Tuple

class BASPreprocessor:

    def abort(self, message: str, file: str = "", iline: int = -1, sline: str= "") -> None:
        if file == "":
            print(f"Fatal error: {message}")
        else:
            print(f"Fatal error in {file}:{iline}: {sline.strip()} -> {message}")
        sys.exit(1)

    def _insert_file(self, iline: int, line: str, lines: List[Tuple[str, int, str]]) -> Any:
        relpath = re.search(r'(?<=")(.*)(?=")', line)
        if relpath is None:
            self.abort(
                f"the file to be included in '{line}' must be specified between double quotes",
                lines[iline][0],
                lines[iline][1],
                lines[iline][2]
            )
        else:
            if ":" in line.replace(relpath.group(0), ''):
                # colon outside of quotes
                self.abort(
                    "lines with INCBAS keyword cannot include other commands in the same line",
                    lines[iline][0],
                    lines[iline][1],
                    lines[iline][2]
                )
            infile = os.path.join(os.getcwd(), relpath.group(0))
            try:
                print("Including BAS file", infile)
                with open(infile, 'r') as f:
                    filecontent = f.readlines()
                    newlines = [(infile, i, line) for i, line in enumerate(filecontent)]
                    return lines[0:iline+1] + newlines + lines[iline+1:]
            except IOError:
                self.abort(
                    f"cannot read included file {relpath.group(0)}",
                    lines[iline][0],
                    lines[iline][1],
                    lines[iline][2]
                )

    def _parse_input(self, inputfile: str, increment: int) -> Any:
        outlines = []
        autonum = increment
        try:
            with open(inputfile, 'r') as f:
                filecontent = f.readlines()
                srclines = [(inputfile, i+1, line) for i, line in enumerate(filecontent)]
                srcline = 0
                while srcline < len(srclines):
                    filename, fileline, line = srclines[srcline]
                    line = line.strip()
                    if "INCBAS " == line[0:7].upper():
                        # insert content from another BAS file
                        srclines = self._insert_file(srcline, line, srclines)
                        srcline = srcline + 1
                    elif line != "":
                        line = str(autonum) + ' ' + line
                        outlines.append((filename, fileline, line + '\n'))
                        autonum = autonum + increment
                    srcline = srcline + 1
            return outlines
        except IOError:
            self.abort(f"couldn't read input file {input}")

    def save_output(self, output: str, code: List[str]) -> Any:
        try:
            with open(output, 'w') as f:
                f.writelines(code)
            print(f"Writting preprocessed file {output}")
            return True
        except IOError:
            self.abort(f"couldn't write file {output}")

    def preprocess(self, input: str, lineinc: int) -> List[Tuple[str, int, str]]:
        if not os.path.isfile(input):
            self.abort("couldn't access input file {input}")

        if lineinc < 1:
            self.abort("line increments must be a number equal or greater than 1")
        
        code = self._parse_input(input, lineinc)
        if len(code) == 0:
            self.abort(f"input file {input} is empty or cannot be read")
        return code

def process_args():
    parser = argparse.ArgumentParser(
        prog='baspp.py',
        description="""
        Utility to parser a pseudo Locomotive .BAS file adding line numbers and replacing
        ::label by equivalent line numbers in GOTO, GOSUB and IF staments.
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
        pp = BASPreprocessor()
        code = pp.preprocess(args.infile, args.inc)
        sys.exit(pp.save_output(args.outfile, [c for _, _, c in code]))
    except Exception as e:
        print(str(e))
    

if __name__ == "__main__":
    main()