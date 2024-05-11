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
from bastypes import SymTypes, Symbol, SymbolTable, TokenType, ErrorCode, Expression, BASTypes

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

        self.cur_token = None
        self.peek_token = None
        self.symbols = SymbolTable()
        self.cur_expr = Expression()

    def abort(self, srcline, message, extrainfo = ""):
        self.errors = self.errors + 1
        filename, linenum, line = self.lexer.get_srccode(srcline)
        filename = os.path.basename(filename)
        if self.verbose:
            print("abort signal from", inspect.stack()[1].function + "()")
        print("Fatal error in %s:%d: %s -> %s %s" % (filename, linenum, line.strip(), message, extrainfo))
        sys.exit(1)
    
    def error(self, srcline, message, extrainfo = ""):
        self.errors = self.errors + 1
        filename, linenum, line = self.lexer.get_srccode(srcline)
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
        self.cur_token
        _, _, line = self.lexer.get_srccode(self.cur_token.srcline)
        self.emitter.emitcode("")
        self.emitter.emitcode("; " + line.strip())

    # SymbolTable management happens only during pass 0, so it is
    # fully created when pass 1 starts and can be used to emit code
    def symtab_addlabel(self, symbol):
        if self.npass == 0:
            if self.symbols.search(symbol.text):
                self.error(symbol.srcline, ErrorCode.LEXISTS)
            else:
                self.symbols.add(symbol, SymTypes.SYMLAB)

    def symtab_addident(self, symbol):
        if self.npass == 0:
            # check if symbol exists (nothing to do)
            entry = self.symbols.search(symbol)
            if entry == None:
                entry = self.symbols.add(symbol, SymTypes.SYMVAR)
            return entry

    def parse(self):
        # lets leave the first line of code ready
        for p in [0, 1]:
            self.npass = p
            self.lexer.reset()
            self.emitter.setpass(p, self.symbols)
            self.emitter.emitstart()
            self.lexer.reset()
            self.cur_token = self.lexer.get_token()
            self.peek_token = self.lexer.get_token()
            self.lines()
            if self.errors:
                print(self.errors, "error(s) in total")
                sys.exit(1)

    # Production rules.

    def lines(self):
        """<lines> ::= EOF | NEWLINE <lines> | <line> <lines>"""
        # Parse all the statements in the program.
        if self.match_current(TokenType.CODE_EOF):
            # End of file
            self.emit_srcline()
            self.emitter.emitend()
        elif self.match_current(TokenType.NEWLINE):
            # Empty lines
            self.next_token()
            self.lines()
        else:
            self.line()
            self.lines()

    def line(self):
        """ <line> := INTEGER NEWLINE | INTEGER <statements> NEWLINE"""
        self.emit_srcline()
        if self.match_current(TokenType.INTEGER):
            self.emitter.emitlabel('LINE' + self.cur_token.text)
            self.next_token()
            if self.match_current(TokenType.NEWLINE):
                 # This was a full line remark (' or REM) removed by the lexer
                 # but we emitted the line number in case a GOTO
                 # or similar statement jumps here
                 self.next_token()
            else:
                self.statements()
                if self.match_current(TokenType.NEWLINE):
                    self.next_token()
        else:
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)

    def statements(self):
         """ <statements>  ::= <statement> [':' <statements>] """
         self.statement()
         if (self.match_current(TokenType.COLON)):
              self.statements()

    def statement(self):
        """  <statement> = ID ':' NEWLINE | ID '=' <expression> | <keyword>"""
        self.cur_expr.reset()
        if self.match_current(TokenType.IDENT):
            symbol = self.cur_token
            self.next_token()
            if self.match_current(TokenType.COLON) and self.match_next(TokenType.NEWLINE):
                self.symtab_addlabel(symbol)
                self.emitter.emitlabel(symbol)
                self.next_token()
            elif self.match_current(TokenType.EQ):
                self.next_token()
                self.expression()
                entry = self.symbols.search(symbol.text)
                if entry == None:
                    entry = self.symtab_addident(symbol.text)
                else:
                    if not self.cur_expr.check_types(entry.valtype):
                        self.error(symbol.srcline, ErrorCode.TYPE)
                        return
                entry.set_value(self.cur_expr)
                self.emitter.emitassign(symbol.text, self.cur_expr)
            else:
                self.error(symbol.srcline, ErrorCode.SYNTAX)
        elif self.cur_token.is_keyword():
            self.keyword()
        else:
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)

    def keyword(self):
        """ <keyword> := COMMAND | FUNCTION """
        keyword_rule = getattr(self, "keyword_" + self.cur_token.text, None)
        if keyword_rule == None:
            self.error(self.cur_token.srcline, ErrorCode.NOKEYW, ": " + self.cur_token.text, )
        else:
            keyword_rule()

    def keyword_CLS(self):
        """ keyword_CLS := CLS [# <expression>]"""
        self.next_token()
        if self.match_current(TokenType.CHANNEL):
            self.next_token()
            self.expression()
        self.emitter.emit_rtcall('CLS', self.cur_expr)
   
    def keyword_MODE(self):
        """ keyword_MODE := MODE <expression> """
        self.next_token()
        self.expression()
        self.emitter.emit_rtcall('MODE', self.cur_expr)


    # Expression rules

    def expression(self):
        """ <expression> ::= <or_term> [XOR <expression>] """
        self.or_term()
        if self.match_current(TokenType.XOR):
            op = self.cur_token
            self.next_token()
            self.expression()
            if not self.cur_expr.pushop(op.text):
                self.error(op.srcline, ErrorCode.TYPE)

    def or_term(self):
        """<or_term> ::= <and_term> [OR <or_term>]"""
        self.and_term()
        if self.match_current(TokenType.AND):
            op = self.cur_token
            self.next_token()
            self.or_term()
            if not self.cur_expr.pushop(op.text):
                self.error(op.srcline, ErrorCode.TYPE)

    def and_term(self):
        """<and_term> ::= <not_term> [AND <and_term>]"""
        self.not_term()
        if self.match_current(TokenType.AND):
            op = self.cur_token
            self.next_token()
            self.and_term()
            if not self.cur_expr.pushop(op.text):
                self.error(ErrorCode.TYPE, op.srcline)

    def not_term(self):
        """<not_term> ::= [NOT] <compare_term>"""
        if self.match_current(TokenType.NOT):
            op = self.cur_token
            self.next_token()
            self.compare_term()
            if not self.cur_expr.pushop(op.text):
                self.error(op.srcline, ErrorCode.TYPE)
        else:
            self.compare_term()

    def compare_term(self):
        """<compare_term> ::= <add_term> [('=','<>'.'>','<','>=','<=')  <compare_term>]"""
        self.add_term()
        if self.cur_token.is_logic_op():
            op = self.cur_token
            self.next_token()
            self.compare_term()
            if not self.cur_expr.pushop(op.text):
                self.error(ErrorCode.TYPE, op.srcline)

    def add_term(self):
        """<add_term> ::= <mod_term> [('+'|'-') <add_term>]"""
        self.mod_term()
        if self.match_current(TokenType.PLUS) or self.match_current(TokenType.MINUS):
            op = self.cur_token
            self.next_token()
            self.add_term()
            if not self.cur_expr.pushop(op.text):
                self.error(op.srcline, ErrorCode.TYPE)

    def mod_term(self):
        """<mod_term> ::= <mult_term> [MOD <mod_term>]"""
        self.mult_term()
        if self.match_current(TokenType.MOD):
            op = self.cur_token
            self.next_token()
            self.mod_term()
            if not self.cur_expr.pushop(op.text):
                self.error(ErrorCode.TYPE)

    def mult_term(self):
        """<mult_term> ::= <negate_term> [('*'|'/'|'\\' <mult_term>] """
        self.negate_term()
        if self.match_current(TokenType.SLASH) or self.match_current(TokenType.LSLASH) or self.match_current(TokenType.ASTERISK):
            op = self.cur_token
            self.next_token()
            self.mult_term()
            if not self.cur_expr.pushop(op.text):
                self.error(op.srcline, ErrorCode.TYPE)

    def negate_term(self):
        """<negate_term> ::= ['-'] <sub_term> """
        if self.match_current(TokenType.MINUS):
            op = self.cur_token
            self.next_token()
            self.sub_term()
            if not self.cur_expr.pushop('NEG'):
                self.error(op.srcline, ErrorCode.TYPE)
        else:
            self.sub_term()

    def sub_term(self):
        """ <sub_term> ::= '(' <expression> ')' | <factor> """
        if self.match_current(TokenType.LPAR):
            partoken = self.cur_token
            self.next_token()
            self.expression()
            if self.match_current(TokenType.RPAR):
                self.next_token()
            else:
                self.error(ErrorCode.SYNTAX, partoken.srcline)
        else:
            self.factor()

    def factor(self):
        """<factor> ::= ID | INTEGER | REAL | STRING | <function>"""
        if self.match_current(TokenType.IDENT):
            sym = self.symbols.search(self.cur_token.text)
            if sym != None:
                if self.cur_expr.pushval(self.cur_token.text, sym.valtype):
                    sym.inc_reads()
                    self.next_token()
                else:
                    self.error(self.cur_token.srcline, ErrorCode.TYPE)
            else:
                self.error(self.cur_token.srcline, ErrorCode.NOIDENT)
        elif self.match_current(TokenType.INTEGER):
            if self.cur_expr.pushval(self.cur_token.text, BASTypes.INT):
                self.next_token()
            else:
                self.error(self.cur_token.srcline, ErrorCode.TYPE)
        elif self.match_current(TokenType.REAL):
            if self.cur_expr.pushval(self.cur_token.text, BASTypes.REAL):
                self.next_token()
            else:
                self.error(self.cur_token.srcline, ErrorCode.TYPE)
        elif self.match_current(TokenType.STRING):
            if self.cur_expr.pushval(self.cur_token.text, BASTypes.STR):
                self.next_token()
            else:
                self.error(self.cur_token.srcline, ErrorCode.TYPE)
        else:
            #TODO functions
            self.error(self.cur_token.srcline, "functions in expressions are not supported yet")
