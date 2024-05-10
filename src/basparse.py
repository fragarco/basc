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

import sys
import os
import baslex
import inspect
from bastypes import Symbol, SymbolTable, TokenType, ErrorCode

class BASParser:
    """
    A BASParser object keeps track of current token, checks if the code matches the grammar,
    and emits code along the way if an emitter has been set.
    To resolve forward declarations (jump points), the parser does two passes. In the
    first pass, the emitter doesn't really emit any code but this allows the parser
    to construct the whole symbols table.
    """
    def __init__(self, lexer, emitter, verbose):
        self.lexer = lexer
        self.emitter = emitter
        self.verbose = verbose
        self.errors = 0
        self.npass = 0

        self.symbols = SymbolTable()
        self.expr_stack = []

    def abort(self, message, extrainfo = ""):
        self.errors = self.errors + 1
        filename, linenum, line = self.lexer.get_currentcode()
        filename = os.path.basename(filename)
        if self.verbose:
            print("abort signal from", inspect.stack()[1].function + "()")
        print("Fatal error in %s:%d: %s -> %s %s" % (filename, linenum, line.strip(), message, extrainfo))
        sys.exit(1)
    
    def error(self, message, extrainfo = ""):
        self.errors = self.errors + 1
        filename, linenum, line = self.lexer.get_currentcode()
        filename = os.path.basename(filename)
        if self.verbose:
            print("error from", inspect.stack()[1].function + "()")
        print("error in %s:%d: %s -> %s %s" % (filename, linenum, line.strip(), message, extrainfo))
        while not self.match_current(TokenType.NEWLINE):
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
        self.emitter.emitcode("")
        self.emitter.emitcode("; " + line.strip())

    def parse(self):
        # lets leave the first line of code ready
        for p in [0, 1]:
            self.npass = p
            self.lexer.reset()
            self.emitter.setpass(p, self.symbols)
            self.emitter.emitstart()
            self.emit_srcline()
            self.lexer.reset()
            self.cur_token = self.lexer.get_token()
            self.peek_token = self.lexer.get_token()
            self.program()
            if self.errors:
                print(self.errors, "error(s) in total")
                sys.exit(1)

    # Production rules.

    def program(self):
        """program := CODE_EOF | NEWLINE program | codeline program"""
        # Parse all the statements in the program.
        if self.match_current(TokenType.CODE_EOF):
            self.emitter.emitend()
        elif self.match_current(TokenType.NEWLINE):
            self.next_token()
            self.program()
        else:
            self.codeline()
            self.emit_srcline()
            self.program()

    def codeline(self):
        """ codeline :=  NUMBER statement """
        if self.match_current(TokenType.NUMBER):
            self.emitter.emitcode('__LINE_' + self.cur_token.text + ':')
            self.next_token()
            self.statement()
        else:
            self.error(ErrorCode.SYNTAX)

    def statement(self):
        """ statement = NEWLINE | keyword (NEWLINE | ':' statement) """
        if self.match_current(TokenType.NEWLINE):
            # for example a full line comment
            self.next_token()
        elif self.cur_token.is_keyword():
            self.keyword()
            if self.match_current(TokenType.COLON):
                self.next_token()
                self.statement()
            elif self.match_current(TokenType.NEWLINE):
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
        self.next_token()
        if self.match_current(TokenType.STREAM):
            self.next_token()
            self.expr_stack = []
            self.expr_int()
        self.emitter.emit_rtcall('CLS', self.expr_stack)
   
    def keyword_MODE(self):
        """ keyword_MODE := MODE expr_int """
        self.next_token()
        self.expr_stack = []
        self.expr_int()
        self.emitter.emit_rtcall('MODE', self.expr_stack)

    def expr_int(self):
        """ expr_int := term_int ('+' term_int | '-' term_int)* """
        self.term_int()
        while True:
            if self.match_current(TokenType.PLUS) or self.match_current(TokenType.MINUS):
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
            if self.match_current(TokenType.ASTERISK) or \
               self.match_current(TokenType.SLASH) or \
               self.match_current(TokenType.LSLASH):
                op = self.cur_token
                self.next_token()
                self.factor_int()
                self.expr_stack.append(op.text)
            else:
                break

    def factor_int(self):
        """ factor_int := (expr_int) | factor_int MOD factor_int | NUMBER | IDENT """
        # TODO type checking
        if self.match_current(TokenType.LPAR):
            self.next_token()
            self.expr_int()
            if self.match_current(TokenType.RPAR):
                self.next_token()
            else:
                self.abort(ErrorCode.SYNTAX)
        elif self.match_current(TokenType.NUMBER):
            self.expr_stack.append(self.cur_token.text)
            self.next_token()
        elif self.match_current(TokenType.IDENT):
            self.expr_stack.append(self.cur_token.text)
            self.next_token()
        else:
            self.abort(ErrorCode.SYNTAX)

        if self.match_current(TokenType.MOD):
            op = self.cur_token
            self.next_token()
            self.factor_int()
            self.expr_stack.append(op.text)