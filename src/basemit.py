
class ASMEmitter:
    """
    An emitter object keeps track of the generated code and outputs it
    as Amstra CPC Z80 Assembly language (Maxam/WinAPE style)
    """
    def __init__(self, outputfile):
        self.outputfile = outputfile
        self.code = [""]

    def save_output(self):
        with open(self.outputfile, 'w') as ofd:
            ofd.writelines(self.code)

    def newline(self):
        self.code[-1] = self.code[-1] + '\n'
        self.code.append("")

    def emit(self, code):
        self.code[-1] = self.code[-1] + code

    def emit_rtcall(self, fun, args = []):
        fun_cb = getattr(self, "rtcall_" + fun, None)
        if fun_cb == None:
            print("Emitter error:", fun, "call is not implemented yet")
        else:
            fun_cb(args)


