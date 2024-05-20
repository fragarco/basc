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

        self.cur_token = None
        self.peek_token = None
        self.symbols = SymbolTable()
        self.cur_expr = Expression()
        self.expr_stack = []
        self.temp_vars = 0

    def abort(self, message):
        if self.verbose:
            print("abort signal from", inspect.stack()[1].function + "()")
        print(f"Fatal error: {message}")
        sys.exit(1)
    
    def error(self, srcline, message, extrainfo = ""):
        self.errors = self.errors + 1
        filename, linenum, line = self.lexer.get_srccode(srcline)
        filename = os.path.basename(filename)
        if self.verbose:
            print("error from", inspect.stack()[1].function + "()")
        print("Error in %s:%d: %s -> %s %s" % (filename, linenum, line.strip(), message, extrainfo))
        while not self.match_current(TokenType.NEWLINE):
            self.next_token()

    def get_curcode(self):
        _, _, line = self.lexer.get_srccode(self.cur_token.srcline)
        return line 
    
    def get_linelabel(self, num):
        return f'__label_line_{num}'

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

    def symtab_name2type(self, symname):
        forcedtype = BASTypes.NONE
        symname = symname.lower()
        if symname.endswith('$'):
            symname = symname.replace('$', 'tstr')
            forcedtype = BASTypes.STR
        elif symname.endswith('!'):
            symname = symname.replace('!', 'treal')
            forcedtype = BASTypes.REAL
        elif symname.endswith('%'): 
            symname = symname.replace('%', 'tint')
            forcedtype = BASTypes.INT
        return symname, forcedtype
        
    def symtab_addlabel(self, symname, srcline):
        if self.symbols.search(symname):
            self.error(srcline, ErrorCode.LEXISTS)
        else:
            return self.symbols.add(symname, SymTypes.SYMLAB)

    def symtab_addident(self, symname, srcline, expr):
        symname, forcedtype = self.symtab_name2type(symname)
        entry = self.symbols.search(symname)
        if entry == None:
            entry = self.symbols.add(symname, SymTypes.SYMVAR)
            # force type if it is included in variable name so
            # check_types will ensure it matches with expression type
            entry.valtype = forcedtype
        if entry.check_types(expr.type):
            entry.set_value(expr)
        else:
            self.error(srcline, ErrorCode.TYPE)
            return None
        return entry

    def symtab_search(self, symname):
        symname, _ = self.symtab_name2type(symname)
        return self.symbols.search(symname)

    def symtab_newtemp(self, srcline, expr):
        sname = f"tmpident{self.temp_vars:03d}"
        entry = self.symtab_addident(sname, srcline, expr)
        entry.temporal = True
        self.temp_vars = self.temp_vars + 1
        return entry

    def push_curexpr(self):
        self.expr_stack.append(self.cur_expr)
        self.cur_expr = Expression()

    def pop_curexpr(self):
        if len(self.expr_stack) > 0:
            self.cur_expr = self.expr_stack[-1]
            self.expr_stack = self.expr_stack[:-1]
        else:
            self.abort("internal error processing expressions")

    def reset_curexpr(self):
        self.cur_expr = Expression()

    def parse(self):
        self.lexer.reset()
        self.cur_token = self.lexer.get_token()
        self.peek_token = self.lexer.get_token()
        self.temp_vars = 0
        self.errors = 0
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
            pass
        elif self.match_current(TokenType.NEWLINE):
            # Empty lines
            self.next_token()
            self.lines()
        else:
            self.line()
            self.lines()

    def line(self):
        """ <line> := INTEGER NEWLINE | INTEGER <statements> NEWLINE"""
        if self.match_current(TokenType.INTEGER):
            self.emitter.remark(self.get_curcode())
            self.emitter.label(self.get_linelabel(self.cur_token.text))
            self.next_token()
            if self.match_current(TokenType.NEWLINE):
                 # This was a full line remark (' or REM) removed by the lexer
                 self.next_token()
            else:
                self.statements()
                if self.match_current(TokenType.NEWLINE):
                    self.next_token()
                else:
                    self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
        else:
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)

    def statements(self):
         """ <statements>  ::= <statement> [':' <statements>] """
         self.statement()
         if (self.match_current(TokenType.COLON)):
              self.statements()

    def statement(self):
        """  <statement> = ID ':' NEWLINE | ID '=' <expression> | <keyword>"""
        self.reset_curexpr()
        if self.match_current(TokenType.IDENT):
            symbol = self.cur_token
            self.next_token()
            if self.match_current(TokenType.COLON) and self.match_next(TokenType.NEWLINE):
                self.symtab_addlabel(symbol.text, symbol.srcline)
                self.emitter.label(symbol.text)
                self.next_token()
            elif self.match_current(TokenType.EQ):
                self.next_token()
                self.expression()
                entry = self.symtab_addident(symbol.text, symbol.srcline, self.cur_expr)
                if  entry != None:
                    self.emitter.expression(self.cur_expr)
                    self.emitter.store(entry.symbol)
            else:
                self.error(symbol.srcline, ErrorCode.SYNTAX)
        elif self.cur_token.is_keyword():
            self.keyword()
        else:
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)

    def keyword(self):
        """ <keyword> := COMMAND | FUNCTION """
        fname = self.cur_token.text.replace('$', 'S').upper()
        keyword_rule = getattr(self, "command_" + fname, None)
        if keyword_rule == None:
            keyword_rule = getattr(self, "function_" + fname, None)
        if keyword_rule == None:
            self.error(self.cur_token.srcline, ErrorCode.NOKEYW, ": " + self.cur_token.text)
        else:
            keyword_rule()

    def command_CLS(self):
        """ <command_CLS> := CLS [<arg_channel>] """
        self.next_token()
        args = [Expression.int('0')]
        if self.match_current(TokenType.CHANNEL):
            self.push_curexpr()
            self.arg_channel()
            args = [self.cur_expr]
            self.pop_curexpr()
        self.emitter.rtcall('CLS', args)

    def command_GOTO(self):
        """ <command_GOTO> := NUMBER | LABEL"""
        # if the label doesn't exit, the assembler will fail
        # this allow us to jump to a forward label/line
        self.next_token()
        args = []
        if self.match_current(TokenType.INTEGER):
            # jump to a line number
            label = self.get_linelabel(self.cur_token.text)
            self.emitter.goto(label)
            self.next_token()
        elif self.match_current(TokenType.IDENT):
            self.emitter.goto(self.cur_token.text)
            self.next_token()
        else:
            self.error(line, ErrorCode.SYNTAX)

    def command_MODE(self):
        """ command_MODE := MODE <arg_int> """
        self.next_token()
        self.push_curexpr()
        self.arg_int()
        self.emitter.rtcall('MODE', [self.cur_expr])      
        self.pop_curexpr()

    def command_PRINT(self):
        """ command_PRINT := PRINT <arg_str> """
        self.next_token()
        self.push_curexpr()
        self.arg_str()
        self.emitter.rtcall('PRINT', [self.cur_expr])      
        self.pop_curexpr()

    # Argument rules

    def arg_channel(self):
        """<arg_channel> = #<expression>.t == INT"""
        line = self.cur_token.srcline
        if self.match_current(TokenType.CHANNEL):
            self.next_token()
            self.expression()
            if not self.cur_expr.is_int():
                self.error(line, ErrorCode.TYPE)
        else:
            self.error(line, ErrorCode.SYNTAX)

    def arg_int(self):
        """<arg_int> = #<expression>.t == INT"""
        line = self.cur_token.srcline
        self.expression()
        if self.cur_expr.is_empty():
            self.error(line, ErrorCode.SYNTAX)
        if not self.cur_expr.is_int():
            self.error(line, ErrorCode.TYPE)

    def arg_real(self):
        """<arg_real> = #<expression>.t == REAL"""
        line = self.cur_token.srcline
        self.expression()
        if self.cur_expr.is_empty():
            self.error(line, ErrorCode.SYNTAX)
        if not self.cur_expr.is_real():
            self.error(line, ErrorCode.TYPE)

    def arg_str(self):
        """<arg_str> = #<expression>.t == STR"""
        line = self.cur_token.srcline
        self.expression()
        if self.cur_expr.is_empty():
            self.error(line, ErrorCode.SYNTAX)
        if not self.cur_expr.is_str():
            self.error(line, ErrorCode.TYPE)

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
            sym = self.symtab_search(self.cur_token.text)
            if sym != None:
                if self.cur_expr.pushval(sym.symbol, sym.valtype):
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
            if self.cur_expr.is_str() or self.cur_expr.is_none():
                # create a constant variable to assign the string literal and 
                # add that variable to the expression
                strexpr = Expression()
                strexpr.pushval(self.cur_token.text, BASTypes.STR)
                sym = self.symtab_newtemp(self.cur_token.srcline, strexpr)
                self.cur_expr.pushval(sym.symbol, BASTypes.STR)
                self.next_token()
            else:
                self.error(self.cur_token.srcline, ErrorCode.TYPE)
        else:
            fname = self.cur_token.text.replace('$', 'S').upper()
            function_rule = getattr(self, "function_" + fname, None)
            if function_rule == None:
                self.error(self.cur_token.srcline, f"function {self.cur_token.text} is not supported yet")
            else:
                function_rule()
