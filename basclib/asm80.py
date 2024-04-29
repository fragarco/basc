#!/usr/bin/env python

"""
ASM80.PY a Z80 assembler focused on the Amstrad CPC. Based on pyz80
pyz80 originally crafted by Andrew Collier, modified by Simon Owen
ASM80.PY by Javier Garcia

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

import getopt
import sys, os
import re
import argparse
import math     # used by expressions in eval calls
import random   # used by expressions in eval calls

class AsmContext:
    def __init__(self):
        self.reset()

    def reset(self):
        self.outputfile = ""
        self.listingfile = None
        self.origin = 0x4000
        self.path = ""
        self.include_stack = []
        self.symboltable = {}
        self.symusetable = {}
        self.labeltable = {}
        self.memory = bytearray()
        self.forstack=[]
        self.ifstack = []
        self.ifstate = 0
        self.currentfile = "",
        self.currentline = ""
        self.lstcode = ""

g_context = AsmContext()

def save_memory(memory, filename):
    contentlen = len(memory)
    if contentlen > 0:
        # check that something has been assembled at all
        with open(filename, 'wb') as fd:
            fd.write(memory)

def warning(message):
    print(g_context.currentfile, 'warning:', message)
    print('\t', g_context.currentline.strip())

def fatal(message):
    print(g_context.currentfile, 'error:', message)
    print ('\t', g_context.currentline.strip())
    sys.exit(1)

def expand_symbol(sym):
    while 1:
        match = re.search(r'\{([^\{\}]*)\}', sym)
        if match:
            value = parse_expression(match.group(1))
            sym = sym.replace(match.group(0),str(value))
        else:
            break
    return sym

def set_symbol(sym, value, is_label=False):
    if is_label:
        # In maxam labels can start with '.' to allow labels similar to opcodes
        if len(sym) and sym[0] == '.': sym = sym[1:].upper()
        g_context.labeltable[sym] = value
    else:
        symorig = expand_symbol(sym)
        sym = symorig.upper()
    g_context.symboltable[sym] = value

def get_symbol(sym):
    symorig = expand_symbol(sym)
    sym = symorig.upper()
    if sym[0] == '.':
        sym = sym[1:]
    
    if sym in g_context.symboltable:
        g_context.symusetable[sym] = g_context.symusetable.get(sym,0)+1
        return g_context.symboltable[sym]
    return None


def parse_expression(arg, signed=0, byte=0, word=0):
    # WARNING: Maxam is supposed to evaluate operators from left to right (no operator precedence)
    # here we do not do that, so this is a departure from Maxam
    if ',' in arg:
        fatal("Erroneous comma in expression" + arg)

    while 1:
        match = re.search('"(.)"', arg)
        if match:
            arg = arg.replace('"' + match.group(1) + '"', str(ord(match.group(1))))
        else:
            break

    while 1:
        match = re.search(r'defined\s*\(\s*(.*?)\s*\)', arg, re.IGNORECASE)
        if match:
            result = (get_symbol(match.group(1)) != None)
            arg = arg.replace(match.group(0),str(int(result)))
        else:
            break
    arg = arg.replace('@', '(' + str(g_context.origin) + ')') # storage location, next address
    arg = arg.replace('%', '0b') # syntax for binary literals
    arg = arg.replace(' MOD ', '%') # Maxam syntax for modulus
    arg = re.sub(r'&|#([0-9a-fA-F]+\b)', r'0x\g<1>', arg) # hex numbers must start with & or #

    # fix capitalized hex or binary Python symbol
    # don't do these except at the start of a token
    arg = re.sub(r'\b0X', '0x', arg) 
    arg = re.sub(r'\b0B', '0b', arg)

    # if the argument contains letters at this point,
    # it's a symbol which needs to be replaced

    testsymbol=''
    argcopy = ''

    incurly = 0
    inquotes = False

    for c in arg+' ':
        if c.isalnum() or c in '"_.{}' or incurly or inquotes:
            testsymbol += c
            if c=='{':
                incurly += 1
            elif c=='}':
                incurly -= 1
            elif c=='"':
                inquotes = not inquotes
        else:
            if (testsymbol != ''):
                if not testsymbol[0].isdigit():
                    result = get_symbol(testsymbol)
                    if (result != None):
                        testsymbol = str(result)
                    elif testsymbol[0] == '"' and testsymbol[-1]=='"':
                        # string literal used in some expressions
                        pass
                    else:
                        understood = 0
                        # some of python's math expressions should be available to the parser
                        if not understood and testsymbol.lower() != 'e':
                            parsestr = 'math.'+testsymbol.lower()
                            try:
                                eval(parsestr)
                                understood = 1
                            except:
                                understood = 0

                        if not understood:
                            parsestr = 'random.'+testsymbol.lower()
                            try:
                                eval(parsestr)
                                understood = 1
                            except:
                                understood = 0

                        if testsymbol in ["FILESIZE"]:
                            parsestr = 'os.path.getsize'
                            understood = 1

                        if not understood :
                            fatal("Error in expression " + arg + ": Undefined symbol " + expand_symbol(testsymbol))

                        testsymbol = parsestr

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
                warning ("Unsigned byte value truncated from "+str(narg))
            narg %= 256
        elif word:
            if narg < -32768 or narg > 65535:
                warning ("Unsigned word value truncated from "+str(narg))
            narg %= 65536
    return narg

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
    #decode single register [b,c,d,e,h,l,(hl),a][(ix {+c}),(iy {+c})]
    single_mapping = {'B':0, 'C':1, 'D':2, 'E':3, 'H':4, 'L':5, 'A':7, 'I':8, 'R':9, 'IXH':10, 'IXL':11, 'IYH':12, 'IYL':13 }
    m = single_mapping.get(arg.strip().upper(),-1)
    prefix=[]
    postfix=[]

    if m==8 and not allow_i:
        m = -1
    if m==9 and not allow_r:
        m = -1

    if allow_half:
        if m==10:
            prefix = [0xdd]
            m = 4
        if m==11:
            prefix = [0xdd]
            m = 5
        if m==12:
            prefix = [0xfd]
            m = 4
        if m==13:
            prefix = [0xfd]
            m = 5
    else:
        if m >= 10 and m <= 13:
            m = -1

    if m==-1 and re.search(r"\A\s*\(\s*HL\s*\)\s*\Z", arg, re.IGNORECASE):
        m = 6

    if m==-1 and allow_index:
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
                    offset = parse_expression(match.group(2), byte=1, signed=1)
                    if offset < -128 or offset > 127:
                        fatal ("invalid index offset: "+str(offset))
                    postfix = [(offset + 256) % 256]
                else:
                    postfix = [0]

    return prefix,m,postfix

def condition(arg):
    # decode condition [nz, z, nc, c, po, pe, p, m]
    condition_mapping = {'NZ':0, 'Z':1, 'NC':2, 'C':3, 'PO':4, 'PE':5, 'P':6, 'M':7 }
    return condition_mapping.get(arg.upper(),-1)


def dump(p, bytes):
    if p == 2:
        g_context.lstcode = ""
        for b in bytes:
            g_context.memory.append(b)
            g_context.lstcode = g_context.lstcode + "%02X " % (b)

def check_args(args, expected):
    if args == '':
        received = 0
    else:
        received = len(args.split(','))
    if expected != received:
        fatal("Opcode wrong number of arguments, expected "+str(expected)+" received "+str(args))

def op_ORG(p, opargs):
    global origin
    check_args(opargs, 1)
    origin = parse_expression(opargs, word=1)
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
            a = parse_expression(expr, silenterror=True)
            if a:
                text.append(str(a))
            else:
                text.append("?")
    print(g_context.currentfile, "PRINT: ", ",".join(text))
    return 0

def op_EQU(p, opargs):
    global symboltable
    check_args(opargs, 2)
    symbol, expr = opargs.split(',')
    symbol = symbol.strip()
    expr = expr.strip()
    if p == 1:
        set_symbol(symbol, parse_expression(expr, signed = 1))
    else:
        expr_result = parse_expression(expr, signed = 1)
        existing = get_symbol(symbol)
        if existing == '':
            set_symbol(symbol, expr_result)
        elif existing != expr_result:
                fatal("Symbol " + expand_symbol(symbol) + ": expected " + str(existing) + " but calculated " + str(expr_result) + ", has this symbol been used twice?")
    return 0

def op_NEXT(p,opargs):
    check_args(opargs,1)
    foritem = g_context.forstack.pop()
    if opargs != foritem[0]:
        fatal("NEXT symbol " + opargs + " doesn't match FOR: expected " + foritem[0])
    foritem[2] += 1

    set_symbol(foritem[0], foritem[2])

    if foritem[2] < foritem[3]:
        g_context.currentfile = foritem[1]
        g_context.forstack.append(foritem)
    return 0

def op_ALIGN(p,opargs):
    global dumpspace_pending
    check_args(opargs,1)

    align = parse_expression(opargs)
    if align<1:
        fatal("Invalid alignment")
    elif (align & (-align)) != align:
        fatal("Alignment is not a power of 2")

    s = (align - origin%align)%align
    dumpspace_pending += s
    return s

def op_DS(p,opargs):
    return op_DEFS(p,opargs)

def op_DEFS(p,opargs):
    global dumpspace_pending
    check_args(opargs, 1)

    if opargs.upper().startswith("ALIGN") and (opargs[5].isspace() or opargs[5] == '('):
        return op_ALIGN(p, opargs[5:].strip())
    s = parse_expression(opargs)
    if s < 0:
        fatal("Allocated invalid space < 0 bytes ("+str(s)+")")
    dumpspace_pending += s
    return s

def op_DB(p,opargs):
    return op_DEFB(p,opargs)

def op_DEFB(p,opargs):
    s = opargs.split(',')
    if (p==2):
        for b in s:
            byte=(parse_expression(b, byte=1, silenterror=1))
            if byte=='':
                fatal("Didn't understand DB or character constant "+b)
            else:
                dump(p, [byte])
    return len(s)

def op_DW(p,opargs):
    return op_DEFW(p,opargs)

def op_DEFW(p,opargs):
    s = opargs.split(',')
    if (p==2):
        for b in s:
            b=(parse_expression(b, word=1))
            dump(p, [b%256, b//256])
    return 2*len(s)

def op_DM(p,opargs):
    return op_DEFM(p,opargs)

def op_DEFM(p,opargs):
    messagelen = 0
    if opargs.strip()=="44" or opargs=="(44)":
        dump ([44])
        messagelen = 1
    else:
        matchstr = opargs
        while matchstr.strip():
            match = re.match(r'\s*\"(.*)\"(\s*,)?(.*)', matchstr)
            if not match:
                match = re.match(r'\s*([^,]*)(\s*,)?(.*)', matchstr)
                byte=(parse_expression(match.group(1), byte=1, silenterror=1))
                if byte=='':
                    fatal("Didn't understand DM character constant "+match.group(1))
                elif p==2:
                    dump(p, [byte])

                messagelen += 1
            else:
                message = list(match.group(1))

                if p==2:
                    for i in message:
                        dump ([ord(i)])
                messagelen += len(message)

            matchstr = match.group(3)

            if match.group(3) and not match.group(2):
                matchstr = '""' + matchstr
                # For cases such as  DEFM "message with a "" in it"
                # I can only apologise for this, this is an artefact of my parsing quotes
                # badly at the top level but it's too much for me to go back and refactor it all.
                # Of course, it would have helped if Comet had had sane quoting rules in the first place.
    return messagelen

def op_INCLUDE(p, opargs):
    match = re.search(r'\A\s*\"(.*)\"\s*\Z', opargs)
    filename = match.group(1)

    g_context.include_stack.append((g_context.path, g_context.currentfile))
    assembler_pass(p, filename)
    g_context.path, g_context.currentfile = g_context.include_stack.pop()
    return 0

def op_FOR(p,opargs):
    args = opargs.split(',',1)
    limit = parse_expression(args[0])
    bytes = 0
    for iterate in range(limit):
        symboltable['FOR'] = iterate
        bytes += assemble_instruction(p,args[1].strip())

    if limit != 0:
        del symboltable['FOR']

    return bytes

def op_noargs_type(p,opargs,instr):
    check_args(opargs,0)
    if (p==2):
        dump(p, instr)
    return len(instr)

def op_ASSERT(p,opargs):
    check_args(opargs,1)
    if (p==2):
        value = parse_expression(opargs)
        if value == 0:
            fatal("Assertion failed ("+opargs+")")
    return 0


def op_NOP(p,opargs):
    return op_noargs_type(p,opargs,[0x00])

def op_RLCA(p,opargs):
    return op_noargs_type(p,opargs,[0x07])

def op_RRCA(p,opargs):
    return op_noargs_type(p,opargs,[0x0F])

def op_RLA(p,opargs):
    return op_noargs_type(p,opargs,[0x17])

def op_RRA(p,opargs):
    return op_noargs_type(p,opargs,[0x1F])

def op_DAA(p,opargs):
    return op_noargs_type(p,opargs,[0x27])

def op_CPL(p,opargs):
    return op_noargs_type(p,opargs,[0x2F])

def op_SCF(p,opargs):
    return op_noargs_type(p,opargs,[0x37])

def op_CCF(p,opargs):
    return op_noargs_type(p,opargs,[0x3F])

def op_HALT(p,opargs):
    return op_noargs_type(p,opargs,[0x76])

def op_DI(p,opargs):
    return op_noargs_type(p,opargs,[0xf3])

def op_EI(p,opargs):
    return op_noargs_type(p,opargs,[0xfb])

def op_EXX(p,opargs):
    return op_noargs_type(p,opargs,[0xd9])

def op_NEG(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0x44])

def op_RETN(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0x45])

def op_RETI(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0x4d])

def op_RRD(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0x67])

def op_RLD(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0x6F])

def op_LDI(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xa0])

def op_CPI(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xa1])

def op_INI(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xa2])

def op_OUTI(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xa3])

def op_LDD(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xa8])

def op_CPD(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xa9])

def op_IND(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xaa])

def op_OUTD(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xab])

def op_LDIR(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xb0])

def op_CPIR(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xb1])

def op_INIR(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xb2])

def op_OTIR(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xb3])

def op_LDDR(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xb8])

def op_CPDR(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xb9])

def op_INDR(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xba])

def op_OTDR(p,opargs):
    return op_noargs_type(p,opargs,[0xed,0xbb])

def op_cbshifts_type(p,opargs,offset,step_per_register=1):
    args = opargs.split(',',1)
    if len(args) == 2:
        # compound instruction of the form RLC B,(IX+c)
        pre1,r1,post1 = single(p, args[0], allow_half=0, allow_index=0)
        pre2,r2,post2 = single(p, args[1], allow_half=0, allow_index=1)
        if r1==-1 or r2==-1:
            fatal("Registers not recognized for compound instruction")
        if r1==6:
            fatal("(HL) not allowed as target of compound instruction")
        if len(pre2)==0:
            fatal("Must use index register as operand of compound instruction")

        instr=pre2
        instr.extend([0xcb])
        instr.extend(post2)
        instr.append(offset + step_per_register*r1)

    else:
        check_args(opargs,1)
        pre,r,post = single(p, opargs, allow_half=0)
        instr = pre
        instr.extend([0xcb])
        instr.extend(post)
        if r==-1:
            fatal ("Invalid argument")
        else:
            instr.append(offset + step_per_register*r)

    if (p==2):
        dump(p, instr)
    return len(instr)

def op_RLC(p,opargs):
    return op_cbshifts_type(p,opargs,0x00)

def op_RRC(p,opargs):
    return op_cbshifts_type(p,opargs,0x08)

def op_RL(p,opargs):
    return op_cbshifts_type(p,opargs,0x10)

def op_RR(p,opargs):
    return op_cbshifts_type(p,opargs,0x18)

def op_SLA(p,opargs):
    return op_cbshifts_type(p,opargs,0x20)

def op_SRA(p,opargs):
    return op_cbshifts_type(p,opargs,0x28)

def op_SLL(p,opargs):
    if (p==1):
        warning("SLL doesn't do what you probably expect on z80b! Use SL1 if you know what you're doing.")
    return op_cbshifts_type(p,opargs,0x30)

def op_SL1(p,opargs):
    return op_cbshifts_type(p,opargs,0x30)

def op_SRL(p,opargs):
    return op_cbshifts_type(p,opargs,0x38)

def op_register_arg_type(p,opargs,offset,ninstr,step_per_register=1):
    check_args(opargs,1)
    pre,r,post = single(p, opargs, allow_half=1)
    instr = pre
    if r==-1:
        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", opargs)
        if match:
            fatal ("Illegal indirection")

        instr.extend(ninstr)
        if (p==2):
            n = parse_expression(opargs, byte=1)
        else:
            n = 0
        instr.append(n)
    else:
        instr.append(offset + step_per_register*r)
    instr.extend(post)
    if (p==2):
        dump(p, instr)
    return len(instr)

def op_SUB(p,opargs):
    return op_register_arg_type(p,opargs, 0x90, [0xd6])

def op_AND(p,opargs):
    return op_register_arg_type(p,opargs, 0xa0, [0xe6])

def op_XOR(p,opargs):
    return op_register_arg_type(p,opargs, 0xa8, [0xee])

def op_OR(p,opargs):
    return op_register_arg_type(p,opargs, 0xb0, [0xf6])

def op_CP(p,opargs):
    return op_register_arg_type(p,opargs, 0xb8, [0xfe])

def op_registerorpair_arg_type(p,opargs,rinstr,rrinstr,step_per_register=8,step_per_pair=16):
    check_args(opargs,1)
    pre,r,post = single(p, opargs)

    if r==-1:
        pre,rr = double(opargs)
        if rr==-1:
            fatal ("Invalid argument")

        instr = pre
        instr.append(rrinstr + step_per_pair*rr)
    else:
        instr = pre
        instr.append(rinstr + step_per_register*r)
        instr.extend(post)
    if (p==2):
        dump(p, instr)
    return len(instr)

def op_INC(p,opargs):
    return op_registerorpair_arg_type(p,opargs, 0x04, 0x03)

def op_DEC(p,opargs):
    return op_registerorpair_arg_type(p,opargs, 0x05, 0x0b)

def op_add_type(p,opargs,rinstr,ninstr,rrinstr,step_per_register=1,step_per_pair=16):
    args = opargs.split(',',1)
    r=-1

    if len(args) == 2:
        pre,r,post = single(p, args[0])

    if (len(args) == 1) or r==7:
        pre,r,post = single(p, args[-1])
        instr = pre
        if r==-1:
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[-1])
            if match:
                fatal ("Illegal indirection")

            instr.extend(ninstr)
            if (p==2):
                n = parse_expression(args[-1], byte=1)
            else:
                n = 0
            instr.append(n)
        else:
            instr.extend(rinstr)
            instr[-1] += step_per_register*r

        instr.extend(post)
    else:
        pre,rr1 = double(args[0])
        dummy,rr2 = double(args[1])

        if (rr1 == rr2) and (pre != dummy):
            fatal ("Can't mix index registers and HL")
        if (len(rrinstr) > 1) and pre:
            fatal ("Can't use index registers in this instruction")

        if (len(args) != 2) or (rr1 != 2) or (rr2 == -1):
            fatal("Invalid argument")

        instr = pre
        instr.extend(rrinstr)
        instr[-1] += step_per_pair*rr2

    if (p==2):
        dump(p, instr)
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
    b = parse_expression(arg1)
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
        dump(p, instr)
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
        dump(p, instr)
    return len(instr)

def op_POP(p,opargs):
    return op_pushpop_type(p,opargs, 0xc1)

def op_PUSH(p,opargs):
    return op_pushpop_type(p,opargs, 0xc5)

def op_jumpcall_type(p,opargs,offset, condoffset):
    args = opargs.split(',',1)
    if len(args) == 1:
        instr = [offset]
    else:
        cond = condition(args[0])
        if cond == -1:
            fatal ("Expected condition, received "+opargs)
        instr = [condoffset + 8*cond]

    match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[-1])
    if match:
        fatal ("Illegal indirection")

    if (p==2):
        nn = parse_expression(args[-1],word=1)
        instr.extend([nn%256, nn//256])
        dump(p, instr)

    return 3

def op_JP(p,opargs):
    if (len(opargs.split(',',1)) == 1):
        prefix, r, postfix = single(p, opargs, allow_offset=0,allow_half=0)
        if r==6:
            instr = prefix
            instr.append(0xe9)
            if (p==2):
                dump(p, instr)
            return len(instr)
    return op_jumpcall_type(p,opargs, 0xc3, 0xc2)

def op_CALL(p,opargs):
    return op_jumpcall_type(p,opargs, 0xcd, 0xc4)

def op_DJNZ(p,opargs):
    check_args(opargs,1)
    if (p==2):
        target = parse_expression(opargs,word=1)
        displacement = target - (origin + 2)
        if displacement > 127 or displacement < -128:
            fatal ("Displacement from "+str(origin)+" to "+str(target)+" is out of range")
        dump(p, [0x10,(displacement+256)%256])

    return 2

def op_JR(p,opargs):
    args = opargs.split(',',1)
    if len(args) == 1:
        instr = 0x18
    else:
        cond = condition(args[0])
        if cond == -1:
            fatal ("Expected condition, received "+opargs)
        elif cond >= 4:
            fatal ("Invalid condition for JR")
        instr = 0x20 + 8*cond
    if (p==2):
        target = parse_expression(args[-1],word=1)
        displacement = target - (origin + 2)
        if displacement > 127 or displacement < -128:
            fatal ("Displacement from "+str(origin)+" to "+str(target)+" is out of range")
        dump(p, [instr,(displacement+256)%256])

    return 2

def op_RET(p,opargs):
    if opargs=='':
        if (p==2):
            dump(p, [0xc9])
    else:
        check_args(opargs,1)
        cond = condition(opargs)
        if cond == -1:
            fatal ("Expected condition, received "+opargs)
        if (p==2):
            dump(p, [0xc0 + 8*cond])
    return 1

def op_IM(p,opargs):
    check_args(opargs,1)
    if (p==2):
        mode = parse_expression(opargs)
        if (mode>2) or (mode<0):
            fatal ("argument out of range")
        if mode > 0:
            mode += 1

        dump(p, [0xed, 0x46 + 8*mode])
    return 2

def op_RST(p,opargs):
    check_args(opargs,1)
    if (p==2):
        vector = parse_expression(opargs)
        if (vector>0x38) or (vector<0) or ((vector%8) != 0):
            fatal ("argument out of range or doesn't divide by 8")

        dump(p, [0xc7 + vector])
    return 1

def op_EX(p,opargs):
    check_args(opargs,2)
    args = opargs.split(',',1)

    if re.search(r"\A\s*\(\s*SP\s*\)\s*\Z", args[0], re.IGNORECASE):
        pre2,rr2 = double(args[1],allow_af_instead_of_sp=1, allow_af_alt=1, allow_index=1)

        if rr2==2:
            instr = pre2
            instr.append(0xe3)
        else:
            fatal("Can't exchange "+args[0]+" with "+args[1])
    else:
        pre1,rr1 = double(args[0],allow_af_instead_of_sp=1, allow_index=0)
        pre2,rr2 = double(args[1],allow_af_instead_of_sp=1, allow_af_alt=1, allow_index=0)

        if rr1==1 and rr2==2:
            # EX DE,HL
            instr = pre1
            instr.extend(pre2)
            instr.append(0xeb)
        elif (rr1==3 and rr2==4):
            instr=[0x08]
        else:
            fatal("Can't exchange "+args[0]+" with "+args[1])

    if (p==2):
        dump(p, instr)
    return len(instr)

def op_IN(p,opargs):
    check_args(opargs,2)
    args = opargs.split(',',1)
    if (p==2):
        pre,r,post = single(p, args[0], allow_index=0, allow_half=0)
        if r!=-1 and r!=6 and re.search(r"\A\s*\(\s*C\s*\)\s*\Z", args[1], re.IGNORECASE):
            dump(p, [0xed, 0x40+8*r])
        elif r==7:
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[1])
            if match==None:
                fatal("No expression in "+args[1])

            n = parse_expression(match.group(1))
            dump(p, [0xdb, n])
        else:
            fatal("Invalid argument")
    return 2

def op_OUT(p,opargs):
    check_args(opargs,2)
    args = opargs.split(',',1)
    if (p==2):
        pre,r,post = single(p, args[1], allow_index=0, allow_half=0)
        if r!=-1 and r!=6 and re.search(r"\A\s*\(\s*C\s*\)\s*\Z", args[0], re.IGNORECASE):
            dump(p, [0xed, 0x41+8*r])
        elif r==7:
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", args[0])
            n = parse_expression(match.group(1))
            dump(p, [0xd3, n])
        else:
            fatal("Invalid argument")
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
            dump(p, instr)
            return len(instr)

        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg2)
        if match:
            # ld rr, (nn)
            if p == 2:
                nn = parse_expression(match.group(1),word=1)
            else:
                nn = 0
            instr = prefix
            if rr1 == 2:
                instr.extend([0x2a, nn%256, nn//256])
            else:
                instr.extend([0xed, 0x4b + 16*rr1, nn%256, nn//256])
            dump(p, instr)
            return len (instr)
        else:
            #ld rr, nn
            if p == 2:
                nn = parse_expression(arg2,word=1)
            else:
                nn = 0
            instr = prefix
            instr.extend([0x01 + 16*rr1, nn%256, nn//256])
            dump(p, instr)
            return len (instr)

    prefix, rr2 = double(arg2)
    if rr2 != -1:
        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg1)
        if match:
            # ld (nn), rr
            if p==2:
                nn = parse_expression(match.group(1))
            else:
                nn = 0
            instr = prefix
            if rr2==2:
                instr.extend([0x22, nn%256, nn//256])
            else:
                instr.extend([0xed, 0x43 + 16*rr2, nn%256, nn//256])
            dump(p, instr)
            return len (instr)

    prefix1,r1,postfix1 = single(p, arg1, allow_i=1, allow_r=1)
    prefix2,r2,postfix2 = single(p, arg2, allow_i=1, allow_r=1)
    if r1 != -1 :
        if r2 != -1:
            if (r1 > 7) or (r2 > 7):
                if r1==7:
                    if r2==8:
                        dump(p, [0xed,0x57])
                        return 2
                    elif r2==9:
                        dump(p, [0xed,0x5f])
                        return 2
                if r2==7:
                    if r1==8:
                        dump(p, [0xed,0x47])
                        return 2
                    elif r1==9:
                        dump(p, [0xed,0x4f])
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
            dump(p, instr)
            return len(instr)

        else:
            if r1 > 7:
                fatal("Invalid argument")

            if r1==7 and re.search(r"\A\s*\(\s*BC\s*\)\s*\Z", arg2, re.IGNORECASE):
                dump(p, [0x0a])
                return 1
            if r1==7 and re.search(r"\A\s*\(\s*DE\s*\)\s*\Z", arg2, re.IGNORECASE):
                dump(p, [0x1a])
                return 1
            match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg2)
            if match:
                if r1 != 7:
                    fatal("Illegal indirection")
                if p==2:
                    nn = parse_expression(match.group(1), word=1)
                    dump(p, [0x3a, nn%256, nn//256])
                return 3

            instr = prefix1
            instr.append(0x06 + 8*r1)
            instr.extend(postfix1)
            if (p==2):
                n = parse_expression(arg2, byte=1)
            else:
                n = 0
            instr.append(n)
            dump(p, instr)
            return len(instr)

    elif r2==7:
        # ld (bc/de/nn),a
        if re.search(r"\A\s*\(\s*BC\s*\)\s*\Z", arg1, re.IGNORECASE):
            dump(p, [0x02])
            return 1
        if re.search(r"\A\s*\(\s*DE\s*\)\s*\Z", arg1, re.IGNORECASE):
            dump(p, [0x12])
            return 1
        match = re.search(r"\A\s*\(\s*(.*)\s*\)\s*\Z", arg1)
        if match:
            if p==2:
                nn = parse_expression(match.group(1), word=1)
                dump(p, [0x32, nn%256, nn//256])
            return 3
    fatal("LD args not understood - "+arg1+", "+arg2)
    return 1

#ifstate=0: parse all code
#ifstate=1: parse this code, but stop at ELSE
#ifstate=2: do not parse this code, but might start at ELSE
#ifstate=3: do not parse any code until ENDIF

def op_IF(p,opargs):
    global ifstate, ifstack
    check_args(opargs,1)

    ifstack.append((g_context.currentfile,ifstate))
    if ifstate < 2:
        cond = parse_expression(opargs)
        if cond:
            ifstate = 1
        else:
            ifstate = 2
    else:
        ifstate = 3
    return 0

def op_ELSE(p,opargs):
    global ifstate, ifstack
    if ifstate==1 or ifstate==3:
        ifstate = 3
    elif ifstate==2:
        if opargs.upper().startswith("IF"):
            cond = parse_expression(opargs[2:].strip())
            if cond:
                ifstate = 1
            else:
                ifstate = 2
        else:
            ifstate = 1
    else:
        fatal("Mismatched ELSE")
    return 0

def op_ENDIF(p,opargs):
    global ifstate, ifstack
    check_args(opargs, 0)

    if len(ifstack) == 0:
        fatal("Mismatched ENDIF")

    _, state = ifstack.pop()
    ifstate = state
    return 0

def process_label(p, label):
    if len(label.split()) > 1:
        fatal("Whitespace not allowed in label names:", label)

    if label != "":
        if p == 1:
            set_symbol(label, g_context.origin, is_label = True)
        elif get_symbol(label) != g_context.origin:
            fatal("label " + label + " expected " + str(get_symbol(label)) + " but calculated " + str(g_context.origin) + ", has this label been used twice?")


def assemble_instruction(p, line):
    # Lines must start by characters or underscord or '.'
    match = re.match(r'^(\.\w+|\w+)(.*)', line)
    if not match:
        fatal("Lines must start with a letter, an underscord or '.'")

    inst = match.group(1).upper()
    args = match.group(2).strip()

    if (g_context.ifstate < 2) or inst in ("IF", "ELSE", "ENDIF"):
        functioncall = "op_" + inst + "(p, args)"
        try:
            return eval(functioncall)
        except SystemExit as e:
            sys.exit(e)
        except NameError as e:
            if " EQU " in line.upper():
                params = line.upper().split(' EQU ')
                op_EQU(p, ','.join(params))
            else:
                # not recognized opcodes or directives are labels in Maxam dialect BUT they
                # can go with opcodes separated by spaces in the same line: loop jp loop
                process_label(p, inst.rstrip())
                extra_statements = line.split(' ', 1)
                if len(extra_statements) > 1:
                    return assemble_instruction(p, extra_statements[1])
            return 0
        except Exception as e:
            print("Unexpected error:", str(e))
            sys.exit(1)
    else:
        return 0

def assembler_pass(p, inputfile):
    # file references are local, so assembler_pass can be called recursively (op_INCLUDE)
    # but copied to a global identifier in g_context for warning printouts

    g_context.currentfile = "command line"
    g_context.currentline = "0"

    # just read the whole file into memory, it's not going to be huge (probably)
    # I'd prefer not to, but assembler_pass can be called recursively
    # (by op_INCLUDE for example) and fileinput does not support two files simultaneously

    this_currentfilename = os.path.join(g_context.path, inputfile)
    if os.sep in this_currentfilename:
        g_context.path = os.path.dirname(this_currentfilename)

    try:
        currentfile = open(this_currentfilename, 'r')
        wholefile = currentfile.readlines()
        wholefile.insert(0, '') # prepend blank so line numbers are 1-based
        currentfile.close()
    except:
        fatal("Couldn't open file " + this_currentfilename + " for reading")

    consider_linenumber = 0
    while consider_linenumber < len(wholefile):
        currentline = wholefile[consider_linenumber]
        g_context.currentline = currentline
        g_context.currentfile = this_currentfilename + ":" + str(consider_linenumber)
        
        # One line can contain multiple statements separated by ':', for example
        # loop: jp loop
        statements = currentline.split(':')
        for statement in statements:
            opcode = ""
            inquotes = ""
            inquoteliteral = False
            char = ""
            for nextchar in statement + " ":
                if char == ';' and not inquotes:
                    # this is a comment
                    break
                if char == '"':
                    if not inquotes:
                        inquotes = char
                    else:
                        if (not inquoteliteral) and nextchar == '"':
                            inquoteliteral = True
                        elif inquoteliteral:
                            inquoteliteral = False
                            inquotes += char
                        else:
                            inquotes += char

                            if inquotes == '""':
                                inquotes = '"""'
                            elif inquotes == '","':
                                inquotes = " 44 "
                                char = ""

                            opcode += inquotes
                            inquotes = ""
                elif inquotes:
                    inquotes += char
                else:
                    opcode += char
                char = nextchar

            opcode = opcode.strip()

            if inquotes:
                fatal("Mismatched quotes")
            
            if (opcode):
                bytes = assemble_instruction(p, opcode)
                if p > 1:
                    lstout = "%06d  %04X  %-13s\t%s" % (
                        consider_linenumber, g_context.origin, g_context.lstcode, statement.strip()
                    )
                    g_context.lstcode = ""
                    writelisting(lstout)
                g_context.origin = (g_context.origin + bytes) % 65536
            else:
                if p > 1:
                    lstout = "    %-13s\t%s" % ("", wholefile[consider_linenumber].rstrip())
                    g_context.lstcode = ""
                    writelisting(lstout)

        if g_context.currentfile.startswith(this_currentfilename + ":") and int(g_context.currentfile.rsplit(':', 1)[1]) != consider_linenumber:
            consider_linenumber = int(g_context.currentfile.rsplit(':', 1)[1])
        consider_linenumber += 1

def writelisting(line):
    if g_context.listingfile == None:
        g_context.listingfile = open(os.path.splitext(g_context.outputfile)[0] + '.lst', "wt")
    g_context.listingfile.write(line+"\n")

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
            print("Error: Invalid value for symbol predefined on command line, " + value)
            sys.exit(1)
        set_symbol(sym[0], aux_int(sym[1]))

    print("Generating", outputfile)
    for p in [1, 2]:
        g_context.origin = startaddr
        g_context.path = ''
        g_context.include_stack = []
        assembler_pass(p, inputfile)

    if len(g_context.ifstack) > 0:
        print("Error: Mismatched IF and ENDIF statements, too many IF")
        for item in g_context.ifstack:
            print(item[0])
        sys.exit(1)
    if len(g_context.forstack) > 0:
        print("Error: Mismatched EQU FOR and NEXT statements, too many EQU FOR")
        for item in g_context.forstack:
            print(item[1])
        sys.exit(1)

    # dump map file
    mapfile = os.path.splitext(outputfile)[0] + '.map'
    with open(mapfile, 'w') as f:
        f.write("symbols = {\n")
        for sym, addr in sorted(g_context.symboltable.items()):
            used = 'True' if sym in g_context.symusetable and g_context.symusetable[sym] > 1 else 'False'
            f.write('  "%s": (%04X, %s),\n' % (sym, addr, used))
        f.write("}\n")
    
    save_memory(g_context.memory, outputfile)

def aux_int(param):
    """
    By default, int params are converted assuming base 10.
    To allow hex values we need to 'auto' detect the base.
    """
    return int(param, 0)

def process_args():
    parser = argparse.ArgumentParser(
        prog = 'asm80.py',
        description = 'A Z80 assembler focused on the Amstrad CPC. Based on pyz80 but using a dialect compatible with Maxam.'
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
