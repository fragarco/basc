"""
Emitter object to generate Amstrad CPC Z80 Assembly language in
Maxam/WinAPE style.

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

import baslib
from bastypes import Symbol, SymbolTable

class FWCALL:
    TXT_CLEAR_WINDOW    = "&BB6C"
    TXT_CURSOR_ON       = "&BB81"
    TXT_CURSOR_OFF      = "&BB84"
    SCR_SET_MODE        = "&BC0E"

class ASMEmitter:
    """
    Emitter for Amstrad CPC Z80 Assembly language (Maxam/WinAPE style)
    """

    def __init__(self, outputfile):
        self.outputfile = outputfile
        self.libcode = []
        self.code = []
        self.data = []
        self.npass = 0
        self.symbols = SymbolTable()

    def save_output(self):
        with open(self.outputfile, 'w') as ofd:
            ofd.writelines(self.libcode)
            ofd.writelines(self.code)
            ofd.writelines(self.data)
        return self.outputfile

    def setpass(self, p, symbolstable):
        self.npass = p
        self.symbols = symbolstable

    def emitlibcode(self, code):
        if self.npass > 0:
            self.libcode.append(code + '\n')

    def emitcode(self, code):
        if self.npass > 0:
            self.code.append(code + '\n')

    def emitdata(self, code):
        if self.npass > 0:
            self.data.append(code + '\n')

    def emitstart(self, addr = 0x4000):
        if self.npass > 0:
            self.emitlibcode("org     &%04X" % addr)

    def emitend(self):
        if self.npass > 0:
            self.emitdata("asm_end: jp asm_end")

    def emitlinelabel(self, text):
        self.emitcode('__LINE_' + text + ':')

    def emit_rtcall(self, fun, args = []):
        if self.npass > 0:
            fun_cb = getattr(self, "rtcall_" + fun, None)
            if fun_cb == None:
                print("Emitter error:", fun, "call is not implemented yet")
            else:
                fun_cb(args)

    def rtcall_CLS(self, args):
        self.emitcode("\tpush    hl")
        self.emitcode("\tcall    " + FWCALL.TXT_CLEAR_WINDOW + " ;TXT_CLEAR_WINDOW")
        self.emitcode("\tpop     hl")

    def rtcall_MODE(self, args):
        self.emitcode("\tpush    af")
        self.emitcode("\tld      a,%s" % args[0])
        self.emitcode("\tpush    hl")
        self.emitcode("\tcall    " + FWCALL.SCR_SET_MODE  + " ;SCR_SET_MODE")
        self.emitcode("\tpop     hl")
        self.emitcode("\tpop     af")
