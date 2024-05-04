import baslex


class ErrorCode:
    NEXT    = "Unexpected NEXT"
    RESUME  = "Unexpected RESUME"
    RETURN  = "Unexpected RETURN"
    WEND    = "Unexpected WEND"
    NONEXT  = "NEXT missing"
    NOWEND  = "WEND missing"
    NORESUME= "RESUME missing"
    NOLINE  = "Line does not exist"
    LINELEN = "Line too long"
    NOOP    = "Operand missing"
    SYNTAX  = "Syntax Error"
    UNKNOWN = "Unknown command"
    DEFFN   = "Unknown user function"
    TYPE    = "Type mismatch"
    DIVZERO = "Division by zero"
    STRFULL = "String space full"
    STRLEN  = "String too long"
    COMPLEX = "String expression too complex"
    OUTRANGE= "Subscript out of range"
    ARRAYDIM= "Array already dimensioned"
    DATAEX  = "DATA exhausted"
    ARGUMENT= "improper argument"
    OVERFLOW= "Overflow"
    MEMFULL = "Memory full"
    INVDIR  = "Invalid direct command"
    DIRECT  = "Direct command found"
    CONTINUE= "Cannot CONTinue"
    EOFMET  = "EOF met"
    FILETYPE= "File type error"
    FILEOPEN= "File already open"
    NOFILE  = "File not open"
    BROKEN  = "Broken in"

class BASParserError(Exception):
    """
    Raised when procesing a file and error are found.
    """
    def __init__(self, message, file = "", line = -1):
        self.message = message
        self.line = line
        self.file = file

    def __str__(self):
        if self.line != -1:
            return "[basparser] Error: %s\n\tfile %s line %d" % (self.message, self.file, self.line)
        else:
            return "[basparser] Error: %s" % self.message

class BASParser:
    """
    A BASParser object keeps track of current token, checks if the code matches the grammar,
    and emits code along the way if an emitter has been set.
    """
    def __init__(self, lexer, emitter):
        self.lexer = lexer
        self.emitter = emitter

        self.symbols = {}           # All variables we have declared so far.
        self.labels_declared = {}   # Keep track of all labels declared
        self.labels_used = {}       # All labels goto'ed, so we know if they exist or not.


    def abort(self, message):
        raise BASParserError(message)
    
    def error(self, message):
        filename, linenum, line = self.lexer.get_currentcode()
        print("%s:%d: %s -> %s" % (filename, linenum, line.strip(), message))
        while not self.match_current(baslex.TokenType.NEWLINE):
            self.next_token()

    def match_current(self, tktype):
        """Return true if the current token matches."""
        return tktype == self.cur_token.type

    def match_next(self, tktype):
        """Return true if the next token matches."""
        return tktype == self.peek_token.tktype

    def match(self, tktype):
        """Try to match current token. If not, error. Advances the current token."""
        if not self.match_current(tktype):
           return False
        self.next_token()
        return True

    def next_token(self):
        """Advances the current token."""
        self.cur_token = self.peek_token
        self.peek_token = self.lexer.get_token()
        # No need to worry about passing the CODE_EOF, lexer handles that.

    def is_comparison_operator(self):
        """Return true if the current token is a comparison operator."""
        return self.match_current(baslex.TokenType.GT) or self.match_current(baslex.TokenType.GTEQ) or self.match_current(baslex.TokenType.LT) or self.match_current(baslex.TokenType.LTEQ) or self.match_current(baslex.TokenType.EQEQ) or self.match_current(baslex.TokenType.NOTEQ)

    def emitcurrentline(self):
        _, _, line = self.lexer.get_currentcode()
        self.emitter.emit("; " + line.strip())
        self.emitter.newline()

    def parse(self):
        # lets leave the first line of code ready
        self.emitcurrentline()
        self.cur_token = self.lexer.get_token()
        self.peek_token = self.lexer.get_token()
        self.program()

    # Production rules.

    def program(self):
        """program ::= CODE_EOF | NEWLINE program | codeline {program}"""

        # Parse all the statements in the program.
        if self.match_current(baslex.TokenType.CODE_EOF):
            pass
        elif self.match_current(baslex.TokenType.NEWLINE):
            self.next_token()
            self.program()
        else:
            self.codeline()
            self.program()

    def codeline(self):
        """ codeline ::= NUMBER code """
        if self.match_current(baslex.TokenType.NUMBER):
            self.emitter.emit("!%s [%s] " % (self.cur_token.type, self.cur_token.text))
            self.next_token()
            self.code()
            self.emitcurrentline()
        else:
            self.error(ErrorCode.SYNTAX)

    def code(self):
        """ code ::= NEWLINE | : code | statement code """
        if self.match_current(baslex.TokenType.NEWLINE):
            self.emitter.newline()
            self.next_token()
        elif self.match_current(baslex.TokenType.COLON):
            self.emitter.emit(": ")
            self.next_token()
            self.code()
        else:
            self.statement()
            self.code()

    def statement(self):
        if self.match_current(baslex.TokenType.NEWLINE):
            self.emitter.newline()
        elif self.match_current(baslex.TokenType.COLON):
            self.emitter.newline()
        else:
            self.emitter.emit("@%s [%s] " % (self.cur_token.type, self.cur_token.text))
            self.next_token()
            self.statement()