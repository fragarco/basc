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
from bastypes import Symbol, SymbolTable, Expression, BASTypes

class ISMEmitter:
    """
    Intermediate Stack Machine emitter for the Amstrad CPC BAS compiler
    """

    def __init__(self):
        self.code = []

    def abort(self, message):
        print(message)
        sys.exit(1)

    def load(self, value):
        self.code.append(f'LOAD {value}')

    def store(self, variable_name):
        self.code.append(f'STORE {variable_name}')

    def operate(self, op):
        if   op == '+': self.code.append('ADD')
        elif op == '-': self.code.append('SUB')
        elif op == '*': self.code.append('MUL')
        elif op == '/': self.code.append('DIV')
        elif op == '\\': self.code.append('DIV')
        else:
            self.abort(f"Operation {op} is not currently supported by the emitter")
    
    def call(self, function_name, *args):
        arg_string = ', '.join(str(arg) for arg in args)
        self.code.append(f'CALL {function_name}, {arg_string}')

    def ret(self, value=None):
        if value is not None:
            self.code.append(f'RET {value}')
        else:
            self.code.append('RET')
