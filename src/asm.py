#!/usr/bin/env python

"""
ASM.PY a Z80 assembler focused on the Amstrad CPC. Based on pyz80
pyz80 originally crafted by Andrew Collier, modified by Simon Owen
ASM.PY by Javier Garcia

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

import sys, os
import re
import argparse


IFSTATE_DISABLED = 0 # assemble all encounted code
IFSTATE_ASSEMBLE = 1 # assemble this code, but stop at ELSE or ELSEIF
IFSTATE_DISCART  = 2 # do not assemble this code, but might start at ELSE or ELSEIF
IFSTATE_FIND_END = 3 # do not assemble any code until ENDIF

class AsmContext:
    def __init__(self):
        self.reset()

    def reset(self):
        self.outputfile = ""
        self.listingfile = None
        self.origin = 0x4000
        self.include_stack = []
        self.symboltable = {}
        self.lettable = {}
        self.symusetable = {}
        self.memory = bytearray()
        self.forstack=[]
        self.ifstack = []
        self.ifstate = IFSTATE_DISABLED
        self.currentfile = "",
        self.currentline = ""
        self.lstcode = ""

    def parse_logic_expr(self, expr):
        values = re.findall(r'\w+', expr)
        for i in range(0, len(values)):
            values[i] = g_context.parse_expression(values[i])
        logic = re.findall(r'[<|>|=|<=|>=|!=|==]', expr)
        if len(logic) and logic[0] == '=': logic[0] = "=="

        if len(values) == 1: return values[0]
        if len(values) == 2:
            operation = "%d %s %d" % (values[0], logic[0], values[1])
            return eval(operation)
        fatal("evaluating logical expression")
       
    def parse_expression(self, arg, signed=0, byte=0, word=0):
        # WARNING: Maxam is supposed to evaluate operators from left to right (no operator precedence)
        # here we do not do that, so this is a departure from Maxam
        if ',' in arg:
            fatal("erroneous comma in expression " + arg)

        while 1:
            # single characters in quotes to integer values
            match = re.search('"(.)"', arg)
            if match:
                arg = arg.replace('"' + match.group(1) + '"', str(ord(match.group(1))))
            else:
                break

        arg = arg.replace('@', '(' + str(self.origin) + ')') # storage location, next address
        arg = arg.replace('%', '0b') # syntax for binary literals
        arg = arg.replace(' MOD ', '%') # Maxam syntax for modulus
        arg = re.sub(r'&|#([0-9a-fA-F]+\b)', r'0x\g<1>', arg) # hex numbers must start with & or #

        # fix capitalized hex or binary Python symbol
        # don't do these except at the start of a token
        arg = re.sub(r'\b0X', '0x', arg) 
        arg = re.sub(r'\b0B', '0b', arg)

        # if the argument still contains letters at this point,
        # it's a symbol which needs to be replaced
        testsymbol=''
        argcopy = ''
        incurly = 0
        inquotes = False

        for c in arg + " ":
            if c.isalnum() or c in '"_.{}' or incurly or inquotes:
                testsymbol += c
                if c == '{':
                    incurly += 1
                elif c == '}':
                    incurly -= 1
                elif c == '"':
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
                            fatal("Error in expression " +
                                arg +
                                ": undefined symbol " +
                                self.expand_symbol(testsymbol))

                    elif testsymbol[0] == '0' and len(testsymbol) > 2 and testsymbol[1] == 'b':
                        # binary literal
                        literal = 0
                        for digit in testsymbol[2:]:
                            literal *= 2
                            if digit == '1':
                                literal += 1
                            elif digit != '0':
                                fatal("Invalid binary digit '" + digit + "'")
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

        narg = int(eval(argcopy))

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

    def expand_symbol(self, sym):
        while 1:
            match = re.search(r'\{([^\{\}]*)\}', sym)
            if match:
                value = self.parse_expression(match.group(1))
                sym = sym.replace(match.group(0),str(value))
            else:
                break
        return sym

    def set_symbol(self, sym, value, is_label=False, is_let=False):
        if is_label:
            # In maxam labels can start with '.' to allow labels similar to opcodes
            if len(sym) and sym[0] == '.': sym = sym[1:].upper()
        else:
            symorig = self.expand_symbol(sym)
            sym = symorig.upper()
        if is_let: self.lettable[sym] = value
        self.symboltable[sym] = value

    def get_symbol(self, sym):
        symorig = self.expand_symbol(sym)
        sym = symorig.upper()
        if sym[0] == '.':
            sym = sym[1:]
        
        if sym in self.symboltable:
            self.symusetable[sym] = g_context.symusetable.get(sym,0)+1
            return self.symboltable[sym]
        return None

    def process_label(self, p, label):
        if len(label.split()) > 1:
            fatal("whitespaces are not allowed in label names")

        if label != "":
            if p == 1:
                self.set_symbol(label, self.origin, is_label = True)
            elif self.get_symbol(label) != self.origin:
                fatal("label address differs from previous stored value")

    def store(self, p, bytes):
        if p == 2:
            self.lstcode = ""
            for b in bytes:
                self.memory.append(b)
                self.lstcode = self.lstcode + "%02X " % (b)

    def save_mapfile(self, filename):
        mapfile = os.path.splitext(filename)[0] + '.map'
        with open(mapfile, 'w') as f:
            for sym, addr in sorted(self.symboltable.items()):
                used = 0 if sym not in self.symusetable else self.symusetable[sym]
                f.write('%-13s: %04X   %d\n' % (sym, addr, used))

    def save_memory(self, filename):
        contentlen = len(self.memory)
        if contentlen > 0:
            # check that something has been assembled at all
            with open(filename, 'wb') as fd:
                fd.write(self.memory)
        self.save_mapfile(filename)

    def write_listinfo(self, line):
        if self.listingfile == None:
            self.listingfile = open(os.path.splitext(self.outputfile)[0] + '.lst', "wt")
        self.listingfile.write(line + "\n")

    def assemble_instruction(self, p, line):
        # Lines must start by characters or underscord or '.'
        match = re.match(r'^(\.\w+|\w+)(.*)', line.strip())
        if not match:
            fatal("in '" + line + "'. Valid instructions must start with a letter, an underscord or '.'")

        inst = match.group(1).upper()
        args = match.group(2).strip()

        if (self.ifstate < IFSTATE_DISCART) or inst in ("IF", "ELSE", "ELSEIF", "ENDIF"):
            try:
                # get the pointer to the op_XXXX func
                # not recognized opcodes or directives are labels in Maxam dialect BUT they
                # can go with opcodes separated by spaces in the same line 'loop jp loop'
                functioncall = eval("op_" + inst)
                return functioncall(p, args)
            except NameError as e:
                if " EQU " in line.upper():
                    params = line.upper().split(' EQU ')
                    op_EQU(p, ','.join(params))
                else:
                    self.process_label(p, inst.rstrip())
                    extra_statements = line.split(' ', 1)
                    if len(extra_statements) > 1:
                        return self.assemble_instruction(p, extra_statements[1])
                return 0
            except SystemExit as e:
                sys.exit(e)
        else:
            return 0

    def assembler_pass(self, p, inputfile):
        # file references are local, so assembler_pass can be called recursively (op_INCLUDE)
        # but copied to a global identifier in g_context for warning printouts

        self.currentfile = "command line"
        self.currentline = "0"

        # just read the whole file into memory, it's not going to be huge (probably)
        # I'd prefer not to, but assembler_pass can be called recursively
        # (by op_INCLUDE for example) and fileinput does not support two files simultaneously

        try:
            currentfile = open(inputfile, 'r')
            wholefile = currentfile.readlines()
            wholefile.insert(0, '') # prepend blank so line numbers are 1-based
            currentfile.close()
        except:
            fatal("Couldn't open file '" + inputfile + "' for reading")

        linenumber = 0
        while linenumber < len(wholefile):
            currentline = wholefile[linenumber].replace("\t", "  ")
            self.currentline = currentline
            self.currentfile = inputfile + ":" + str(linenumber)
            
            # One line can contain multiple statements separated by ':', for example
            # loop: jp loop
            # lets remove comments and check for multi opcodes
            filteredline = currentline.strip().split(';')[0]
            statements = filteredline.split(':')
            for opcode in statements:
                opcode = opcode.strip()
                if opcode == '': continue
                if opcode.count('"') % 2 != 0 or opcode.count("'") % 2 != 0:
                    fatal("mismatched quotes")
                
                bytes = self.assemble_instruction(p, opcode)
                if p > 1:
                    lstout = "%06d  %04X  %-13s\t%s" % (linenumber, self.origin, self.lstcode, opcode)
                    self.lstcode = ""
                    self.write_listinfo(lstout)
                self.origin = (self.origin + bytes) % 65536

            if self.currentfile.startswith(inputfile + ":") and int(self.currentfile.rsplit(':', 1)[1]) != linenumber:
                linenumber = int(self.currentfile.rsplit(':', 1)[1])
            linenumber += 1

    def assemble(self, inputfile, outputfile, startaddr):
        print("Generating", outputfile)
        for p in [1, 2]:
            self.origin = startaddr
            self.include_stack = []
            self.assembler_pass(p, inputfile)

        if len(self.ifstack) > 0:
            print("Error: Mismatched IF and ENDIF statements, too many IF")
            for item in self.ifstack:
                print(item[0])
            sys.exit(1)
        if len(self.forstack) > 0:
            print("Error: Mismatched EQU FOR and NEXT statements, too many EQU FOR")
            for item in self.forstack:
                print(item[1])
            sys.exit(1)
        self.save_memory(outputfile)


g_context = AsmContext()

###########################################################################

def warning(message):
    print(os.path.basename(g_context.currentfile), 'warning:', message)
    print('\t', g_context.currentline.strip())

def fatal(message):
    print(os.path.basename(g_context.currentfile), 'error:', message)
    print('\t', g_context.currentline.strip())
    sys.exit(1)


def double(arg, allow_af_instead_of_sp=0, allow_af_alt=0, allow_index=1):
    # decode double register [bc, de, hl, sp][ix,iy] --special:  af af'
    double_mapping = {'BC':([],0), 'DE':([],1), 'HL':([],2), 'SP':([],3), 'IX':([0xdd],2), 'IY':([0xfd],2), 'AF':([],5), "AF'":([],4) }
    rr = double_mapping.get(arg.strip().upper(),([],-1))
    if (rr[1]==3) and allow_af_instead_of_sp:
        rr = ([],-1)
    if rr[1]==5:
        if allow_af_instead_of_sp:
            rr = ([],3)
        else:
            rr = ([],-1)
    if (rr[1]==4) and not allow_af_alt:
        rr = ([],-1)

    if (rr[0] != []) and not allow_index:
        rr = ([],-1)

    return rr

def single(p, arg, allow_i=0, allow_r=0, allow_index=1, allow_offset=1, allow_half=1):
    # decode single register [b,c,d,e,h,l,(hl),a][(ix {+c}),(iy {+c})]
    single_mapping = {'B':0, 'C':1, 'D':2, 'E':3, 'H':4, 'L':5, 'A':7, 'I':8, 'R':9, 'IXH':10, 'IXL':11, 'IYH':12, 'IYL':13 }
    m = single_mapping.get(arg.strip().upper(), -1)
    prefix = []
    postfix = []

    if m == 8 and not allow_i:
        m = -1
    if m == 9 and not allow_r:
        m = -1

    if allow_half:
        if m == 10:
            prefix = [0xdd]
            m = 4
        if m == 11:
            prefix = [0xdd]
            m = 5
        if m == 12:
            prefix = [0xfd]
            m = 4
        if m == 13:
            prefix = [0xfd]
            m = 5
    else:
        if m >= 10 and m <= 13:
            m = -1

    if m == -1 and re.search(r"\A\s*\(\s*HL\s*\)\s*\Z", arg, re.IGNORECASE):
        m = 6

    if m == -1 and allow_index:
        match = re.search(r"\A\s*\(\s*(I[XY])\s*\)\s*\Z", arg, re.IGNORECASE)
        if match:
            m = 6
            prefix = [0xdd] if match.group(1).lower() == 'ix' else [0xfd]
            postfix = [0]

        elif allow_offset:
            match = re.search(r"\A\s*\(\s*(I[XY])\s*([+-].*)\s*\)\s*\Z", arg, re.IGNORECASE)
            if match:
                m = 6
                prefix = [0xdd] if match.group(1).lower() == 'ix' else [0xfd]
                if p == 2:
                    offset = g_context.parse_expression(match.group(2), byte=1, signed=1)
                    if offset < -128 or offset > 127:
                        fatal ("invalid index offset: "+str(offset))
                    postfix = [(offset + 256) % 256]
                else:
                    postfix = [0]

    return prefix, m, postfix

def condition(arg):
    # decode condition [nz, z, nc, c, po, pe, p, m]
    condition_mapping = {'NZ':0, 'Z':1, 'NC':2, 'C':3, 'PO':4, 'PE':5, 'P':6, 'M':7 }
    return condition_mapping.get(arg.upper(),-1)

def check_args(args, expected):
    if args == '':
        received = 0
    else:
        received = len(args.split(','))
    if expected != received:
        fatal("wrong number of arguments, expected "+str(expected)+" but received "+str(args))

def op_ORG(p, opargs):
    check_args(opargs, 1)
    g_context.origin = g_context.parse_expression(opargs, word=1)
    return 0

def op_DUMP(p, opargs):
    # Not currently implemented. Maxam used it to write symbol information
    return 0

def op_PRINT(p, opargs):
    text = []
    for expr in opargs.split(","):
        if expr.strip().startswith('"'):
            text.append(expr.strip().rstrip()[1:-1])
        else:
            a = g_context.parse_expression(expr)
            if a:
                text.append(str(a))
            else:
                text.append("?")
    print(g_context.currentfile, "PRINT: ", ",".join(text))
    return 0

def op_EQU(p, opargs):
    check_args(opargs, 2)
    symbol, expr = opargs.split(',')
    symbol = symbol.strip()
    expr = expr.strip()
    if p == 1:
        g_context.set_symbol(symbol, g_context.parse_expression(expr, signed = 1))
    else:
        expr_result = g_context.parse_expression(expr, signed = 1)
        existing = g_context.get_symbol(symbol)
        if existing == '':
            g_context.set_symbol(symbol, expr_result)
        elif existing != expr_result:
                fatal("Symbol " +
                      g_context.expand_symbol(symbol) +
                      ": expected " + str(existing) +
                      " but calculated " + str(expr_result) +
                      ", has this symbol been used twice?")
    return 0

def op_NEXT(p, opargs):
    check_args(opargs, 1)
    foritem = g_context.forstack.pop()
    if opargs != foritem[0]:
        fatal("NEXT symbol " + opargs + " doesn't match FOR: expected " + foritem[0])
    foritem[2] += 1

    g_context.set_symbol(foritem[0], foritem[2])

    if foritem[2] < foritem[3]:
        g_context.currentfile = foritem[1]
        g_context.forstack.append(foritem)
    return 0

def op_ALIGN(p, opargs):
    args = opargs.replace(" ", "").split(",")
    if len(args) < 1:
        fatal("ALIGN directive requieres at least one value")
    padding = 0 if len(args) == 1 else g_context.parse_expression(args[1])
    align = g_context.parse_expression(args[0])
    if align < 1:
        fatal("invalid negative alignment")
    elif (align & (-align)) != align:
        fatal("requested alignment is not a power of 2")
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
        fatal("Allocated invalid space < 0 bytes (" + str(s) + ")")
    g_context.store(p, [0 for i in range(0, s)])
    return s

def op_DW(p, opargs):
    return op_DEFW(p, opargs)

def op_DEFW(p, opargs):
    s = opargs.split(',')
    if p == 2:
        for b in s:
            b=(g_context.parse_expression(b, word=1))
            g_context.store(p, [b%256, b//256])
    return 2*len(s)

def op_DM(p, opargs):
    return op_DEFB(p, opargs)

def op_DB(p, opargs):
    return op_DEFB(p, opargs)

def op_DEFM(p, opargs):
   return op_DEFB(p, opargs)

def op_DEFB(p, opargs):
    args = opargs.split(',')
    bytes = []
    for arg in args:
        texts = re.findall(r'"(.*?)"', arg)
        if len(texts) == 0: texts = re.findall(r"'(.*?)'", arg)
        if len(texts) > 0:
            # text string between "" or ''
            bytes = bytes + list(texts[0].encode('latin-1'))
        else:
            byte = 0 if p == 1 else g_context.parse_expression(arg, byte = 1)
            bytes.append(byte)
    if p == 2: g_context.store(p, bytes)
    return len(bytes)

def op_LET(p, opargs):
    args = opargs.replace(" ", "").upper().split("=")
    if len(args) != 2:
        fatal("LET directive uses the format SYMBOL=VALUE")
    sym, val = args
    val = g_context.parse_expression(val)
    g_context.set_symbol(sym, val, is_let = True)
    return 0

def op_READ(p, opargs):
    # WinAPE directive to include other assembly source code
    if len(g_context.include_stack) > 5:
        fatal("too deep read/include tree")

    path = re.search(r'(?<=["\'])(.*?)(?=["\'])', opargs)
    if path == None or os.path.exists(path.group(0)):
        fatal("wrong path specified in the READ directive")
    g_context.include_stack.append(g_context.currentfile)
    filename = os.path.join(os.path.dirname(g_context.currentfile), path.group(0))
    g_context.assembler_pass(p, filename)
    g_context.currentfile = g_context.include_stack.pop()
    return 0

def op_FOR(p,opargs):
    args = opargs.split(',',1)
    limit = g_context.parse_expression(args[0])
    bytes = 0
    for iterate in range(limit):
        g_context.symboltable['FOR'] = iterate
        bytes += g_context.assemble_instruction(p,args[1].strip())

    if limit != 0:
        del g_context.symboltable['FOR']

    return bytes

def op_noargs_type(p,opargs,instr):
    check_args(opargs,0)
    if (p==2):
        g_context.store(p, instr)
    return len(instr)

def op_ASSERT(p,opargs):
    check_args(opargs,1)
    if (p==2):
        value = g_context.parse_expression(opargs)
        if value == 0:
            fatal("Assertion failed ("+opargs+")")
    return 0


def op_NOP(p, opargs):
    return op_noargs_type(p, opargs, [0x00])

def op_RLCA(p, opargs):
    return op_noargs_type(p, opargs, [0x07])

def op_RRCA(p, opargs):
    return op_noargs_type(p, opargs, [0x0F])

def op_RLA(p, opargs):
    return op_noargs_type(p, opargs, [0x17])

def op_RRA(p, opargs):
    return op_noargs_type(p, opargs, [0x1F])

def op_DAA(p, opargs):
    return op_noargs_type(p, opargs, [0x27])

def op_CPL(p, opargs):
    return op_noargs_type(p, opargs, [0x2F])

def op_SCF(p, opargs):
    return op_noargs_type(p, opargs, [0x37])

def op_CCF(p, opargs):
    return op_noargs_type(p, opargs, [0x3F])

def op_HALT(p, opargs):
    return op_noargs_type(p, opargs, [0x76])

def op_DI(p, opargs):
    return op_noargs_type(p, opargs, [0xf3])

def op_EI(p, opargs):
    return op_noargs_type(p, opargs, [0xfb])

def op_EXX(p, opargs):
    return op_noargs_type(p, opargs, [0xd9])

def op_NEG(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0x44])

def op_RETN(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0x45])

def op_RETI(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0x4d])

def op_RRD(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0x67])

def op_RLD(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0x6F])

def op_LDI(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xa0])

def op_CPI(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xa1])

def op_INI(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xa2])

def op_OUTI(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xa3])

def op_LDD(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xa8])

def op_CPD(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xa9])

def op_IND(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xaa])

def op_OUTD(p,opargs):
    return op_noargs_type(p, opargs, [0xed, 0xab])

def op_LDIR(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xb0])

def op_CPIR(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xb1])

def op_INIR(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xb2])

def op_OTIR(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xb3])

def op_LDDR(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xb8])

def op_CPDR(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xb9])

def op_INDR(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xba])

def op_OTDR(p, opargs):
    return op_noargs_type(p, opargs, [0xed, 0xbb])

def op_cbshifts_type(p, opargs, offset, step_per_register=1):
    args = opargs.split(',', 1)
    if len(args) == 2:
        # compound instruction of the form RLC B,(IX+c)
        pre1, r1, post1 = single(p, args[0], allow_half=0, allow_index=0)
        pre2, r2, post2 = single(p, args[1], allow_half=0, allow_index=1)
        if r1 == -1 or r2 == -1:
            fatal("registers not recognized for compound instruction")
        if r1 == 6:
            fatal("(HL) not allowed as target of compound instruction")
        if len(pre2) == 0:
            fatal("must use index register as operand of compound instruction")

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
        if r == -1:
            fatal("invalid argument")
        else:
            instr.append(offset + step_per_register * r)
    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def op_RLC(p, opargs):
    return op_cbshifts_type(p, opargs, 0x00)

def op_RRC(p, opargs):
    return op_cbshifts_type(p, opargs, 0x08)

def op_RL(p, opargs):
    return op_cbshifts_type(p, opargs, 0x10)

def op_RR(p, opargs):
    return op_cbshifts_type(p, opargs, 0x18)

def op_SLA(p, opargs):
    return op_cbshifts_type(p, opargs, 0x20)

def op_SRA(p, opargs):
    return op_cbshifts_type(p, opargs, 0x28)

def op_SLL(p, opargs):
    if p == 1:
        warning("SLL doesn't do what you probably expect on z80b! Use SL1 if you know what you're doing.")
    return op_cbshifts_type(p, opargs, 0x30)

def op_SL1(p, opargs):
    return op_cbshifts_type(p, opargs, 0x30)

def op_SRL(p, opargs):
    return op_cbshifts_type(p, opargs, 0x38)

def op_register_arg_type(p, opargs, offset, ninstr, step_per_register=1):
    check_args(opargs, 1)
    pre, r, post = single(p, opargs, allow_half=1)
    instr = pre
    if r == -1:
        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", opargs)
        if match:
            fatal ("illegal indirection")

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

def op_SUB(p, opargs):
    return op_register_arg_type(p, opargs, 0x90, [0xd6])

def op_AND(p, opargs):
    # Z80 Aseembly language programming book lists AND without register A
    # because always operates with the accumulator BUT WinAPE assembler seems
    # to use the aliases AND A,r AND A,n AND A,(HL) AND A,(IX + d) AND A,(IY + d)
    # lets support that in case we get two parameters and issue a warning
    args = opargs.strip().split(',')
    if len(args) > 1:
        warning('invalid <ADD expr,expr> opcode. Assuming alias ADD A,expr')
        opargs = args[1]
    return op_register_arg_type(p, opargs, 0xa0, [0xe6])

def op_XOR(p, opargs):
    return op_register_arg_type(p, opargs, 0xa8, [0xee])

def op_OR(p, opargs):
    # Z80 Aseembly language programming book lists OR without register A
    # because always operates with the accumulator BUT WinAPE assembler seems
    # to use the aliases OR A,r OR A,n OR A,(HL) OR A,(IX + d) OR A,(IY + d)
    # lets support that in case we get two parameters and issue a warning
    args = opargs.strip().split(',')
    if len(args) > 1:
        warning('invalid <OR expr,expr> opcode. Assuming alias OR A,expr')
        opargs = args[1]
    return op_register_arg_type(p, opargs, 0xb0, [0xf6])

def op_CP(p, opargs):
    # Z80 Aseembly language programming book lists CP without register A
    # because always operates with the accumulator BUT WinAPE assembler seems
    # to use the aliases CP A,r CP A,n CP A,(HL) CP A,(IX + d) CP A,(IY + d)
    # lets support that in case we get two parameters and issue a warning
    args = opargs.strip().split(',')
    if len(args) > 1:
        warning('invalid <CP expr,expr> opcode. Assuming alias CP A,expr')
        opargs = args[1]
    return op_register_arg_type(p, opargs, 0xb8, [0xfe])

def op_registerorpair_arg_type(p, opargs, rinstr, rrinstr, step_per_register=8, step_per_pair=16):
    check_args(opargs, 1)
    pre,r,post = single(p, opargs)

    if r==-1:
        pre,rr = double(opargs)
        if rr==-1:
            fatal ("Invalid argument")

        instr = pre
        instr.append(rrinstr + step_per_pair * rr)
    else:
        instr = pre
        instr.append(rinstr + step_per_register * r)
        instr.extend(post)
    if (p==2):
        g_context.store(p, instr)
    return len(instr)

def op_INC(p, opargs):
    return op_registerorpair_arg_type(p,opargs, 0x04, 0x03)

def op_DEC(p, opargs):
    return op_registerorpair_arg_type(p,opargs, 0x05, 0x0b)

def op_add_type(p, opargs, rinstr, ninstr, rrinstr, step_per_register=1, step_per_pair=16):
    args = opargs.split(',', 1)
    r=-1
    if len(args) == 2:
        pre,r,post = single(p, args[0])
    if len(args) == 1 or r == 7:
        pre, r, post = single(p, args[-1])
        instr = pre
        if r == -1:
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[-1])
            if match:
                fatal("illegal indirection")
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
            fatal("Can't mix index registers and HL")
        if len(rrinstr) > 1 and pre:
            fatal("can't use index registers in this instruction")

        if len(args) != 2 or rr1 != 2 or rr2 == -1:
            fatal("invalid argument")
        instr = pre
        instr.extend(rrinstr)
        instr[-1] += step_per_pair * rr2

    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def op_ADD(p,opargs):
    return op_add_type(p,opargs,[0x80], [0xc6],[0x09])

def op_ADC(p,opargs):
    return op_add_type(p,opargs,[0x88], [0xce],[0xed,0x4a])

def op_SBC(p,opargs):
    return op_add_type(p,opargs,[0x98], [0xde],[0xed,0x42])

def op_bit_type(p,opargs,offset):
    check_args(opargs,2)
    arg1,arg2 = opargs.split(',',1)
    b = g_context.parse_expression(arg1)
    if b>7 or b<0:
        fatal ("argument out of range")
    pre,r,post = single(p, arg2,allow_half=0)
    if r==-1:
        fatal ("Invalid argument")
    instr = pre
    instr.append(0xcb)
    instr.extend(post)
    instr.append(offset + r + 8*b)
    if (p==2):
        g_context.store(p, instr)
    return len(instr)

def op_BIT(p,opargs):
    return op_bit_type(p,opargs, 0x40)

def op_RES(p,opargs):
    return op_bit_type(p,opargs, 0x80)

def op_SET(p,opargs):
    return op_bit_type(p,opargs, 0xc0)

def op_pushpop_type(p,opargs,offset):
    check_args(opargs,1)
    prefix, rr = double(opargs, allow_af_instead_of_sp=1)
    instr = prefix
    if rr==-1:
        fatal ("Invalid argument")
    else:
        instr.append(offset + 16 * rr)
    if (p==2):
        g_context.store(p, instr)
    return len(instr)

def op_POP(p, opargs):
    return op_pushpop_type(p,opargs, 0xc1)

def op_PUSH(p, opargs):
    return op_pushpop_type(p,opargs, 0xc5)
 
def op_jumpcall_type(p, opargs, offset, condoffset):
    args = opargs.split(',', 1)
    if len(args) == 1:
        instr = [offset]
    else:
        cond = condition(args[0])
        if cond == -1:
            fatal ("expected condition but received '" + opargs + "'")
        instr = [condoffset + 8 * cond]

    match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[-1])
    if match:
        fatal ("Illegal indirection")

    if p == 2:
        nn = g_context.parse_expression(args[-1], word=1)
        instr.extend([nn%256, nn//256])
        g_context.store(p, instr)
    return 3

def op_JP(p,opargs):
    if (len(opargs.split(',',1)) == 1):
        prefix, r, postfix = single(p, opargs, allow_offset=0,allow_half=0)
        if r==6:
            instr = prefix
            instr.append(0xe9)
            if (p==2):
                g_context.store(p, instr)
            return len(instr)
    return op_jumpcall_type(p,opargs, 0xc3, 0xc2)

def op_CALL(p,opargs):
    return op_jumpcall_type(p,opargs, 0xcd, 0xc4)

def op_DJNZ(p,opargs):
    check_args(opargs,1)
    if (p==2):
        target = g_context.parse_expression(opargs,word=1)
        displacement = target - (g_context.origin + 2)
        if displacement > 127 or displacement < -128:
            fatal ("Displacement from "+str(g_context.origin)+" to "+str(target)+" is out of range")
        g_context.store(p, [0x10,(displacement+256)%256])
    return 2

def op_JR(p, opargs):
    args = opargs.split(',', 1)
    if len(args) == 1:
        instr = 0x18
    else:
        cond = condition(args[0].strip().upper())
        if cond == -1:
            fatal("expected condition but received '" + opargs + "'")
        elif cond >= 4:
            fatal ("Invalid condition for JR")
        instr = 0x20 + 8 * cond
    if p == 2:
        target = g_context.parse_expression(args[-1], word=1)
        displacement = target - (g_context.origin + 2)
        if displacement > 127 or displacement < -128:
            fatal ("Displacement from " + str(g_context.origin) +
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
            fatal ("expected condition but received '" + opargs + "'")
        if p == 2:
            g_context.store(p, [0xc0 + 8 * cond])
    return 1

def op_IM(p, opargs):
    check_args(opargs, 1)
    if (p==2):
        mode = g_context.parse_expression(opargs)
        if mode > 2 or mode < 0:
            fatal ("argument out of range")
        if mode > 0:
            mode += 1
        g_context.store(p, [0xed, 0x46 + 8*mode])
    return 2

def op_RST(p, opargs):
    check_args(opargs, 1)
    if p == 2:
        vector = g_context.parse_expression(opargs)
        if vector > 0x38 or vector < 0 or (vector % 8) != 0:
            fatal ("argument out of range or doesn't divide by 8")
        g_context.store(p, [0xc7 + vector])
    return 1

def op_EX(p, opargs):
    check_args(opargs, 2)
    args = opargs.upper().split(',', 1)

    if re.search(r"\A\s*\(\s*SP\s*\)\s*\Z", args[0], re.IGNORECASE):
        pre2, rr2 = double(args[1],allow_af_instead_of_sp=1, allow_af_alt=1, allow_index=1)
        if rr2 == 2:
            instr = pre2
            instr.append(0xe3)
        else:
            fatal("can't exchange " + args[0].strip() + " with " + args[1].strip())
    else:
        pre1, rr1 = double(args[0], allow_af_instead_of_sp=1, allow_index=0)
        pre2, rr2 = double(args[1], allow_af_instead_of_sp=1, allow_af_alt=1, allow_index=0)
        if rr1 == 1 and rr2 == 2:
            # EX DE,HL
            instr = pre1
            instr.extend(pre2)
            instr.append(0xeb)
        elif rr1 == 3 and rr2 == 4:
            instr = [0x08]
        else:
            fatal("can't exchange " + args[0].strip() + " with " + args[1].strip())
    if p == 2:
        g_context.store(p, instr)
    return len(instr)

def op_IN(p, opargs):
    check_args(opargs, 2)
    args = opargs.split(',', 1)
    if p == 2:
        pre, r, post = single(p, args[0], allow_index=0, allow_half=0)
        if r!=-1 and r!=6 and re.search(r"\A\s*\(\s*C\s*\)\s*\Z", args[1], re.IGNORECASE):
            g_context.store(p, [0xed, 0x40 + 8 * r])
        elif r == 7:
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[1])
            if match == None:
                fatal("no expression in " + args[1])

            n = g_context.parse_expression(match.group(1))
            g_context.store(p, [0xdb, n])
        else:
            fatal("invalid argument")
    return 2

def op_OUT(p, opargs):
    check_args(opargs, 2)
    args = opargs.split(',', 1)
    if p == 2:
        pre, r, post = single(p, args[1], allow_index=0, allow_half=0)
        if r!=-1 and r!=6 and re.search(r"\A\s*\(\s*C\s*\)\s*\Z", args[0], re.IGNORECASE):
            g_context.store(p, [0xed, 0x41 + 8 * r])
        elif r == 7:
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[0])
            n = g_context.parse_expression(match.group(1))
            g_context.store(p, [0xd3, n])
        else:
            fatal("invalid argument")
    return 2

def op_LD(p,opargs):
    check_args(opargs, 2)
    arg1 ,arg2 = opargs.split(',', 1)

    prefix, rr1 = double(arg1)
    if rr1 != -1:
        prefix2, rr2 = double(arg2)
        if rr1 == 3 and rr2 == 2:
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
            if rr1 == 2:
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
    if rr2 != -1:
        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg1)
        if match:
            # ld (nn), rr
            if p==2:
                nn = g_context.parse_expression(match.group(1))
            else:
                nn = 0
            instr = prefix
            if rr2==2:
                instr.extend([0x22, nn%256, nn//256])
            else:
                instr.extend([0xed, 0x43 + 16*rr2, nn%256, nn//256])
            g_context.store(p, instr)
            return len (instr)

    prefix1,r1,postfix1 = single(p, arg1, allow_i=1, allow_r=1)
    prefix2,r2,postfix2 = single(p, arg2, allow_i=1, allow_r=1)
    if r1 != -1 :
        if r2 != -1:
            if (r1 > 7) or (r2 > 7):
                if r1==7:
                    if r2==8:
                        g_context.store(p, [0xed,0x57])
                        return 2
                    elif r2==9:
                        g_context.store(p, [0xed,0x5f])
                        return 2
                if r2==7:
                    if r1==8:
                        g_context.store(p, [0xed,0x47])
                        return 2
                    elif r1==9:
                        g_context.store(p, [0xed,0x4f])
                        return 2
                fatal("Invalid argument")

            if r1==6 and r2==6:
                fatal("Ha - nice try. That's a HALT.")

            if (r1==4 or r1==5) and (r2==4 or r2==5) and prefix1 != prefix2:
                fatal("Illegal combination of operands")

            if r1==6 and (r2==4 or r2==5) and len(prefix2) != 0:
                fatal("Illegal combination of operands")

            if r2==6 and (r1==4 or r1==5) and len(prefix1) != 0:
                fatal("Illegal combination of operands")

            instr = prefix1
            if len(prefix1) == 0:
                instr.extend(prefix2)
            instr.append(0x40 + 8*r1 + r2)
            instr.extend(postfix1)
            instr.extend(postfix2)
            g_context.store(p, instr)
            return len(instr)

        else:
            if r1 > 7:
                fatal("Invalid argument")

            if r1==7 and re.search(r"\A\s*\(\s*BC\s*\)\s*\Z", arg2, re.IGNORECASE):
                g_context.store(p, [0x0a])
                return 1
            if r1==7 and re.search(r"\A\s*\(\s*DE\s*\)\s*\Z", arg2, re.IGNORECASE):
                g_context.store(p, [0x1a])
                return 1
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg2)
            if match:
                if r1 != 7:
                    fatal("Illegal indirection")
                if p==2:
                    nn = g_context.parse_expression(match.group(1), word=1)
                    g_context.store(p, [0x3a, nn%256, nn//256])
                return 3

            instr = prefix1
            instr.append(0x06 + 8*r1)
            instr.extend(postfix1)
            if (p==2):
                n = g_context.parse_expression(arg2, byte=1)
            else:
                n = 0
            instr.append(n)
            g_context.store(p, instr)
            return len(instr)

    elif r2==7:
        # ld (bc/de/nn),a
        if re.search(r"\A\s*\(\s*BC\s*\)\s*\Z", arg1, re.IGNORECASE):
            g_context.store(p, [0x02])
            return 1
        if re.search(r"\A\s*\(\s*DE\s*\)\s*\Z", arg1, re.IGNORECASE):
            g_context.store(p, [0x12])
            return 1
        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg1)
        if match:
            if p==2:
                nn = g_context.parse_expression(match.group(1), word=1)
                g_context.store(p, [0x32, nn%256, nn//256])
            return 3
    fatal("LD args not understood - "+arg1+", "+arg2)
    return 1

def op_IF(p, opargs):
    check_args(opargs, 1)
    g_context.ifstack.append((g_context.currentfile, g_context.ifstate))
    if g_context.ifstate < IFSTATE_DISCART:
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
        fatal("mismatched ELSE/ELSEIF directive")
    return 0

def op_ELSEIF(p, opargs):
    # Pass "IF (cond)" to op_ELSE
    return op_ELSE(p, opargs[4:])

def op_ENDIF(p, opargs):
    check_args(opargs, 0)

    if len(g_context.ifstack) == 0:
        fatal("Mismatched ENDIF")

    _, state = g_context.ifstack.pop()
    g_context.ifstate = state
    return 0

###########################################################################

def run_assemble(inputfile, outputfile, predefsymbols, startaddr):
    if (outputfile == None):
        outputfile = os.path.splitext(inputfile)[0] + ".bin"
    
    g_context.reset()
    g_context.outputfile = outputfile

    for value in predefsymbols:
        sym = value.split('=', 1)
        if len(sym) == 1:
            sym.append("1")
        sym[0] = sym[0].upper()
        try:
            val = aux_int(sym[1])
        except:
            print("error: invalid format for command-line symbol definition in" + value)
            sys.exit(1)
        g_context.set_symbol(sym[0], aux_int(sym[1]))

    g_context.assemble(inputfile, outputfile, startaddr)

def aux_int(param):
    """
    By default, int params are converted assuming base 10.
    To allow hex values we need to 'auto' detect the base.
    """
    return int(param, 0)

def process_args():
    parser = argparse.ArgumentParser(
        prog = 'asm.py',
        description = 'A Z80 assembler focused on the Amstrad CPC. Based on pyz80 but using a dialect compatible with Maxam/WinAPE.'
    )
    parser.add_argument('inputfile', help = 'Input file.')
    parser.add_argument('-d', '--define', default = [], action = 'append', help = 'Defines a pair SYMBOL=VALUE.')
    parser.add_argument('-o', '--output', help = 'Target file in binary format. If not specified, first input file name will be used.')
    parser.add_argument('--start', type = aux_int, default = 0x4000, help = 'Starting address. Can be overwritten by ORG directive (default 0x4000).')

    args = parser.parse_args()
    return args

def main():
    args = process_args()
    run_assemble(args.inputfile, args.output, args.define, args.start)
    print("OK")
    sys.exit(0)

if __name__ == "__main__":
    main()
