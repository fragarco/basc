"""
Preprocesses an ASCII BAS input file to insert other BASIC files
"""

import sys
import os
import re
import argparse


class BASPreprocessorError(Exception):
    """
    Raised when procesing a file and its format is not the expected one.
    """
    def __init__(self, message, file = "", line = -1):
        self.message = message
        self.line = line
        self.file = file

    def __str__(self):
        if self.line != -1:
            return "[baspp] Error: %s\n\tfile %s line %d" % (self.message, self.file, self.line)
        else:
            return "[baspp] Error: %s" % self.message
    
class BASPreprocessor:

    def _insert_file(self, iline, line, lines):
        relpath = re.search(r'(?<=")(.*)(?=")', line)
        if relpath == None:
            raise BASPreprocessorError(
                "the file to be included in '%s' must be specified between double quotes" % line,
                lines[iline][0],
                lines[iline][1]
            )
        if ":" in line.replace(relpath.group(0), ''):
            # colon outside of quotes
            raise BASPreprocessorError(
                "lines with INCBAS keyword cannot include multiple commands symbol ':'",
                lines[iline][0],
                lines[iline][1]
            )
        infile = os.path.join(os.getcwd(), relpath.group(0))
        try:
            print("[baspp] Including", infile)
            with open(infile, 'r') as f:
                filecontent = f.readlines()
                newlines = [(infile, i, line) for i, line in enumerate(filecontent)]
                return lines[0:iline+1] + newlines + lines[iline+1:]
        except IOError:
            raise BASPreprocessorError(
                "couldn't read included file %s" % relpath.group(0),
                lines[iline][0],
                lines[iline][1]
            )

    def _parse_input(self, inputfile, increment):
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
                    else:
                        line = str(autonum) + ' ' + line
                        outlines.append((filename, fileline, line + '\n'))
                        autonum = autonum + increment
                    srcline = srcline + 1
            return outlines
        except IOError:
            raise BASPreprocessorError("couldn't read input file %s" % input)

    def save_output(self, output, code):
        try:
            with open(output, 'w') as f:
                f.writelines(code)
            print("[baspp] File", output, "has been generated")
            return True
        except IOError:
            raise BASPreprocessorError("couldn't write file %s" % output)

    def preprocess(self, input, lineinc):
        if not os.path.isfile(input):
            raise BASPreprocessorError("couldn't access input file %s" % input)

        if lineinc < 1:
            raise BASPreprocessorError("line increments must be a number equal or greater than 1")
        
        code = self._parse_input(input, lineinc)
        if len(code) == 0:
            raise BASPreprocessorError("input file %s is empty or cannot be read" % input)
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

def main():
    args = process_args()
    try:
        pp = BASPreprocessor()
        code = pp.preprocess(args.infile, args.inc)
        sys.exit(pp.save_output(args.outfile, code))
    except Exception as e:
        print(str(e))
    

if __name__ == "__main__":
    main()