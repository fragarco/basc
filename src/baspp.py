"""
Preprocesses an ASCII BAS input file to add line numbers, remove lines starting with ',
removes tabs and head/tail spaces, inserts other BASIC files and replace labels 
(strings starting with ::) with the corresponding line numbers in GOSUB, GOTO
and IF sentences.

Code:

' Simple example
::main
    print "Hello World!"
    goto ::main

Will be translated to:

10 print "Hello World!"
20 goto 10

It is possible to insert code from other BAS files using the reserved keyword
INCBAS, for example:

' Simple example
incbas "myrutines.bas"
::main
    print "Hello World!"
    ' calling a gosub section defined in myrutines through a label
    gosub ::myrutine_01

"""

import sys
import os
import re
import argparse


class BASPreprocessorError(Exception):
    """
    Raised when procesing a file and its format is not the expected one.
    """
    def __init__(self, message, line = -1):
        self.message = message
        self.line = line

    def __str__(self):
        if self.line != -1:
            return "[baspp] Error in line %d: %s" % (self.line, self.message)
        else:
            return "[baspp] Error: %s" % self.message
    
class BASPreprocessor:

    def _insert_file(self, iline, line, lines):
        relpath = re.search(r'(?<=["\'])(.*?)(?=["\'])', line)
        if relpath == None:
            raise BASPreprocessorError("%s\nIncluded files must be specified between double quotes '" % infile)
        infile = os.path.join(os.getcwd(), relpath.group(0))
        try:
            print("[baspp] Including", infile)
            with open(infile, 'r') as f:
                newlines = f.readlines()
                return lines[0:iline+1] + newlines + lines[iline+1:]
        except IOError:
            raise BASPreprocessorError("couldn't read included file %s" % infile)

    def _replace_labels(self, code, labels):
        output = []
        label_pattern = re.compile("(::[a-zA-Z0-9_-]*)")
        for _, l in code:
            toreplace = label_pattern.findall(l)
            for label in toreplace:
                ulabel = label.upper()
                if ulabel in labels:
                    l = l.replace(label, labels[ulabel])
                else:
                    raise BASPreprocessorError("unknown label %s"%(l))
            output.append(l + "\n")
        return output

    def _parse_input(self, inputfile, increment):
        lines = []
        labels = {}
        linenum = increment
        try:
            with open(inputfile, 'r') as f:
                filelines = f.readlines()
                iline = 0
                while iline < len(filelines):
                    line = filelines[iline].strip()
                    upline = line.upper()
                    if len(line) > 0 and line[0] != "'" and upline[0:4] != "REM ":
                        if "INCBAS " == upline[0:7]:
                            # insert content from another BAS file
                            filelines = self._insert_file(iline, line, filelines)
                            iline = iline + 1
                            continue 
                        elif line[0:2] == '::':
                            # label that can be used by GOSUB, GOTO or IF
                            if upline in labels:
                                raise BASPreprocessorError("multiple definitions of label %s" % (line))
                            labels[upline] = str(linenum)
                        else:
                            # regular line
                            line = str(linenum) + ' ' + line
                            lines.append((iline + 1, line))
                            linenum = linenum + increment
                    iline = iline + 1
            return lines, labels
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
        
        code, labels = self._parse_input(input, lineinc)
        if len(code) == 0:
            raise BASPreprocessorError("input file %s couldn't be read or accessed" % input)

        return self._replace_labels(code, labels)

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