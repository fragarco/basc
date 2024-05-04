
class BASEmitter:
    """
    An emitter object keeps track of the generated code and outputs it.
    """
    def __init__(self, outputfile):
        self.outputfile = outputfile
        self.code = [""]

    def emit(self, code):
        self.code[-1] = self.code[-1] + code

    def newline(self):
        self.code[-1] = self.code[-1] + '\n'
        self.code.append("")

    def save_output(self):
        with open(self.outputfile, 'w') as ofd:
            ofd.writelines(self.code)
