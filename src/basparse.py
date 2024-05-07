"""
Syntactic analyzer of Amstrad locomotive BASIC code. It support some
basic enhacements like the use of labels instead of line number in
GOTO, GOSUB and THEN/ELSE sentences.

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

import baslex
import inspect

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
    NOKEYW   = "Keyword not implemented"

class BASParserError(Exception):
    """
    Raised when procesing a file and error are found.
    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class BASParser:
    """
    A BASParser object keeps track of current token, checks if the code matches the grammar,
    and emits code along the way if an emitter has been set.
    """
    def __init__(self, lexer, emitter, verbose):
        self.lexer = lexer
        self.emitter = emitter
        self.verbose = verbose
        self.errors = 0

        self.symbols = {}           # All variables we have declared so far.
        self.labels_declared = {}   # Keep track of all labels declared
        self.labels_used = {}       # All labels goto'ed, so we know if they exist or not.
        self.expr_stack = []

    def abort(self, message, extrainfo = ""):
        self.errors = self.errors + 1
        filename, linenum, line = self.lexer.get_currentcode()
        if self.verbose:
            print("abort signal from", inspect.stack()[1].function + "()")
        errmsg = "Fatal error in %s:%d: %s -> %s %s" % (filename, linenum, line.strip(), message, extrainfo)
        raise BASParserError(errmsg)
    
    def error(self, message, extrainfo = ""):
        self.errors = self.errors + 1
        filename, linenum, line = self.lexer.get_currentcode()
        if self.verbose:
            print("error from", inspect.stack()[1].function + "()")
        print("%s:%d: %s -> %s %s" % (filename, linenum, line.strip(), message, extrainfo))
        while not self.match_current(baslex.TokenType.NEWLINE):
            self.next_token()

    def match_current(self, tktype):
        """Return true if the current token matches."""
        return tktype == self.cur_token.type

    def match_next(self, tktype):
        """Return true if the next token matches."""
        return tktype == self.peek_token.type

    def next_token(self):
        """Advances the current token."""
        self.cur_token = self.peek_token
        self.peek_token = self.lexer.get_token()
        if self.verbose:
            print("call from", inspect.stack()[1].function + "()",
                "moving current token to ->",
                None if self.cur_token == None else self.cur_token.type,
                None if self.cur_token == None else self.cur_token.text
            )

    def emit_srcline(self):
        _, _, line = self.lexer.get_currentcode()
        self.emitter.emit("; " + line.strip())

    def parse(self):
        # lets leave the first line of code ready
        self.emitter.emitstart()
        self.emit_srcline()
        self.cur_token = self.lexer.get_token()
        self.peek_token = self.lexer.get_token()
        self.program()

    # Production rules.

    def program(self):
        """program := CODE_EOF | NEWLINE program | codeline program"""
        # Parse all the statements in the program.
        if self.match_current(baslex.TokenType.CODE_EOF):
            self.emitter.emitend()
        elif self.match_current(baslex.TokenType.NEWLINE):
            self.next_token()
            self.program()
        else:
            self.codeline()
            self.emit_srcline()
            self.program()

    def codeline(self):
        """ codeline :=  NUMBER statement """
        if self.match_current(baslex.TokenType.NUMBER):
            self.next_token()
            self.statement()
        else:
            self.error(ErrorCode.SYNTAX)

    def statement(self):
        """ statement = NEWLINE | keyword (NEWLINE | ':' statement) """
        if self.match_current(baslex.TokenType.NEWLINE):
            # for example a full line comment
            self.next_token()
        elif self.cur_token.is_keyword():
            self.keyword()
            if self.match_current(baslex.TokenType.COLON):
                self.next_token()
                self.statement()
            elif self.match_current(baslex.TokenType.NEWLINE):
                self.next_token()
            else:
                self.error(ErrorCode.SYNTAX)
        else:
            self.error(ErrorCode.UNKNOWN)

    def keyword(self):
        """ keyword := keyword_KEYWORD"""
        keyword_rule = getattr(self, "keyword_" + self.cur_token.text, None)
        if keyword_rule == None:
            self.error(ErrorCode.NOKEYW, ": " + self.cur_token.text)
        else:
            keyword_rule()

    def keyword_CLS(self):
        """ keyword_CLS := CLS [# expr_int]"""
        if self.match_next(baslex.TokenType.STREAM):
            self.next_token()
            self.next_token()
            self.expr_stack = []
            self.expr_int()
        self.emitter.emit_rtcall('CLS', self.expr_stack)
   
    def expr_int(self):
        """ expr_int := term_int ('+' term_int | '-' term_int)* """
        self.term_int()
        while True:
            if self.match_current(baslex.TokenType.PLUS) or self.match_current(baslex.TokenType.MINUS):
                op = self.cur_token
                self.next_token()
                self.term_int()
                self.expr_stack.append(op.text)
            else:
                break
        if self.verbose: print("Int expression =", self.expr_stack)

    def term_int(self):
        """ term_int := factor_int ('*' factor_int | '/' factor_int)* """
        self.factor_int()
        while True:
            if self.match_current(baslex.TokenType.ASTERISK) or \
               self.match_current(baslex.TokenType.SLASH) or \
               self.match_current(baslex.TokenType.LSLASH):
                op = self.cur_token
                self.next_token()
                self.factor_int()
                self.expr_stack.append(op.text)
            else:
                break

    def factor_int(self):
        """ factor_int := (expr_int) | factor_int MOD factor_int | NUMBER | IDENT """
        # TODO type checking
        if self.match_current(baslex.TokenType.LPAR):
            self.next_token()
            self.expr_int()
            if self.match_current(baslex.TokenType.RPAR):
                self.next_token()
            else:
                self.abort(ErrorCode.SYNTAX)
        elif self.match_current(baslex.TokenType.NUMBER):
            self.expr_stack.append(self.cur_token.text)
            self.next_token()
        elif self.match_current(baslex.TokenType.IDENT):
            self.expr_stack.append(self.cur_token.text)
            self.next_token()
        else:
            self.abort(ErrorCode.SYNTAX)

        if self.match_current(baslex.TokenType.MOD):
            op = self.cur_token
            self.next_token()
            self.factor_int()
            self.expr_stack.append(op.text)