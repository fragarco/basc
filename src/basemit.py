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

class FW_CALL:
    TXT_CLEAR_WINDOW = "&6CBB"

class ASMEmitter:
    """
    Emitter for Amstrad CPC Z80 Assembly language (Maxam/WinAPE style)
    """

    def __init__(self, outputfile):
        self.outputfile = outputfile
        self.code = []

    def save_output(self):
        with open(self.outputfile, 'w') as ofd:
            ofd.writelines(self.code)
        return self.outputfile

    def emit(self, code):
        self.code.append(code + '\n')

    def emitstart(self, addr = 0x4000):
        self.emit("org     &%04X" % addr)

    def emitend(self):
        self.emit("asm_end: jp asm_end")

    def emit_rtcall(self, fun, args = []):
        fun_cb = getattr(self, "rtcall_" + fun, None)
        if fun_cb == None:
            print("Emitter error:", fun, "call is not implemented yet")
        else:
            fun_cb(args)

    def rtcall_CLS(self, args):
        self.emit("push    hl")
        self.emit("call    " + FW_CALL.TXT_CLEAR_WINDOW)
        self.emit("pop     hl")

