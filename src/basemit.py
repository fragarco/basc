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
from typing import List, Tuple, Optional
from bastypes import Expression, Symbol

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
    SKIP    = 'SKIP'

class SMEmitter:
    """
    Intermediate Stack Machine emitter for the Amstrad CPC BAS compiler
    """

    def __init__(self) -> None:
        """ code is (SMI opcode, optional param, optional string prefix to use in output text)"""
        self.code: List[Tuple[str, str, str]] = []

    def abort(self, message: str) -> None:
        print(f"Fatal error: {message}")
        sys.exit(1)

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
        else:
            self.abort(f"Operation {op} is not currently supported with integers")
    
    def operate_real(self, op: str) -> None:
        self.abort(f"Operation {op} is not currently supported with real numbers")

    def operate_str(self, op: str) -> None:
        if   op == '=':
            self._emit(SMI.LIBCALL, 'STRCOMP')
        else:
            self.abort(f"Operation {op} is not currently supported with strings")

    def expression(self, expression: Expression) -> None:
        for i, token in enumerate(expression.expr):
            if token.is_int():
                if i > 0: self._emit(SMI.PUSH)
                self.load_num(token.text)
            elif token.is_ident():
                if i > 0: self._emit(SMI.PUSH)
                if expression.is_str():
                    # memory address
                    self._emit(SMI.LDVAL, token.text)
                else:
                    # stored value
                    self.load_symbol(token.text)
            else:
                if   expression.is_int(): self.operate_int(token.text)
                elif expression.is_real(): self.operate_real(token.text)
                elif expression.is_str(): self.operate_str(token.text)
                else:
                    self.abort(f"Expression has not a valid type (integer, real, string)")
    
    def logical_expr(self, expr: Expression, jumplabel: str) -> None:
        self.expression(expr)
        self._emit(SMI.JMPFALSE, jumplabel)     

    def assign(self, variable_name: str, expression: Expression) -> None:
        self.expression(expression)
        if expression.is_str():
            # assign of strings means copy memory
            self._emit(SMI.PUSH)
            self._emit(SMI.LDVAL, variable_name)
            self._emit(SMI.LIBCALL, 'STRCOPY')
        else:
            self.store(variable_name)

    def goto(self, label: str) -> None:
        self._emit(SMI.JUMP, label)

    def end(self) -> None:
        self._emit(SMI.RET)

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

