"""
Emitter object to generate Intermediate Stack Machine Code

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
from typing import List, Tuple, Dict, Optional
from bastypes import Expression, Symbol, BASTypes

class SMI:
    """ Stack Machine Instructions """
    NOP     = 'NOP'
    REM     = 'REM'
    LABEL   = 'LABEL'
    PUSH    = 'PUSH'
    CLEAR   = 'CLEAR'
    DROP    = 'DROP'
    LDVAL   = 'LDVAL'
    LDMEM   = 'LDMEM'
    STMEM   = 'STMEM'
    LDLREF  = 'LDLREF'
    LDLOCL  = 'LDLOCL'
    STLOCL  = 'STLOCL'
    STINDR  = 'STINDR'
    STINDB  = 'STINDB'
    INCGLOB = 'INCGLOB'
    INCLOCL = 'INCLOCL'
    INC     = 'INC'
    INCR    = 'INCR'
    STACK   = 'STACK'
    UNSTACK = 'UNSTACK'
    LOCLVEC = 'LOCLVEC'
    GLOBVEC = 'GLOBVEC'
    INDEX   = 'INDEX'
    DEREF   = 'DEREF'
    INDXB   = 'INDXB'
    DREFB   = 'DREFB'
    CALL    = 'CALL'
    CALR    = 'CALR'
    LIBCALL = 'LIBCALL'
    JUMP    = 'JUMP'
    RJUMP   = 'RJUMP'
    JMPFALSE= 'JMPFALSE'
    JMPTRUE = 'JMPTRUE'
    FOR     = 'FOR'
    FORDOWN = 'FORDOWN'
    MKFRAME = 'MKFRAME'
    DELFRAME= 'DELFRAME'
    RET     = 'RET'
    HALT    = 'HALT'
    NEG     = 'NEG'
    INV     = 'INV'
    LOGNOT  = 'LOGNOT'
    ADD     = 'ADD'
    SUB     = 'SUB'
    MUL     = 'MUL'
    DIV     = 'DIV'
    MOD     = 'MOD'
    AND     = 'AND'
    OR      = 'OR'
    XOR     = 'XOR'
    SHL     = 'SHL'
    SHR     = 'SHR'
    EQ      = 'EQ'
    NE      = 'NE'
    LT      = 'LT'
    GT      = 'GT'
    LE      = 'LE'
    GE      = 'GE'
    UMUL    = 'UMUL'
    UDIV    = 'UDIV'
    ULT     = 'ULT'
    UGT     = 'UGT'
    ULE     = 'ULE'
    UGE     = 'UGE'
    JMPEQ   = 'JMPEQ'
    JMPNE   = 'JMPNE'
    JMPLT   = 'JMPLT'
    JMPGT   = 'JMPGT'
    JMPLE   = 'JMPLE'
    JMPGE   = 'JMPGE'
    JMPULT  = 'JMPULT'
    JMPUGT  = 'JMPUGT'
    JMPULE  = 'JMPULE'
    JMPUGE  = 'JMPUGE'
    RMEM    = 'RMEM'
    FILLMEM = 'FILLMEM'
    SKIP    = 'SKIP'

class SMEmitter:
    """
    Intermediate Stack Machine emitter for the Amstrad CPC BAS compiler
    """

    def __init__(self) -> None:
        """ code is (SMI opcode, optional param, optional string prefix to use in output text)"""
        self.code: List[Tuple[str, str, str]] = []
        self.symbol_start = 256
        self.symbols: Dict[int,List[List[int]]] = {}

    def abort(self, message: str) -> None:
        print(f"Fatal error: {message}")
        sys.exit(1)

    def warning(self, message: str) -> None:
        print(f"Warning: {message}")

    def _emit(self, opcode: str, param: str = '', prefix: str = '\t') -> None:
        self.code.append((opcode, param, prefix))

    def remark(self, text: str) -> None:
        self._emit(SMI.REM, text.strip(), prefix='')

    def label(self, text: str) -> None:
        self._emit(SMI.LABEL, text, prefix='')

    def load_num(self, value: str) -> None:
        self._emit(SMI.LDVAL, value)

    def load_addr(self, value: str) -> None:
        self._emit(SMI.LDVAL, value)

    def load_symbol(self, symbol: str) -> None:
        self._emit(SMI.LDMEM, symbol)

    def store(self, variable_name: str) -> None:
        self._emit(SMI.STMEM, variable_name)

    def operate_int(self, op: str) -> None:
        if   op == '+': self._emit(SMI.ADD)
        elif op == '-': self._emit(SMI.SUB)
        elif op == '*': self._emit(SMI.MUL)
        elif op == '/': self._emit(SMI.DIV)
        elif op == '\\': self._emit(SMI.DIV)
        elif op == '%': self._emit(SMI.MOD)
        elif op == 'XOR': self._emit(SMI.XOR)
        elif op == 'AND': self._emit(SMI.AND)
        elif op == 'OR': self._emit(SMI.OR)
        elif op == '=': self._emit(SMI.EQ)
        elif op == '<': self._emit(SMI.LT)
        elif op == '>': self._emit(SMI.GT)
        elif op == '>=': self._emit(SMI.GE)
        elif op == '<=': self._emit(SMI.LE)
        elif op == 'NEG': self._emit(SMI.NEG)
        elif op == 'AT':
            # memory address already loaded so this has no futher effects
            self._emit(SMI.NOP)
        else:
            self.abort(f"Operation {op} is not currently supported with integers")
    
    def operate_real(self, op: str) -> None:
        if op == 'AT':
            # memory address already loaded so this has no futher effects
            self._emit(SMI.NOP)
        self.abort(f"Operation {op} is not currently supported with real numbers")

    def operate_str(self, op: str) -> None:
        if   op == '=':
            self._emit(SMI.LIBCALL, 'STRCOMP')
        elif op == '+':
            self._emit(SMI.LIBCALL, 'STRADD')
        elif op == '<>':
            self._emit(SMI.LIBCALL, 'STRCOMP')
            self._emit(SMI.INC)  # -1 TRUE / 0 FALSE + 1 = NON EQ
        elif op == 'AT':
            # memory address already loaded so this has no futher effects
            self._emit(SMI.NOP)
        else:
            self.abort(f"Operation {op} is not currently supported with strings")

    def expression(self, expression: Expression) -> None:
        for i, (token, type) in enumerate(expression.expr):
            if token.is_int():
                if i > 0: self._emit(SMI.PUSH)
                self.load_num(token.text)
            elif token.is_ident():
                if i > 0: self._emit(SMI.PUSH)
                # check if next operant is @ (get memory address)
                next_at = (i + 1) < len(expression.expr) and expression.expr[i+1][0].text == 'AT'
                if not next_at and type == BASTypes.INT:
                    # only integers are loaded directly, string, reals or memory addresses does not
                    self.load_symbol(token.text)
                else:
                    self._emit(SMI.LDVAL, token.text)          
            else:
                if   type == BASTypes.INT: self.operate_int(token.text)
                elif type == BASTypes.REAL:self.operate_real(token.text)
                elif type == BASTypes.STR: self.operate_str(token.text)
                else:
                    # Expression is bad formed due to errors and operant is still BASTypes.NONE
                    self._emit(SMI.NOP)
    
    def logical_expr(self, expr: Expression, jumplabel: str) -> None:
        self.expression(expr)
        self._emit(SMI.JMPFALSE, jumplabel)     

    def assign(self, variable_name: str, expression: Expression) -> None:
        self.expression(expression)
        if expression.is_str_result():
            # assign of strings means copy memory
            self._emit(SMI.PUSH)
            self._emit(SMI.LDVAL, variable_name)
            self._emit(SMI.LIBCALL, 'STRCOPY')
        elif expression.is_real_result():
            self._emit(SMI.PUSH)
            self._emit(SMI.LDVAL, variable_name)
            self._emit(SMI.LIBCALL, 'REALCOPY')
        else:
            self.store(variable_name)

    def forloop(self, variant: Symbol, limit: Symbol, step: Optional[Expression], looplabel: Symbol, endlabel: Symbol) -> None:
        self.label(looplabel.symbol)
        self.load_symbol(variant.symbol)
        self._emit(SMI.PUSH)
        self.load_symbol(limit.symbol)
        if step is None or step.is_simple():
            self._emit(SMI.FOR, endlabel.symbol)
        else:
            self._emit(SMI.FORDOWN, endlabel.symbol)

    def next(self, variant: Symbol, limit: Symbol, step: Optional[Expression], looplabel: Symbol, endlabel: Symbol) -> None:
        self.load_symbol(variant.symbol)
        if step is None:
            self._emit(SMI.INC)
        else:
            self._emit(SMI.PUSH)
            self.expression(step)
            self._emit(SMI.ADD)
        self.store(variant.symbol)
        self._emit(SMI.JUMP, looplabel.symbol)
        self.label(endlabel.symbol)
    
    def goto(self, label: str) -> None:
        self._emit(SMI.JUMP, label)

    def end(self) -> None:
        self._emit(SMI.LIBCALL, 'END')

    def symbol(self, args: List[Expression]) -> None:
        try:
            if self.symbol_start == 256:
                self.warning("SYMBOL command appears before a SYMBOL AFTER")
            sym = int(args[0].expr[0][0].text, 0)
            self.symbol_start = min(self.symbol_start, sym)
            values: List[str] = []
            for e in args[1:]:
                values.append(e.expr[0][0].text)
        except:
            self.abort("wrong symbol value in SYMBOL command: " + args[0].expr[0][0].text)
        try:
            numbers: List[int] = []
            for v in values:
                numbers.append(int(v, 0))
            if len(numbers) != 8:
                self.abort("wrong number of arguments in SYMBOL command: " + str(values))
            if sym in self.symbols:
                self.symbols[sym].append(numbers)
            else:
                self.symbols[sym] = [numbers]
        except:
            self.abort("wrong value in SYMBOL arguments: " + str(values))
        label = f"_user_symbol_{str(sym)}_{len(self.symbols[sym])}"
        self.load_addr(label)
        self._emit(SMI.PUSH)
        self.load_num(str(sym))
        self._emit(SMI.LIBCALL, 'SYMBOL')

    def symbolafter(self, args: List[Expression]) -> None:
        try:
            value = int(args[0].expr[0][0].text, 0)
            self.symbol_start = value
        except:
            self.abort("wrong value in SYMBOL AFTER: " + args[0].expr[0][0].text)
        self.load_num(str(value))
        self._emit(SMI.PUSH)
        self.load_addr("_user_symbol_table")
        self._emit(SMI.LIBCALL, 'SYMBOL_AFTER')

    def emitsymboltable(self) -> None:
        if self.symbol_start != 256:
            for sym in self.symbols:
                for i,values in enumerate(self.symbols[sym]):
                    self.label(f"_user_symbol_{str(sym)}_{i+1}")
                    strlist = str(values)[1:-1]
                    self._emit(SMI.FILLMEM, strlist)
            self.remark('USER DEFINED SYMBOL TABLE')
            self.label("_user_symbol_table")
            self._emit(SMI.RMEM, f'(256-{self.symbol_start})*8')

    def rtcall(self, fname: str, args: List[Expression] = [], retsym: Optional[Symbol] = None) -> None:
        if retsym is not None:
            # store the address for the result of a function call
            self._emit(SMI.LDVAL, retsym.symbol)
            self._emit(SMI.PUSH)
        if len(args):
            self.expression(args[0])
            for i in range(1,len(args)):
                self._emit(SMI.PUSH)    # previous arg value
                self.expression(args[i])
        self._emit(SMI.LIBCALL, fname)

