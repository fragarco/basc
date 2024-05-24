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
from typing import List, Tuple
from bastypes import Expression

class SMI:
    """ Stack Machine Instructions """
    NOP     = 'NOP'
    REM     = 'REM'
    LABEL   = 'LABEL'
    PUSH    = 'PUSH'
    CLEAR   = 'CLEAR'
    DROP    = 'DROP'
    LDVAL   = 'LDVAL'
    LDADDR  = 'LDADDR'
    LDLREF  = 'LDLREF'
    LDGLOB  = 'LDGLOB'
    LDLOCL  = 'LDLOCL'
    STGLOB  = 'STGLOB'
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
        self._emit(SMI.LDADDR, value)

    def load_symbol(self, symbol: str) -> None:
        self._emit(SMI.LDGLOB, symbol)

    def store(self, variable_name: str) -> None:
        self._emit(SMI.STGLOB, variable_name)

    def operate(self, op: str) -> None:
        if   op == '+': self._emit(SMI.ADD)
        elif op == '-': self._emit(SMI.SUB)
        elif op == '*': self._emit(SMI.MUL)
        elif op == '/': self._emit(SMI.DIV)
        elif op == '\\': self._emit(SMI.DIV)
        elif op == '%': self._emit(SMI.MOD)
        elif op == 'XOR': self._emit(SMI.XOR)
        elif op == 'AND': self._emit(SMI.AND)
        elif op == 'OR': self._emit(SMI.OR)
        else:
            self.abort(f"Operation {op} is not currently supported by the emitter")
    
    def expression(self, expression: Expression) -> None:
        for i, token in enumerate(expression.expr):
            if token.is_int():
                if i > 0: self._emit(SMI.PUSH)
                self.load_num(token.text)
            elif token.is_ident():
                if i > 0: self._emit(SMI.PUSH)
                if expression.is_str():
                    # memory address
                    self._emit(SMI.LDADDR, token.text)
                else:
                    # stored value
                    self.load_symbol(token.text)
            else:
                self.operate(token.text)
    
    def assign(self, variable_name: str, expression: Expression) -> None:
        self.expression(expression)
        if expression.is_str():
            # assign of strings means copy memory
            self._emit(SMI.PUSH)
            self._emit(SMI.LDADDR, variable_name)
            self._emit(SMI.LIBCALL, 'STRCOPY')
        else:
            self.store(variable_name)

    def goto(self, label: str) -> None:
        self._emit(SMI.JUMP, label)

    def end(self) -> None:
        self._emit(SMI.JUMP, '0')

    def rtcall(self, fname: str, args: List[Expression] = []) -> None:
        if len(args):
            self.expression(args[0])
            for i in range(1,len(args)):
                self._emit(SMI.PUSH)    # previous arg value
                self.expression(args[i])
        self._emit(SMI.LIBCALL, fname)

