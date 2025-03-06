#!/usr/bin/env python

"""
BASM.PY by Javier Garcia

BASM is a Z80 assembler focused on the Amstrad CPC. It's based on pyz80,
originally crafted by Andrew Collier and later on modified by Simon Owen

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
__version__='1.2'

import sys, os
import re
import argparse
import inspect

IFSTATE_DISABLED = 0 # assemble all encounted code
IFSTATE_ASSEMBLE = 1 # assemble this code, but stop at ELSE or ELSEIF
IFSTATE_DISCART  = 2 # do not assemble this code, but might start at ELSE or ELSEIF
IFSTATE_FIND_END = 3 # do not assemble any code until ENDIF

WSTATE_DISABLED = 0  # assemble all encounted code
WSTATE_ASSEMBLE = 1  # assemble code inside WHILE body
WSTATE_FIND_END = 2  # do not assemble code inside WHILE body
WSTATE_LOOP     = 3  # go back to WHILE condition

RSTATE_DISABLED = 0  # assemble all encounted code
RSTATE_ASSEMBLE = 1  # assemble code inside REPEAT body
RSTATE_FIND_END = 2  # do not assemble code inside REPEAT body
RSTATE_LOOP     = 3  # go back to REPEAT condition

NO_REG = -1
REG_B = 0
REG_C = 1
REG_D = 2
REG_E = 3
REG_H = 4
REG_L = 5
REG_IND = 6 # Indirect use of registers (HL) (IX) (IY)
REG_A = 7
REG_I = 8
REG_R = 9
REG_IXH = 10
REG_IXL = 11
REG_IYH = 12
REG_IYL = 13

REG_SINGLES = {
    'B': REG_B,
    'C': REG_C,
    'D': REG_D,
    'E': REG_E,
    'H': REG_H,
    'L': REG_L,
    'A': REG_A,
    'I': REG_I,
    'R': REG_R,
    'IXH': REG_IXH,
    'IXL': REG_IXL,
    'IYH': REG_IYH,
    'IYL': REG_IYL
}

REG_BC = 0
REG_DE = 1
REG_HL = 2
REG_SP = 3
REG_IX = 2
REG_IY = 2
REG_AF = 5
REG_AFA = 4 # AF'

REG_DOUBLES = {
    "BC": ([], REG_BC),
    "DE": ([], REG_DE),
    "HL": ([], REG_HL),
    "SP": ([], REG_SP),
    "IX": ([0xdd], REG_IX),
    "IY": ([0xfd], REG_IY),
    "AF": ([], REG_AF),
    "AF'": ([], REG_AFA)
}

class AsmMacro:
    def __init__(self, name, argv):
        self.name = name
        self.argv = []
        for arg in argv:
            self.argv.append(arg.strip())
        self.code = []

class AsmContext:
    def __init__(self):
        self.reset()
        self.verbose = False
        self.registernames = [
            "A", "F", "B", "C", "D", "E", "H", "L", "I", "R",
            "IXL", "IXH", "IYL", "IYH", "AF", "BC", "DE", "HL",
            "SP", "IX", "IY", "AF'"
        ]

    def reset(self):
        self.outputfile = ""
        self.listingfile = None
        self.origin = 0x4000
        self.limit  = 65536
        self.modulename = ""
        self.modules = []
        self.include_stack = []
        self.symboltable = {}
        self.lettable = {}
        self.symusetable = {}
        self.memory = bytearray(0x00 for i in range(0,0xFFFF))
        self.memory_high = 0
        self.memory_low = 0xFFFF
        self.machine_code = bytearray()
        self.ifstack = []
        self.ifstate = IFSTATE_DISABLED
        self.whileline = None
        self.whilestate= WSTATE_DISABLED
        self.repeatloop = None
        self.repeatstate = RSTATE_DISABLED
        self.currentfile = ""
        self.currentline = ""
        self.currentinst = ""
        self.linenumber = 0
        self.lstcode = ""
        self.macros = {}
        self.macros_stack = []
        self.macros_applied = 0
        self.defining_macro = None
        self.applying_macro = None
        self.list_instruction = True
    
    def parse_logic_expr(self, expr):
        """
        Resolves an expression that can be reduced to 0 = FALSE or !0 = TRUE.
        """
        values = re.findall(r'\w+', expr)
        for i in range(0, len(values)):
            values[i] = g_context.parse_expression(values[i])
        logic = re.findall(r'[<|>|=|<=|>=|!=|==]', expr)
        if len(logic) and logic[0] == '=': logic[0] = "=="

        if len(values) == 1: return values[0]
        if len(values) == 2:
            operation = "%d %s %d" % (values[0], logic[0], values[1])
            return eval(operation)
        abort("evaluating logical expression " + expr)
       
    def parse_expression(self, arg, signed=0, byte=0, word=0, allowundef=0):
        """
        Resolves a numeric expression that can be reduced to an integer value.
        To allow using symbols in expressions that are defined later on the code, the
        call can be made using allowundef=1 which will delay the final resolution to
        the second pass.
        WARNING: Maxam is supposed to evaluate operators from left to right (no operator
        precedence) here we do not do that, so this is a departure from Maxam.
        """
        if ',' in arg:
            abort("erroneous comma in expression " + arg)

        # convert single characters in quotes to integer values
        matches = re.findall(r'"(.)"', arg)
        for match in matches:
            arg = arg.replace(f'"{match}"', str(ord(match)))
        # hex literals start with & or # so convert them to Python 0x
        matches = re.findall(r'(&|#)([0-9a-fA-F]+\b)', arg)
        for (sym, expr) in matches:
            arg = arg.replace(sym+expr, '0x'+expr)
        # bin literals start with % so convert hem to Python 0b
        arg = arg.replace('%', '0b') 

        arg = arg.replace('@', '(' + str(self.origin) + ')') # storage location, next address
        arg = arg.replace('$', '(' + str(self.origin) + ')') # storage location, next address
        arg = arg.replace(' AND ', '&') # Maxam AND bitwise operator
        arg = arg.replace(' OR ', '|') # Maxam OR bitwise operator
        arg = arg.replace(' XOR ', '^') # Maxam XOR bitwise operator
        arg = arg.replace(' MOD ', '%') # Maxam syntax for modulus
        arg = arg.replace('/', '//') # Maxam div is integer which in Python is done with //

        # fix capitalized hex or binary Python symbol
        # don't do these except at the start of a token
        arg = re.sub(r'\b0X', '0x', arg) 
        arg = re.sub(r'\b0B', '0b', arg)

        # if the argument still contains letters at this point,
        # it's a symbol which needs to be replaced
        testsymbol=''
        argcopy = ''
        inquotes = False

        for c in arg + " ":
            if c.isalnum() or c in '"_.!' or inquotes:
                testsymbol += c
                if c == '"':
                    inquotes = not inquotes
            else:
                if testsymbol != '':
                    if not testsymbol[0].isdigit():
                        result = self.get_symbol(testsymbol)
                        if result != None:
                            testsymbol = str(result)
                        elif testsymbol[0] == '"' and testsymbol[-1]=='"':
                            # string literal used in some expressions
                            pass
                        else:
                            errormsg = f"symbol {testsymbol} is undefined"
                            if testsymbol.upper() in self.registernames:
                                errormsg = f"unexpected register {testsymbol}"
                            elif allowundef != 0:
                                # Allow undefined symbols if undefsym=1
                                return None
                            abort(errormsg)

                    elif testsymbol[0] == '0' and len(testsymbol) > 2 and testsymbol[1] == 'b':
                        # binary literal
                        literal = 0
                        for digit in testsymbol[2:]:
                            literal *= 2
                            if digit == '1':
                                literal += 1
                            elif digit != '0':
                                abort("Invalid binary digit '" + digit + "'")
                        testsymbol = str(literal)

                    elif testsymbol[0]=='0' and len(testsymbol)>1 and testsymbol[1]!='x':
                        # literals with leading zero would be treated as octal,
                        decimal = testsymbol
                        while decimal[0] == '0' and len(decimal) > 1:
                            decimal = decimal[1:]
                        testsymbol = decimal

                    argcopy += testsymbol
                    testsymbol = ''
                argcopy += c

        try:
            narg = int(eval(argcopy))
        except Exception:
            abort("syntax error in expression")

        if not signed:
            if byte:
                if narg < -128 or narg > 255:
                    warning ("unsigned byte value truncated from " + str(narg))
                narg %= 256
            elif word:
                if narg < -32768 or narg > 65535:
                    warning ("unsigned word value truncated from " + str(narg))
                narg %= 65536
        return narg

    def set_symbol(self, sym, value, is_label=False, is_let=False, type='label'):
        orgsym = sym = sym.upper()
        if is_label:
            if sym[0] == "!":
                if self.applying_macro == None:
                    # module local label
                    sym = sym + '!' + self.modulename
                else:
                    # macro local label
                   sym = sym + str(self.macros_applied) + '!' + self.modulename
            elif sym[0] == '.':
                # In maxam labels can start with '.' to allow labels similar to opcodes
                # so we need to remove that .
                sym = sym[1:]
        elif is_let:
            self.lettable[sym] = value
        self.symboltable[sym] = (value, self.modulename)
        if self.verbose:
            print(f" adding {type} {orgsym} to the symbols table with values ({value}, {self.modulename})")

    def get_symbol(self, sym):
        sym = sym.upper()
        if sym[0] == '!':
            if self.applying_macro == None:
                #  module local label
                sym = sym + '!' + self.modulename
            else:
                sym = sym + str(self.macros_applied) + '!' + self.modulename
        if sym[0] == '.': sym = sym[1:]
        if sym in self.symboltable:
            self.symusetable[sym] = g_context.symusetable.get(sym, 0) + 1
            return self.symboltable[sym][0]
        return None

    def check_symbol(self, sym, type):
        try:
            if sym in g_context.registernames or "op_" + sym in g_opcode_functions:
                abort(f"{type} name {sym} matches a directive, opcode or registry name")
        except Exception as e:
            pass
            
    def process_label(self, p, label):
        if len(label.split()) > 1:
            abort("whitespaces are not allowed in label names")

        if label != "":
            if p == 1:
                self.check_symbol(label, type='label')
                self.set_symbol(label, self.origin, is_label = True, type='label')
            elif self.get_symbol(label) != self.origin:
                abort("label address differs from previous stored value")

    def process_macro(self, macro, args):
        argv = args.replace(' ', '').split(',')
        code = self.macros[macro].code
        params = self.macros[macro].argv
        macrocode = [f"_MACRO_ENTER_ {macro}"]
        for line in code:
            for i,arg in enumerate(argv):
                line = line.replace(params[i], arg)
            macrocode.append(line)
        macrocode.append(f"_MACRO_LEAVE_ {macro}")
        return macrocode

    def store(self, p, bytes):
        if p == 2:
            self.lstcode = ""
            mempos = self.origin
            for b in bytes:
                self.memory[mempos] = b
                self.lstcode = self.lstcode + "%02X " % (b)
                mempos = mempos + 1
            self.memory_low = min(self.memory_low, self.origin)
            self.memory_high = max(self.memory_high, mempos-1)
            if len(self.lstcode) > 17:
                self.lstcode = self.lstcode[0:15] + ".."

    def save_mapfile(self, filename):
        mapfile = os.path.splitext(filename)[0] + '.map'
        try:
            with open(mapfile, 'w') as f:
                f.write('# List of symbols in Python dictionary format\n')
                f.write('# Symbol: [address, total number of reads, file name]\n')
                f.write('{\n')
                for sym, (addr, modulename) in sorted(self.symboltable.items()):
                    if sym[0] != '!':
                        # Only write global symbols
                        used = 0 if sym not in self.symusetable else self.symusetable[sym]
                        f.write('\t"%s": [0x%04X, %d, "%s"],\n' % (sym, addr, used, modulename))
                f.write('}\n')
        except Exception as e:
            abort(f"Error trying to generate the file {filename}: " + str(e))

    def save_memory(self, filename, start, size):
        memory = bytearray()
        if size > 0:
            memory = self.memory[start:start+size]
        print("[abasm] output: %s [%04X:%04X (%d bytes)]" % (filename, start, start+size, size))
        try:
            with open(filename, 'wb') as fd:
                fd.write(memory)
        except Exception as e:
            abort(f"Error trying to generate the file {filename}: " + str(e))

    def write_listinfo(self, line):
        if self.listingfile == None:
            self.listingfile = open(os.path.splitext(self.outputfile)[0] + '.lst', "wt")
        self.listingfile.write(line + "\n")

    def save_binfile(self, filename):
        size = 0
        if self.memory_low < self.memory_high:
            # something has been assembled
            size = self.memory_high - self.memory_low + 1
            self.save_memory(filename, self.memory_low, size)
            self.save_mapfile(filename)
        else:
            abort("EOF and nothing was assembled")

    def parse_instruction(self, line):
        # Lines must start by characters or underscord or '.'
        match = re.match(r'^(\.\w+|\!\w+|\w+)(.*)', line.strip())
        if not match:
            abort("in '" + line + "'. Valid literals must start with a letter, an underscord, '.' or '!' symbols")

        inst = match.group(1).upper().strip()
        args = match.group(2).strip()
        return inst, args

    def assemble_instruction(self, p, line):
        inst, args = self.parse_instruction(line)
        if self.defining_macro is not None and inst != "ENDM":
            self.defining_macro.code.append(line)
            return 0, []
        assemble = (self.ifstate < IFSTATE_DISCART) or inst in ("IF", "ELSE", "ELSEIF", "ENDIF")
        assemble = assemble and ((self.whilestate < WSTATE_FIND_END) or inst in ("WHILE", "WEND"))
        assemble = assemble and ((self.repeatstate < RSTATE_FIND_END) or inst in ("REPEAT", "REND"))
        self.list_instruction = assemble
        if assemble:
            if g_context.verbose and p == 2:
                print(f" line {self.linenumber}: assembling '{inst}' with args: '{args}'", end=' ')
            if "op_" + inst in g_opcode_functions:
                # check if we have a pointer to the op_XXXX func
                # not recognized opcodes or directives are labels in Maxam dialect BUT they
                # can go with opcodes separated by spaces in the same line 'loop jp loop'
                if g_context.verbose and p == 2: print("as an opcode")
                return g_opcode_functions["op_" + inst](p, args), []
            elif " EQU " in line.upper():
                params = line.upper().split(' EQU ')
                op_EQU(p, ','.join(params))
                if g_context.verbose and p == 2: print("as an EQU instruction")
            elif inst in self.macros:
                # Return the extra code generated by the macro
                if g_context.verbose and p == 2: print("as a macro call")
                self.list_instruction = False
                return 0, self.process_macro(inst, args)
            else:
                # must be a label
                if g_context.verbose and p == 2: print("as a label")
                self.process_label(p, inst)
                # MAXAM support the structure <label> <opcode> <operands>
                # without using the colon at the end of the label
                extra_statements = line.split(' ', 1)
                if len(extra_statements) > 1:
                    return self.assemble_instruction(p, extra_statements[1])
        return 0, []

    def read_srcfile(self, inputfile):
        try:
            fd = open(inputfile, 'r')
            content = fd.readlines()
            content.insert(0, '') # prepend blank so line numbers are 1-based
            fd.close()
            return content
        except Exception as e:
            print("[abasm]", str(e))
            abort("Couldn't open file '" + inputfile + "' for reading")

    @staticmethod
    def split_line(instr, sep):
        # Here we deal with splitting a text line by a separator symbol but
        # we ignore that symbol if it is between quoted colons
        result = []
        start = 0
        current = 0
        quoted = False
        while current < len(instr):
            if instr[current] == sep and not quoted:
                result.append(instr[start: current])
                start = current + 1
            elif instr[current] == '"':
                quoted = not quoted
            current = current + 1
        # add trail
        result.append(instr[start:])
        return result

    def get_statements(self, codeline):
        # remove comments
        codeline = codeline.strip().split(';')[0]
        # basic sanity checks
        statements = []
        index = 0
        # one line can have multiple instructions separated by :
        opcodes = self.split_line(codeline, ':')
        while index < len(opcodes):
            opcode = opcodes[index]
            opcode = opcode.strip()
            if opcode != "":
                # sanity check
                if opcode.count('"') % 2 != 0 or opcode.count("'") % 2 != 0:
                    abort("mismatched quotes")
                # label: equ <value> exception
                if (index+ 1) < len(opcodes) and 'EQU 'in opcodes[index+1].upper():
                    statements.append(opcode + ' ' + opcodes[index + 1])
                    index = index + 2
                    continue
                statements.append(opcode)
            index = index + 1
        return statements

    def set_module(self, inputfile):
        self.modulename = os.path.basename(inputfile).upper()
        if self.modulename in self.modules:
            abort(f"file {self.modulename} was already assembled")
        else:
            self.modules.append(self.modulename)

    def assembler_pass(self, p, inputfile):
        self.set_module(inputfile)
        self.currentfile = ""
        self.currentline = ""
        self.linenumber = 0
        srccode = self.read_srcfile(inputfile)

        while self.linenumber < len(srccode):
            self.currentline = srccode[self.linenumber].replace("\t", "  ")
            self.currentfile = inputfile + ":" + str(self.linenumber)   
            statements = self.get_statements(self.currentline)
            while len(statements) > 0:
                self.currentinst = statements.pop(0)
                # macro substitution can generate extra statements
                self.list_instruction = True
                incbytes, extracode = self.assemble_instruction(p, self.currentinst)
                if extracode:
                    statements = extracode + statements
                if p == 2 and self.list_instruction:
                    fname = os.path.basename(inputfile)[0:13]
                    lstout = "%-13s %06d  %04X  %-16s\t%s" % (fname, self.linenumber, self.origin, self.lstcode, self.currentinst)
                    self.lstcode = ""
                    self.write_listinfo(lstout)
                self.origin = self.origin + incbytes
                if self.origin > self.limit:
                    abort(f"memory full. Current limit is set to {self.limit}")
            if self.whilestate == WSTATE_LOOP:
                self.linenumber = self.whileline
            elif self.repeatstate == RSTATE_LOOP:
                self.linenumber = self.repeatloop[0]
            else:
                self.linenumber += 1

    def assemble(self, inputfile, outputfile, startaddr):
        print("[abasm] input: ", inputfile)
        for p in [1, 2]:
            self.origin = startaddr
            self.include_stack = []
            self.modules = []
            self.macros_stack = []
            self.macros_applied = 0
            self.assembler_pass(p, inputfile)

        if self.listingfile != None:
            self.listingfile.close()

        if len(self.ifstack) > 0:
            print("[abasm] Error: mismatched IF and ENDIF statements, too many IF")
            for item in self.ifstack:
                print(item[0])
            sys.exit(1)

        if self.whilestate != WSTATE_DISABLED:
            print("[abasm] Error: mismatched WHILE and WEND statements")
            sys.exit(1)

        if self.repeatstate != RSTATE_DISABLED:
            print("[abasm] Error: mismatched REPEAT and REND statements")
            sys.exit(1)

        if self.defining_macro is not None:
            print("[abasm] Error: missing ENDM directive for macro", self.defining_macro.name)
            sys.exit(1)

        self.save_binfile(outputfile)


g_context = AsmContext()
g_opcode_functions = {}

###########################################################################
# Error and warning reporting

def warning(message):
    print("[abasm]", os.path.basename(g_context.currentfile) + ':', 'warning:', message)
    print('\t', g_context.currentline.strip())

def abort(message):
    line1 = f"{os.path.basename(g_context.currentfile)}: error: {message}"
    code = g_context.currentline.strip()
    line2 = '' if code == '' else f"in '{code}'"
    if g_context.listingfile != None:
        g_context.listingfile.close()
    if __name__ == "__main__":
        print("[abasm]", line1)
        if line2 != '': print("\t", line2)
        sys.exit(1)
    else:
        raise RuntimeError(f"{line1} {line2}")


###########################################################################
# Refactored common code shared by several opcode implementations

def double(arg, allow_af_instead_of_sp=0, allow_af_alt=0, allow_index=1):
    """
    Decodes double registers BC, DE, HL, SP, IX, IY, AF and special AF'
    """
    rr = REG_DOUBLES.get(arg.strip().upper(), ([], NO_REG))
    if rr[1] == REG_SP and allow_af_instead_of_sp:
        rr = ([], NO_REG)
    if rr[1] == REG_AF:
        if allow_af_instead_of_sp:
            rr = ([], REG_SP)
        else:
            rr = ([], NO_REG)
    if rr[1] == REG_AFA and not allow_af_alt:
        rr = ([], NO_REG)

    if (rr[0] != []) and not allow_index:
        rr = ([], NO_REG)
    return (list(rr[0]), rr[1])

def single(p, arg, allow_i=0, allow_r=0, allow_index=1, allow_offset=1, allow_half=1):
    """
    Decodes single registers B, C, D, E, H, L, A and specials I, R, IXH, IXL, IYH, IYL
    or indirect access using registers (HL) (IX) (IY)
    """
    m = REG_SINGLES.get(arg.strip().upper(), NO_REG)
    prefix = []
    postfix = []
    if m == REG_I and not allow_i:
        m = NO_REG
    if m == REG_R and not allow_r:
        m = NO_REG

    if allow_half:
        if m == REG_IXH:
            prefix = [0xdd]
            m = REG_H
        if m == REG_IXL:
            prefix = [0xdd]
            m = REG_L
        if m == REG_IYH:
            prefix = [0xfd]
            m = REG_H
        if m == REG_IYL:
            prefix = [0xfd]
            m = REG_L
    else:
        if m >= REG_IXH and m <= REG_IYL:
            m = NO_REG

    if m == NO_REG and re.search(r"\A\s*\(\s*HL\s*\)\s*\Z", arg, re.IGNORECASE):
        m = REG_IND

    if m == NO_REG and allow_index:
        match = re.search(r"\A\s*\(\s*(I[XY])\s*\)\s*\Z", arg, re.IGNORECASE)
        if match:
            m = REG_IND
            prefix = [0xdd] if match.group(1).lower() == 'ix' else [0xfd]
            postfix = [0]

        elif allow_offset:
            match = re.search(r"\A\s*\(\s*(I[XY])\s*([+-].*)\s*\)\s*\Z", arg, re.IGNORECASE)
            if match:
                m = REG_IND
                prefix = [0xdd] if match.group(1).lower() == 'ix' else [0xfd]
                if p == 2:
                    offset = g_context.parse_expression(match.group(2), byte=1, signed=1)
                    if offset < -128 or offset > 127:
                        abort("invalid index offset: "+str(offset))
                    postfix = [(offset + 256) % 256]
                else:
                    postfix = [0]
    return prefix, m, postfix

def condition(arg):
    """ decodes condition nz, z, nc, c, po, pe, p, m """
    condition_mapping = {'NZ':0, 'Z':1, 'NC':2, 'C':3, 'PO':4, 'PE':5, 'P':6, 'M':7 }
    return condition_mapping.get(arg.upper(),-1)

def check_args(args, expected):
    if args == '':
        received = 0
    else:
        received = len(AsmContext.split_line(args, ','))
    if expected != received:
        abort("wrong number of arguments, expected "+str(expected)+" but received "+str(args))

def store_noargs_type(p, opargs, instr):
    check_args(opargs, 0)
    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def store_register_arg_type(p, opargs, offset, ninstr, step_per_register=1):
    check_args(opargs, 1)
    pre, r, post = single(p, opargs, allow_half=1)
    instr = pre
    if r == NO_REG:
        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", opargs)
        if match:
            abort("illegal indirection")

        instr.extend(ninstr)
        if p == 2:
            n = g_context.parse_expression(opargs, byte=1)
        else:
            n = 0
        instr.append(n)
    else:
        instr.append(offset + step_per_register * r)
    instr.extend(post)
    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def store_cbshifts_type(p, opargs, offset, step_per_register=1):
    args = opargs.split(',', 1)
    if len(args) == 2:
        # compound instruction of the form RLC B,(IX+c)
        _, r1, _ = single(p, args[0], allow_half=0, allow_index=0)
        pre2, r2, post2 = single(p, args[1], allow_half=0, allow_index=1)
        if r1 == NO_REG or r2 == NO_REG:
            abort("registers not recognized for compound instruction")
        if r1 == REG_IND:
            abort("(HL) not allowed as target of compound instruction")
        if len(pre2) == 0:
            abort("must use index register as operand of compound instruction")

        instr = pre2
        instr.extend([0xcb])
        instr.extend(post2)
        instr.append(offset + step_per_register * r1)
    else:
        check_args(opargs, 1)
        pre, r, post = single(p, opargs, allow_half=0)
        instr = pre
        instr.extend([0xcb])
        instr.extend(post)
        if r == NO_REG:
            abort("invalid argument")
        else:
            instr.append(offset + step_per_register * r)
    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def store_registerorpair_arg_type(p, opargs, rinstr, rrinstr, step_per_register=8, step_per_pair=16):
    check_args(opargs, 1)
    pre, r, post = single(p, opargs)
    if r == NO_REG:
        pre,rr = double(opargs)
        if rr == NO_REG:
            abort("Invalid argument")

        instr = pre
        instr.append(rrinstr + step_per_pair * rr)
    else:
        instr = pre
        instr.append(rinstr + step_per_register * r)
        instr.extend(post)
    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def store_add_type(p, opargs, rinstr, ninstr, rrinstr, step_per_register=1, step_per_pair=16):
    args = opargs.split(',', 1)
    r=-1
    if len(args) == 2:
        pre, r, post = single(p, args[0])
    if len(args) == 1 or r == REG_A:
        pre, r, post = single(p, args[-1])
        instr = pre
        if r == NO_REG:
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[-1])
            if match:
                abort("illegal indirection")
            instr.extend(ninstr)
            if p == 2:
                n = g_context.parse_expression (args[-1], byte=1)
            else:
                n = 0
            instr.append(n)
        else:
            instr.extend(rinstr)
            instr[-1] += step_per_register * r
        instr.extend(post)
    else:
        pre, rr1 = double(args[0])
        dummy, rr2 = double(args[1])

        if rr1 == rr2 and pre != dummy:
            abort("Can't mix index registers and HL")
        if len(rrinstr) > 1 and pre:
            abort(f"this instruction can't use index registers {args[0]} {pre} {rr1}")

        if len(args) != 2 or rr1 != REG_HL or rr2 == NO_REG:
            abort("invalid operands")
        instr = pre
        instr.extend(rrinstr)
        instr[-1] += step_per_pair * rr2

    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def store_bit_type(p, opargs, offset):
    check_args(opargs,2)
    arg1,arg2 = opargs.split(',',1)
    allowundef = 1 if p == 1 else 0
    b = g_context.parse_expression(arg1, allowundef)
    if b == None:
        b = 0  # lets wait until the second pass for missing symbols
    if b > 7 or b < 0:
        abort("argument out of range")
    pre, r, post = single(p, arg2, allow_half=0)
    if r == NO_REG:
        abort("Invalid argument")
    instr = pre
    instr.append(0xcb)
    instr.extend(post)
    instr.append(offset + r + 8*b)
    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def store_pushpop_type(p, opargs, offset):
    check_args(opargs,1)
    prefix, rr = double(opargs, allow_af_instead_of_sp=1)
    instr = prefix
    if rr == NO_REG:
        abort("Invalid argument")
    else:
        instr.append(offset + 16 * rr)
    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def store_jumpcall_type(p, opargs, offset, condoffset):
    args = opargs.split(',', 1)
    if len(args) == 1:
        instr = [offset]
    else:
        cond = condition(args[0])
        if cond == -1:
            abort("expected condition but received '" + opargs + "'")
        instr = [condoffset + 8 * cond]

    match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[-1])
    if match:
        abort("Illegal indirection")

    if p == 2:
        nn = g_context.parse_expression(args[-1], word=1)
        instr.extend([nn%256, nn//256])
        g_context.store(p, instr)
    return 3

###########################################################################
# directives and opcodes

def op_ORG(p, opargs):
    check_args(opargs, 1)
    # Not undefined symbols are allowed here
    g_context.origin = g_context.parse_expression(opargs, word=1)
    return 0

def op_SAVE(p, opargs):
    if p == 2:
        check_args(opargs, 3)
        fname, expr1, expr2 = opargs.split(',')
        fname = fname.replace('"', '')
        fname = fname.replace("'", '')
        start = g_context.parse_expression(expr1, word=1)
        size = g_context.parse_expression(expr2, word=1)
        g_context.save_memory(fname, start, size)
    return 0

def op_DUMP(p, opargs):
    # Not currently implemented. Maxam used it to write symbol information
    # ABASM outputs the MAP file instead
    warning ("directive DUMP found but ignored, Abasm uses MAP files instead")
    return 0

def op_BRK(p, opargs):
    # Not currently implemented. WinAPE uses it to set a breakpoint using RST &30
    # as MAXAM did back in the day
    warning ("directive BRK (breakpoint) found but ignored")
    return 0

def op_PRINT(p, opargs):
    if p == 2:
        text = []
        for expr in opargs.split(","):
            if expr.strip().startswith('"'):
                text.append(expr.strip().rstrip()[1:-1])
            else:
                a = g_context.parse_expression(expr, allowundef=1)
                if a != None:
                    text.append(str(a))
                else:
                    text.append("?")
        print("[abasm]", os.path.basename(g_context.currentfile) + ":", "PRINT ", ",".join(text))
    return 0

def op_EQU(p, opargs):
    check_args(opargs, 2)
    symbol, expr = opargs.split(',')
    symbol = symbol.strip()
    expr = expr.strip()
    if p == 1:
        v = g_context.parse_expression(expr, signed=1, allowundef=1)
        if v != None: g_context.set_symbol(symbol, v, type='alias')
    else:
        expr_result = g_context.parse_expression(expr, signed=1)
        existing = g_context.get_symbol(symbol)
        if existing == None:
            g_context.set_symbol(symbol, expr_result, type='alias')
        elif existing != expr_result:
                abort("Symbol " + symbol +
                      ": expected " + str(existing) +
                      " but calculated " + str(expr_result) +
                      ", has this symbol been used twice?")
    return 0

def op_ALIGN(p, opargs):
    args = opargs.replace(" ", "").split(",")
    if len(args) < 1:
        abort("ALIGN directive requieres at least one value")
    # Not undefined symbols are allowed in expressions for this
    # directive
    padding = 0 if len(args) == 1 else g_context.parse_expression(args[1])
    align = g_context.parse_expression(args[0])
    if align < 1:
        abort("invalid negative alignment")
    elif (align & (-align)) != align:
        abort("requested alignment is not a power of 2")
    s = (align - (g_context.origin % align)) % align
    g_context.store(p, [padding for i in range(0, s)])
    return s

def op_DS(p, opargs):
    return op_DEFS(p, opargs)

def op_DEFS(p, opargs):
    return op_RMEM(p, opargs)

def op_RMEM(p, opargs):
    check_args(opargs, 1)
    s = g_context.parse_expression(opargs)
    if s < 0:
        abort("Allocated invalid space < 0 bytes (" + str(s) + ")")
    g_context.store(p, [0 for i in range(0, s)])
    return s

def op_DW(p, opargs):
    return op_DEFW(p, opargs)

def op_DEFW(p, opargs):
    s = opargs.split(',')
    if p == 2:
        words = []
        for b in s:
            b = (g_context.parse_expression(b, word=1))
            words = words + [b%256, b//256]
        g_context.store(p, words)
    return 2 * len(s)

def op_DM(p, opargs):
    return op_DEFB(p, opargs)

def op_DB(p, opargs):
    return op_DEFB(p, opargs)

def op_DEFM(p, opargs):
   return op_DEFB(p, opargs)

def op_DEFB(p, opargs):
    args = AsmContext.split_line(opargs, ',')
    bytes = []
    for arg in args:
        texts = re.findall(r'"(.*?)"', arg)
        if len(texts) == 0: texts = re.findall(r"'(.*?)'", arg)
        if len(texts) > 0:
            # text string between "" or '', special case is '' which
            # produces an empty list but should write &00
            txtbytes = list(texts[0].encode('latin-1'))
            if len(txtbytes) == 0: txtbytes = [0]
            bytes = bytes + txtbytes
        else:
            byte = 0 if p == 1 else g_context.parse_expression(arg, byte=1)
            bytes.append(byte)
    if p == 2: g_context.store(p, bytes)
    return len(bytes)

def op_LET(p, opargs):
    args = opargs.replace(" ", "").upper().split("=")
    if len(args) != 2:
        abort("LET directive uses the format SYMBOL=VALUE")
    sym, val = args
    allowundef = 1 if p == 1 else 0
    val = g_context.parse_expression(val, allowundef)
    if val != None:
        g_context.set_symbol(sym, val, is_let=True, type='let')
    return 0

def op_READ(p, opargs):
    # WinAPE directive to include other assembly source code
    if g_context.whilestate != WSTATE_DISABLED or g_context.repeatstate != RSTATE_DISABLED:
        abort("READ is not allowed inside WHILE or REPEAT loops")

    if g_context.applying_macro != None:
        abort("READ is no allowed inside a MACRO code")

    if len(g_context.include_stack) > 5:
        abort("too deep READ tree")

    path = re.search(r'(?<=["\'])(.*?)(?=["\'])', opargs)
    if path == None:
        abort("wrong path specified in the READ directive")
    g_context.include_stack.append((g_context.currentfile, g_context.linenumber))
    filename = os.path.join(os.path.dirname(g_context.currentfile), path.group(0))
    if not os.path.exists(filename):
        abort("couldn't access to the file " + filename)
    if p == 1: print("[abasm] including", filename)
    g_context.assembler_pass(p, filename)
    g_context.currentfile, g_context.linenumber = g_context.include_stack.pop()
    return 0

def op_INCBIN(p, opargs):
    # WinAPE directive to include the content of a binary file
    # incbin "file", offset, size
    path = re.search(r'(?<=["\'])(.*?)(?=["\'])', opargs)
    if path == None:
        abort("wrong path specified in the INCBIN directive")
    filename = os.path.join(os.path.dirname(g_context.currentfile), path.group(0))
    if not os.path.exists(filename):
        abort("couldn't access to the file " + filename)
    args = opargs.split(',')
    offset = 0 if len(args) < 2 else g_context.parse_expression(args[1].strip())
    try:
        with open(filename, 'rb') as fd:
            content = fd.read()
        nbytes = len(content) - offset if len(args) < 3 else g_context.parse_expression(args[2].strip())
    except Exception as e:
        abort("cannot read the content of the binary file: " + str(e))
    content = content[offset: offset + nbytes]
    g_context.store(p, content)
    return len(content)

def op_WHILE(p, opargs):
    do = g_context.parse_expression(opargs)
    if do != 0:
        if g_context.whileline != None and g_context.whileline != g_context.linenumber:
            abort("nesting is not supported in WHILE loops")
        g_context.whileline = g_context.linenumber
        g_context.whilestate = WSTATE_ASSEMBLE
    else:
        g_context.whileline = None
        g_context.whilestate = WSTATE_FIND_END
    g_context.list_instruction = False
    return 0

def op_WEND(p, opargs):
    if g_context.whilestate == WSTATE_DISABLED:
        abort("unexpected WEND")
    elif g_context.whilestate == WSTATE_ASSEMBLE:
        g_context.whilestate = WSTATE_LOOP
    else:
        g_context.whilestate = WSTATE_DISABLED
    g_context.list_instruction = False
    return 0

def op_REPEAT(p, opargs):
    value = 0
    if g_context.repeatloop != None:
        line, value = g_context.repeatloop
        if line != g_context.linenumber:
            abort("nesting is not supported in REPEAT loops")
    else:
        value = g_context.parse_expression(opargs)

    if value > 0:
        g_context.repeatloop = (g_context.linenumber, value)
        g_context.repeatstate = RSTATE_ASSEMBLE
    else:
        g_context.repeatloop = None
        g_context.repeatstate = RSTATE_FIND_END
    g_context.list_instruction = False
    return 0

def op_REND(p, opargs):
    if g_context.repeatstate == RSTATE_DISABLED:
        abort("unexpected REND")
    elif g_context.repeatstate == RSTATE_ASSEMBLE:
        line, value = g_context.repeatloop
        value = value - 1
        g_context.repeatloop = (line, value)
        g_context.repeatstate = RSTATE_LOOP
    else:
        g_context.repeatstate = RSTATE_DISABLED
    g_context.list_instruction = False
    return 0

def op_LIMIT(p, opargs):
    check_args(opargs,1)
    if p == 2:
        g_context.limit = g_context.parse_expression(opargs)
    return 0

def op_ASSERT(p, opargs):
    check_args(opargs,1)
    if p == 2:
        value = g_context.parse_expression(opargs)
        if value == 0:
            abort("Assertion failed (" + opargs + ")")
    return 0

def op_STOP(p, opargs):
    abort("directive STOP found")

def op_NOP(p, opargs):
    return store_noargs_type(p, opargs, [0x00])

def op_RLCA(p, opargs):
    return store_noargs_type(p, opargs, [0x07])

def op_RRCA(p, opargs):
    return store_noargs_type(p, opargs, [0x0F])

def op_RLA(p, opargs):
    return store_noargs_type(p, opargs, [0x17])

def op_RRA(p, opargs):
    return store_noargs_type(p, opargs, [0x1F])

def op_DAA(p, opargs):
    return store_noargs_type(p, opargs, [0x27])

def op_CPL(p, opargs):
    return store_noargs_type(p, opargs, [0x2F])

def op_SCF(p, opargs):
    return store_noargs_type(p, opargs, [0x37])

def op_CCF(p, opargs):
    return store_noargs_type(p, opargs, [0x3F])

def op_HALT(p, opargs):
    return store_noargs_type(p, opargs, [0x76])

def op_DI(p, opargs):
    return store_noargs_type(p, opargs, [0xf3])

def op_EI(p, opargs):
    return store_noargs_type(p, opargs, [0xfb])

def op_EXX(p, opargs):
    return store_noargs_type(p, opargs, [0xd9])

def op_NEG(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0x44])

def op_RETN(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0x45])

def op_RETI(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0x4d])

def op_RRD(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0x67])

def op_RLD(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0x6F])

def op_LDI(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xa0])

def op_CPI(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xa1])

def op_INI(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xa2])

def op_OUTI(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xa3])

def op_LDD(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xa8])

def op_CPD(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xa9])

def op_IND(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xaa])

def op_OUTD(p,opargs):
    return store_noargs_type(p, opargs, [0xed, 0xab])

def op_LDIR(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xb0])

def op_CPIR(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xb1])

def op_INIR(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xb2])

def op_OTIR(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xb3])

def op_LDDR(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xb8])

def op_CPDR(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xb9])

def op_INDR(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xba])

def op_OTDR(p, opargs):
    return store_noargs_type(p, opargs, [0xed, 0xbb])

def store_store_cbshifts_type(p, opargs, offset, step_per_register=1):
    args = opargs.split(',', 1)
    if len(args) == 2:
        # compound instruction of the form RLC B,(IX+c)
        _, r1, _ = single(p, args[0], allow_half=0, allow_index=0)
        pre2, r2, post2 = single(p, args[1], allow_half=0, allow_index=1)
        if r1 == NO_REG or r2 == NO_REG:
            abort("registers not recognized for compound instruction")
        if r1 == REG_IND:
            abort("(HL) not allowed as target of compound instruction")
        if len(pre2) == 0:
            abort("must use index register as operand of compound instruction")

        instr=pre2
        instr.extend([0xcb])
        instr.extend(post2)
        instr.append(offset + step_per_register * r1)
    else:
        check_args(opargs, 1)
        pre, r, post = single(p, opargs, allow_half=0)
        instr = pre
        instr.extend([0xcb])
        instr.extend(post)
        if r == NO_REG:
            abort("invalid argument")
        else:
            instr.append(offset + step_per_register * r)
    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def op_RLC(p, opargs):
    return store_store_cbshifts_type(p, opargs, 0x00)

def op_RRC(p, opargs):
    return store_store_cbshifts_type(p, opargs, 0x08)

def op_RL(p, opargs):
    return store_store_cbshifts_type(p, opargs, 0x10)

def op_RR(p, opargs):
    return store_store_cbshifts_type(p, opargs, 0x18)

def op_SLA(p, opargs):
    return store_store_cbshifts_type(p, opargs, 0x20)

def op_SRA(p, opargs):
    return store_store_cbshifts_type(p, opargs, 0x28)

def op_SL1(p, opargs):
    return store_store_cbshifts_type(p, opargs, 0x30)

def op_SRL(p, opargs):
    return store_store_cbshifts_type(p, opargs, 0x38)

def op_SUB(p, opargs):
    # Z80 Aseembly language programming book lists SUB without register A
    # because always operates with the accumulator BUT WinAPE assembler seems
    # to use the aliases SUB A,r SUB A,n SUB A,(HL) SUB A,(IX + d) SUB A,(IY + d)
    # lets support that in case we get two parameters and issue a warning
    args = opargs.strip().split(',')
    if len(args) > 1:
        warning('invalid <SUB expr,expr> opcode. Assuming alias SUB A,expr')
        opargs = args[1]
    return store_register_arg_type(p, opargs, 0x90, [0xd6])

def op_AND(p, opargs):
    # Z80 Aseembly language programming book lists AND without register A
    # because always operates with the accumulator BUT WinAPE assembler seems
    # to use the aliases AND A,r AND A,n AND A,(HL) AND A,(IX + d) AND A,(IY + d)
    # lets support that in case we get two parameters and issue a warning
    args = opargs.strip().split(',')
    if len(args) > 1:
        warning('invalid <ADD expr,expr> opcode. Assuming alias ADD A,expr')
        opargs = args[1]
    return store_register_arg_type(p, opargs, 0xa0, [0xe6])

def op_XOR(p, opargs):
    return store_register_arg_type(p, opargs, 0xa8, [0xee])

def op_OR(p, opargs):
    # Z80 Aseembly language programming book lists OR without register A
    # because always operates with the accumulator BUT WinAPE assembler seems
    # to use the aliases OR A,r OR A,n OR A,(HL) OR A,(IX + d) OR A,(IY + d)
    # lets support that in case we get two parameters and issue a warning
    args = opargs.strip().split(',')
    if len(args) > 1:
        warning('invalid <OR expr,expr> opcode. Assuming alias OR A,expr')
        opargs = args[1]
    return store_register_arg_type(p, opargs, 0xb0, [0xf6])

def op_CP(p, opargs):
    # Z80 Aseembly language programming book lists CP without register A
    # because always operates with the accumulator BUT WinAPE assembler seems
    # to use the aliases CP A,r CP A,n CP A,(HL) CP A,(IX + d) CP A,(IY + d)
    # lets support that in case we get two parameters and issue a warning
    args = opargs.strip().split(',')
    if len(args) > 1:
        warning('invalid <CP expr,expr> opcode. Assuming alias CP A,expr')
        opargs = args[1]
    return store_register_arg_type(p, opargs, 0xb8, [0xfe])

def op_INC(p, opargs):
    return store_registerorpair_arg_type(p, opargs, 0x04, 0x03)

def op_DEC(p, opargs):
    return store_registerorpair_arg_type(p, opargs, 0x05, 0x0b)

def op_ADD(p,opargs):
    return store_add_type(p,opargs, [0x80], [0xc6], [0x09])

def op_ADC(p,opargs):
    return store_add_type(p,opargs, [0x88], [0xce], [0xed, 0x4a])

def op_SBC(p,opargs):
    return store_add_type(p, opargs,[0x98], [0xde], [0xed, 0x42])

def op_BIT(p,opargs):
    return store_bit_type(p, opargs, 0x40)

def op_RES(p,opargs):
    return store_bit_type(p, opargs, 0x80)

def op_SET(p,opargs):
    return store_bit_type(p, opargs, 0xc0)

def op_POP(p, opargs):
    return store_pushpop_type(p, opargs, 0xc1)

def op_PUSH(p, opargs):
    return store_pushpop_type(p, opargs, 0xc5)
 
def op_JP(p,opargs):
    if (len(opargs.split(',',1)) == 1):
        prefix, r, _ = single(p, opargs, allow_offset=0,allow_half=0)
        if r == REG_IND:
            instr = prefix
            instr.append(0xe9)
            if p == 2:
                g_context.store(p, instr)
            return len(instr)
    return store_jumpcall_type(p, opargs, 0xc3, 0xc2)

def op_CALL(p,opargs):
    return store_jumpcall_type(p,opargs, 0xcd, 0xc4)

def op_DJNZ(p,opargs):
    check_args(opargs,1)
    if p == 2:
        target = g_context.parse_expression(opargs, word=1)
        displacement = target - (g_context.origin + 2)
        if displacement > 127 or displacement < -128:
            abort ("Displacement from " + str(g_context.origin) + " to " + str(target) + " is out of range")
        g_context.store(p, [0x10, (displacement + 256) % 256])
    return 2

def op_JR(p, opargs):
    args = opargs.split(',', 1)
    if len(args) == 1:
        instr = 0x18
    else:
        cond = condition(args[0].strip().upper())
        if cond == -1:
            abort("expected condition but received '" + opargs + "'")
        elif cond >= 4:
            abort ("Invalid condition for JR")
        instr = 0x20 + 8 * cond
    if p == 2:
        target = g_context.parse_expression(args[-1], word=1)
        displacement = target - (g_context.origin + 2)
        if displacement > 127 or displacement < -128:
            abort ("Displacement from " + str(g_context.origin) +
                   " to " + str(target)+" is out of range")
        g_context.store(p, [instr, (displacement + 256) % 256])
    return 2

def op_RET(p, opargs):
    if opargs == '':
        if p == 2:
            g_context.store(p, [0xc9])
    else:
        check_args(opargs, 1)
        cond = condition(opargs)
        if cond == -1:
            abort ("expected condition but received '" + opargs + "'")
        if p == 2:
            g_context.store(p, [0xc0 + 8 * cond])
    return 1

def op_IM(p, opargs):
    check_args(opargs, 1)
    if p == 2:
        mode = g_context.parse_expression(opargs)
        if mode > 2 or mode < 0:
            abort ("argument out of range")
        if mode > 0:
            mode += 1
        g_context.store(p, [0xed, 0x46 + 8*mode])
    return 2

def op_RST(p, opargs):
    check_args(opargs, 1)
    if p == 2:
        vector = g_context.parse_expression(opargs)
        if vector > 0x38 or vector < 0 or (vector % 8) != 0:
            abort ("argument out of range or doesn't divide by 8")
        g_context.store(p, [0xc7 + vector])
    return 1

def op_EX(p, opargs):
    check_args(opargs, 2)
    args = opargs.upper().split(',', 1)

    if re.search(r"\A\s*\(\s*SP\s*\)\s*\Z", args[0], re.IGNORECASE):
        pre2, rr2 = double(args[1],allow_af_instead_of_sp=1, allow_af_alt=1, allow_index=1)
        if rr2 == REG_HL:
            instr = pre2
            instr.append(0xe3)
        else:
            abort("can't exchange " + args[0].strip() + " with " + args[1].strip())
    else:
        pre1, rr1 = double(args[0], allow_af_instead_of_sp=1, allow_index=0)
        pre2, rr2 = double(args[1], allow_af_instead_of_sp=1, allow_af_alt=1, allow_index=0)
        if (rr1 == REG_DE and rr2 == REG_HL) or (rr1 == REG_HL and rr2 == REG_DE):
            # EX DE,HL is the opcode but WinAPE allows EX HL,DE so we allow it too
            instr = pre1
            instr.extend(pre2)
            instr.append(0xeb)
        elif rr1 == REG_SP and rr2 == REG_AFA:
            instr = [0x08]
        else:
            abort("can't exchange " + args[0].strip() + " with " + args[1].strip())
    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def op_IN(p, opargs):
    check_args(opargs, 2)
    args = opargs.split(',', 1)
    if p == 2:
        _, r, _ = single(p, args[0], allow_index=0, allow_half=0)
        if r != NO_REG and r != REG_IND and re.search(r"\A\s*\(\s*C\s*\)\s*\Z", args[1], re.IGNORECASE):
            g_context.store(p, [0xed, 0x40 + 8 * r])
        elif r == REG_A:
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[1])
            if match == None:
                abort("no expression in " + args[1])

            n = g_context.parse_expression(match.group(1))
            g_context.store(p, [0xdb, n])
        else:
            abort("invalid argument")
    return 2

def op_OUT(p, opargs):
    check_args(opargs, 2)
    args = opargs.split(',', 1)
    if p == 2:
        _, r, _ = single(p, args[1], allow_index=0, allow_half=0)
        if r != NO_REG and r != REG_IND and re.search(r"\A\s*\(\s*C\s*\)\s*\Z", args[0], re.IGNORECASE):
            g_context.store(p, [0xed, 0x41 + 8 * r])
        elif r == REG_A:
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[0])
            n = g_context.parse_expression(match.group(1))
            g_context.store(p, [0xd3, n])
        else:
            abort("invalid argument")
    return 2

def op_LD(p,opargs):
    check_args(opargs, 2)
    arg1 ,arg2 = opargs.split(',', 1)

    prefix, rr1 = double(arg1)
    if rr1 != NO_REG:
        prefix2, rr2 = double(arg2)
        if rr1 == REG_SP and rr2 == REG_HL:
            instr = prefix2
            instr.append(0xf9)
            g_context.store(p, instr)
            return len(instr)

        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg2)
        if match:
            # ld rr, (nn)
            if p == 2:
                nn = g_context.parse_expression(match.group(1),word=1)
            else:
                nn = 0
            instr = prefix
            if rr1 == REG_HL:
                instr.extend([0x2a, nn%256, nn//256])
            else:
                instr.extend([0xed, 0x4b + 16*rr1, nn%256, nn//256])
            g_context.store(p, instr)
            return len (instr)
        else:
            #ld rr, nn
            if p == 2:
                nn = g_context.parse_expression(arg2,word=1)
            else:
                nn = 0
            instr = prefix
            instr.extend([0x01 + 16*rr1, nn%256, nn//256])
            g_context.store(p, instr)
            return len (instr)

    prefix, rr2 = double(arg2)
    if rr2 != NO_REG:
        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg1)
        if match:
            # ld (nn), rr
            if p == 2:
                nn = g_context.parse_expression(match.group(1))
            else:
                nn = 0
            instr = prefix
            if rr2 == REG_HL:
                instr.extend([0x22, nn%256, nn//256])
            else:
                instr.extend([0xed, 0x43 + 16*rr2, nn%256, nn//256])
            g_context.store(p, instr)
            return len (instr)

    prefix1,r1,postfix1 = single(p, arg1, allow_i=1, allow_r=1)
    prefix2,r2,postfix2 = single(p, arg2, allow_i=1, allow_r=1)
    if r1 != NO_REG:
        if r2 != NO_REG:
            if (r1 > REG_A) or (r2 > REG_A):
                if r1 == REG_A:
                    if r2 == REG_I:
                        g_context.store(p, [0xed,0x57])
                        return 2
                    elif r2 == REG_R:
                        g_context.store(p, [0xed,0x5f])
                        return 2
                if r2 == REG_A:
                    if r1 == REG_I:
                        g_context.store(p, [0xed,0x47])
                        return 2
                    elif r1 == REG_R:
                        g_context.store(p, [0xed,0x4f])
                        return 2
                abort("Invalid argument")

            if r1 == REG_IND and r2 == REG_IND:
                abort("Ha - nice try. That's a HALT.")

            if (r1 == REG_H or r1 == REG_L) and (r2 == REG_H or r2 == REG_L) and prefix1 != prefix2:
                abort("Illegal combination of operands")

            if r1 == REG_IND and (r2 == REG_H or r2 == REG_L) and len(prefix2) != 0:
                abort("Illegal combination of operands")

            if r2 == REG_IND and (r1 == REG_H or r1 == REG_L) and len(prefix1) != 0:
                abort("Illegal combination of operands")

            instr = prefix1
            if len(prefix1) == 0:
                instr.extend(prefix2)
            instr.append(0x40 + 8 * r1 + r2)
            instr.extend(postfix1)
            instr.extend(postfix2)
            g_context.store(p, instr)
            return len(instr)

        else:
            if r1 > REG_A:
                abort("Invalid argument")

            if r1 == REG_A and re.search(r"\A\s*\(\s*BC\s*\)\s*\Z", arg2, re.IGNORECASE):
                g_context.store(p, [0x0a])
                return 1
            if r1 == REG_A and re.search(r"\A\s*\(\s*DE\s*\)\s*\Z", arg2, re.IGNORECASE):
                g_context.store(p, [0x1a])
                return 1
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg2)
            if match:
                if r1 != REG_A:
                    abort("Illegal indirection")
                if p == 2:
                    nn = g_context.parse_expression(match.group(1), word=1)
                    g_context.store(p, [0x3a, nn%256, nn//256])
                return 3

            instr = prefix1
            instr.append(0x06 + 8 * r1)
            instr.extend(postfix1)
            if p == 2:
                n = g_context.parse_expression(arg2, byte=1)
            else:
                n = 0
            instr.append(n)
            g_context.store(p, instr)
            return len(instr)

    elif r2 == REG_A:
        # ld (bc/de/nn),a
        if re.search(r"\A\s*\(\s*BC\s*\)\s*\Z", arg1, re.IGNORECASE):
            g_context.store(p, [0x02])
            return 1
        if re.search(r"\A\s*\(\s*DE\s*\)\s*\Z", arg1, re.IGNORECASE):
            g_context.store(p, [0x12])
            return 1
        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg1)
        if match:
            if p == 2:
                nn = g_context.parse_expression(match.group(1), word=1)
                g_context.store(p, [0x32, nn%256, nn//256])
            return 3
    abort("LD args not understood - " + arg1 + ", " + arg2)
    return 1

def op_IF(p, opargs):
    check_args(opargs, 1)
    g_context.ifstack.append((g_context.currentfile, g_context.ifstate))
    if g_context.ifstate < IFSTATE_DISCART:
        # No undefined symbols are allowed in IF expressions or we may
        # calculate wrong other symbols
        cond = g_context.parse_logic_expr(opargs)
        if cond:
            g_context.ifstate = IFSTATE_ASSEMBLE
        else:
            g_context.ifstate = IFSTATE_DISCART
    else:
        g_context.ifstate = IFSTATE_FIND_END
    return 0

def op_ELSE(p, opargs):
    if g_context.ifstate == IFSTATE_ASSEMBLE or g_context.ifstate == IFSTATE_FIND_END:
        g_context.ifstate = IFSTATE_FIND_END
    elif g_context.ifstate == IFSTATE_DISCART:
        if opargs.upper().startswith("IF"):
            cond = g_context.parse_logic_expr(opargs[2:].strip())
            if cond:
                g_context.ifstate = IFSTATE_ASSEMBLE
            else:
                g_context.ifstate = IFSTATE_DISCART
        else:
            g_context.ifstate = IFSTATE_ASSEMBLE
    else:
        abort("mismatched ELSE/ELSEIF directive")
    return 0

def op_ELSEIF(p, opargs):
    # Pass "IF (cond)" to op_ELSE
    return op_ELSE(p, opargs[4:])

def op_ENDIF(p, opargs):
    check_args(opargs, 0)

    if len(g_context.ifstack) == 0:
        abort("Mismatched ENDIF")

    _, state = g_context.ifstack.pop()
    g_context.ifstate = state
    return 0

def op_MACRO(p, opargs):
    # Macros can contain calls to other macros but can not nest macro definitions
    if g_context.applying_macro != None:
        abort("macro definitions cannot be nested")
    name, args = g_context.parse_instruction(opargs)
    if g_context.verbose and p==1: print(f" adding macro {name} to the macros table")
    g_context.check_symbol(name, 'macro')
    if len(args) > 0:
        argv = args.split(',')

    macro = AsmMacro(name, argv)
    g_context.macros[name] = macro
    g_context.defining_macro = macro
    return 0

def op_ENDM(p, opargs):
    g_context.defining_macro = None
    return 0

def op__MACRO_ENTER_(p, opargs):
    if g_context.applying_macro != None:
        g_context.macros_stack.append((g_context.applying_macro, g_context.macros_applied))
    g_context.macros_applied = g_context.macros_applied + 1
    g_context.applying_macro = opargs.strip()
    return 0

def op__MACRO_LEAVE_(p, opargs):
    if len(g_context.macros_stack) > 0:
        g_context.applying_macro, g_context.macros_applied = g_context.macros_stack.pop()
    else:
        g_context.applying_macro = None
    return 0

###########################################################################

def create_opdict():
    """ Get all functions of this module that start with op_ """
    global g_opcode_functions
    g_opcode_functions = {}
    mod = inspect.getmodule(AsmContext)
    module_syms = inspect.getmembers(mod)
    for (sym, fun) in module_syms:
        if 'op_' == sym[0:3]:
            g_opcode_functions[sym] = fun

def assemble(inputfile, outputfile = None, predefsymbols = [], startaddr = 0x4000):
    if (outputfile == None):
        outputfile = os.path.splitext(inputfile)[0] + ".bin"
    
    g_context.reset()
    g_context.outputfile = outputfile
    for sym in predefsymbols:
        sym[0] = sym[0].upper()
        try:
            val = aux_int(sym[1])
        except:
            print("Error: invalid format for command-line symbol definition in" + val)
            sys.exit(1)
        g_context.set_symbol(sym[0], aux_int(sym[1]), type='predefined symbol')

    g_context.assemble(inputfile, outputfile, startaddr)

def aux_int(param):
    """
    By default, int params are converted assuming base 10.
    To allow hex values we need to 'auto' detect the base.
    """
    return int(param, 0)

def process_args():
    parser = argparse.ArgumentParser(
        prog = 'abasm.py',
        description = f'A Z80 assembler focused on the Amstrad CPC. Based on pyz80 but using a dialect compatible with Maxam/WinAPE and RVM.'
    )
    parser.add_argument('inputfile', help = 'Input file.')
    parser.add_argument('-d', '--define', nargs = 2, default = [], action = 'append', help = 'Defines a pair SYMBOL=VALUE.')
    parser.add_argument('-o', '--output', help = 'Target file in binary format. If not specified, first input file name will be used.')
    parser.add_argument('--start', type = aux_int, default = 0x4000, help = 'Starting address. Can be overwritten by ORG directive (default 0x4000).')
    parser.add_argument('-v', '--version', action='version', version=f' Abasm Assembler Version {__version__}', help = "Shows program's version and exits")
    parser.add_argument('--verbose', action='store_true', help = 'Prints all source code lines as they are assembled')
    args = parser.parse_args()
    return args

def main():
    global g_context
    args = process_args()
    g_context.verbose = args.verbose
    create_opdict()
    assemble(args.inputfile, args.output, args.define, args.start)
    sys.exit(0)

if __name__ == "__main__":
    main()
