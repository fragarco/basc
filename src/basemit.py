
class FW_CALL:
    TXT_CLEAR_WINDOW = "&6CBB"

class ASMEmitter:
    """
    An emitter object keeps track of the generated code and outputs it
    as Amstra CPC Z80 Assembly language (Maxam/WinAPE style)
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

