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
from typing import List, Optional, Tuple
from baslex import BASLexer
from basemit import SMEmitter
from bastypes import SymTypes, Symbol, SymbolTable, Token, TokenType, ErrorCode, Expression, BASTypes

class BASParser:
    """
    A BASParser object keeps track of current token, checks if the code matches the grammar,
    and emits code along the way if an emitter has been set.
    To resolve forward declarations (jump points), the parser does two passes. In the
    first pass, the emitter doesn't really emit any code but this allows the parser
    to construct the whole symbols table.
    """
    def __init__(self, lexer: BASLexer, emitter: SMEmitter, verbose: bool) -> None:
        self.lexer = lexer
        self.emitter = emitter
        self.verbose = verbose
        self.errors = 0

        self.cur_token: Optional[Token] = None
        self.peek_token: Optional[Token] = None
        self.symbols = SymbolTable()
        self.cur_expr = Expression()
        self.expr_stack: List[Expression] = []
        self.temp_vars: int = 0

    def abort(self, message: str) -> None:
        print(f"Fatal error: {message}")
        sys.exit(1)
    
    def error(self, srcline: int, message: str, extrainfo: str = "") -> None:
        self.errors = self.errors + 1
        filename, linenum, line = self.lexer.get_srccode(srcline)
        filename = os.path.basename(filename)
        print(f"Error in {filename}:{linenum}: {line.strip()} -> {message} {extrainfo}")
        while not self.match_current(TokenType.NEWLINE):
            self.next_token()

    def get_curcode(self) -> str:
        assert self.cur_token is not None
        _, _, line = self.lexer.get_srccode(self.cur_token.srcline)
        return line 
    
    def get_linelabel(self, num: str) -> str:
        return f'__label_line_{num}'

    def match_current(self, tktype: TokenType) -> bool:
        """Return true if the current token matches."""
        assert self.cur_token is not None
        return tktype == self.cur_token.type

    def match_next(self, tktype: TokenType) -> bool:
        """Return true if the next token matches."""
        assert self.peek_token is not None
        return tktype == self.peek_token.type

    def next_token(self) -> None:
        """Advances the current token."""
        self.cur_token = self.peek_token
        self.peek_token = self.lexer.get_token()

    def rollback_token(self) -> None:
        """ Goes back to the previous token."""
        self.peek_token = self.cur_token
        self.cur_token = self.lexer.rollback()

    def symtab_name2type(self, symname: str) -> Tuple[str, BASTypes]:
        """ Lets enforce variable types """
        forcedtype = BASTypes.NONE
        symname = 'var' + symname.lower()
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
        
    def symtab_addlabel(self, symname: str, srcline: int) -> Optional[Symbol]:
        if self.symbols.search(symname):
            self.error(srcline, ErrorCode.LEXISTS)
            return None
        else:
            return self.symbols.add(symname, SymTypes.SYMLAB)

    def symtab_addident(self, symname: str, srcline: int, expr: Expression) -> Optional[Symbol]:
        symname, forcedtype = self.symtab_name2type(symname)
        entry = self.symbols.search(symname)
        if entry is None:
            entry = self.symbols.add(symname, SymTypes.SYMVAR)
            # force type if it is included in variable name so
            # check_types will ensure it matches with expression type
            entry.valtype = forcedtype
        if entry.check_types(expr.restype):
            entry.set_value(expr)
            return entry
        else:
            self.error(srcline, ErrorCode.TYPE)
            return None

    def symtab_search(self, symname: str) -> Optional[Symbol]:
        symname, _ = self.symtab_name2type(symname)
        return self.symbols.search(symname)

    def symtab_newtmpvar(self, srcline: int, expr: Expression) -> Optional[Symbol]:
        sname = f"tmp{self.temp_vars:03d}"
        entry = self.symtab_addident(sname, srcline, expr)
        if entry is not None:
            entry.temporal = True
            self.temp_vars = self.temp_vars + 1
        return entry

    def symtab_newtmplabel(self, srcline: int) -> Optional[Symbol]:
        sname = f"labeltmp{self.temp_vars:03d}"
        entry = self.symtab_addlabel(sname, srcline)
        if entry is not None:
            entry.temporal = True
            self.temp_vars = self.temp_vars + 1
        return entry

    def push_curexpr(self) -> None:
        self.expr_stack.append(self.cur_expr)
        self.cur_expr = Expression()

    def pop_curexpr(self) -> None:
        if len(self.expr_stack) > 0:
            self.cur_expr = self.expr_stack[-1]
            self.expr_stack = self.expr_stack[:-1]
        else:
            self.abort("internal error processing expressions")

    def reset_curexpr(self) -> None:
        self.cur_expr = Expression()

    def parse(self) -> None:
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

    def lines(self) -> None:
        """<lines> ::= EOF | NEWLINE <lines> | <line> <lines>"""
        assert self.cur_token is not None
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

    def line(self) -> None:
        """ <line> := INTEGER NEWLINE | INTEGER ID: NEWLINE | INTEGER <statements> NEWLINE"""
        assert self.cur_token is not None
        if self.match_current(TokenType.INTEGER):
            self.emitter.remark(self.get_curcode())
            self.emitter.label(self.get_linelabel(self.cur_token.text))
            self.next_token()
            if self.match_current(TokenType.NEWLINE):
                # This was a full line remark (' or REM) removed by the lexer
                self.next_token()
            elif self.match_current(TokenType.IDENT) and self.match_next(TokenType.COLON):
                # Label that can be used by GOTO, THEN, GOSUB, etc.
                self.symtab_addlabel(self.cur_token.text, self.cur_token.srcline)
                self.emitter.label(self.cur_token.text)
                self.next_token()
                self.next_token()
                if self.match_current(TokenType.NEWLINE):
                    self.next_token()
                else:
                    self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
            else:
                self.statements()
                if self.match_current(TokenType.NEWLINE):
                    self.next_token()
                else:
                    self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
        else:
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)

    def statements(self) -> None:
         """ <statements>  ::= <statement> [':' <statements>] """
         assert self.cur_token is not None
         self.statement()
         if (self.match_current(TokenType.COLON)):
              self.statements()

    def statement(self) -> None:
        """  <statement> = ID '=' <expression> | <keyword>"""
        assert self.cur_token is not None
        self.reset_curexpr()
        if self.match_current(TokenType.IDENT):
            symbol = self.cur_token
            self.next_token()
            if self.match_current(TokenType.EQ):
                self.next_token()
                self.expression()
                entry = self.symtab_addident(symbol.text, symbol.srcline, self.cur_expr)
                if entry is not None:
                    self.emitter.assign(entry.symbol, self.cur_expr)
            else:
                self.error(symbol.srcline, ErrorCode.SYNTAX)
        elif self.cur_token.is_keyword():
            self.keyword()
        else:
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)

    def keyword(self) -> None:
        """ <keyword> := COMMAND | FUNCTION """
        assert self.cur_token is not None
        fname = self.cur_token.text.replace('$', 'S').upper()
        keyword_rule = getattr(self, "command_" + fname, None)
        if keyword_rule is None:
            keyword_rule = getattr(self, "function_" + fname, None)
        if keyword_rule is None:
            self.error(self.cur_token.srcline, ErrorCode.NOKEYW, ": " + self.cur_token.text)
        else:
            keyword_rule()

    def command_CLS(self) -> None:
        """ <command_CLS> := CLS [<arg_channel>] """
        assert self.cur_token is not None
        self.next_token()
        args = [Expression.int('0')]
        if self.match_current(TokenType.CHANNEL):
            self.push_curexpr()
            self.arg_channel()
            args = [self.cur_expr]
            self.pop_curexpr()
        self.emitter.rtcall('CLS', args)

    def command_END(self) -> None:
        """ <command_END> := END """
        self.emitter.end()
        self.next_token()

    def command_IF(self) -> None:
        """ <command_IF> := IF <expression> (THEN|GOTO) (LABEL | NUMBER | <statements>) [ELSE (LABEL| NUMBER | <statements>)] NEWLINE"""
        assert self.cur_token is not None
        self.next_token()
        line = self.cur_token.srcline
        endif = self.symtab_newtmplabel(line)
        if endif is not None:
            self.expression()
            self.emitter.logical_expr(self.cur_expr, endif.symbol)
            if self.match_current(TokenType.GOTO):
                self.command_GOTO()
            elif self.match_current(TokenType.THEN):
                self.command_GOTO() 
            else:
                self.error(line, ErrorCode.SYNTAX)
            if self.match_current(TokenType.ELSE):
                endelse = self.symtab_newtmplabel(line)
                if endelse is not None:
                    self.emitter.goto(endelse.symbol)
                    self.emitter.label(endif.symbol)
                    endif = endelse
                    self.command_GOTO()
            self.emitter.label(endif.symbol)

    def function_INKEYS(self) -> None:
        """ <function_INKEYS> := INKEYS """
        # no need of pushing current expression as this function has not
        # parameters
        assert self.cur_token is not None
        sym = self.symtab_newtmpvar(self.cur_token.srcline, Expression.string(""))
        if sym is not None:
            self.emitter.rtcall('INKEYS', [], sym)
            tmpident = Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline)
            self.cur_expr.pushval(tmpident, BASTypes.STR)
            self.next_token()

    def command_GOTO(self) -> None:
        """ <command_GOTO> := GOTO (NUMBER | LABEL)"""
        assert self.cur_token is not None
        # if the label doesn't exit, the assembler will fail
        # this allow us to jump to a forward label/line
        line = self.cur_token.srcline
        self.next_token()
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

    def command_MODE(self) -> None:
        """ <command_MODE> := MODE <arg_int> """
        assert self.cur_token is not None
        self.next_token()
        self.arg_int()
        self.emitter.rtcall('MODE', [self.cur_expr])      

    def command_PRINT(self) -> None:
        """ <command_PRINT> := PRINT <arg_str> """
        assert self.cur_token is not None
        self.next_token()
        self.arg_str()
        self.emitter.rtcall('PRINT', [self.cur_expr])      

    def command_THEN(self) -> None:
        assert self.cur_token is not None
        self.error(self.cur_token.srcline, ErrorCode.THEN)

    # Argument rules

    def arg_channel(self) -> None:
        """<arg_channel> = #<expression>.t == INT"""
        assert self.cur_token is not None
        line = self.cur_token.srcline
        if self.match_current(TokenType.CHANNEL):
            self.next_token()
            self.expression()
            if not self.cur_expr.is_int_result():
                self.error(line, ErrorCode.TYPE)
        else:
            self.error(line, ErrorCode.SYNTAX)

    def arg_int(self) -> None:
        """<arg_int> = #<expression>.t == INT"""
        assert self.cur_token is not None
        line = self.cur_token.srcline
        self.expression()
        if self.cur_expr.is_empty():
            self.error(line, ErrorCode.SYNTAX)
        elif not self.cur_expr.is_int_result():
            self.error(line, ErrorCode.TYPE)

    def arg_real(self) -> None:
        """<arg_real> = #<expression>.t == REAL"""
        assert self.cur_token is not None
        line = self.cur_token.srcline
        self.expression()
        if self.cur_expr.is_empty():
            self.error(line, ErrorCode.SYNTAX)
        elif not self.cur_expr.is_real_result():
            self.error(line, ErrorCode.TYPE)

    def arg_str(self) -> None:
        """<arg_str> = #<expression>.t == STR"""
        assert self.cur_token is not None
        line = self.cur_token.srcline
        self.expression()
        if self.cur_expr.is_empty():
            print("AAA")
            self.error(line, ErrorCode.SYNTAX)
        elif not self.cur_expr.is_str_result():
            self.error(line, ErrorCode.TYPE)

    # Expression rules

    def expression(self) -> None:
        """ <expression> ::= <or_term> [XOR <expression>] """
        assert self.cur_token is not None
        self.or_term()
        if self.match_current(TokenType.XOR):
            op = self.cur_token
            self.next_token()
            self.expression()
            if not self.cur_expr.pushop(op):
                self.error(op.srcline, ErrorCode.TYPE)

    def or_term(self) -> None:
        """<or_term> ::= <and_term> [OR <or_term>]"""
        assert self.cur_token is not None
        self.and_term()
        if self.match_current(TokenType.AND):
            op = self.cur_token
            self.next_token()
            self.or_term()
            if not self.cur_expr.pushop(op):
                self.error(op.srcline, ErrorCode.TYPE)

    def and_term(self) -> None:
        """<and_term> ::= <not_term> [AND <and_term>]"""
        assert self.cur_token is not None
        self.not_term()
        if self.match_current(TokenType.AND):
            op = self.cur_token
            self.next_token()
            self.and_term()
            if not self.cur_expr.pushop(op):
                self.error(op.srcline, ErrorCode.TYPE)

    def not_term(self) -> None:
        """<not_term> ::= [NOT] <compare_term>"""
        assert self.cur_token is not None
        if self.match_current(TokenType.NOT):
            op = self.cur_token
            self.next_token()
            self.compare_term()
            if not self.cur_expr.pushop(op):
                self.error(op.srcline, ErrorCode.TYPE)
        else:
            self.compare_term()

    def compare_term(self) -> None:
        """<compare_term> ::= <add_term> [('=','<>'.'>','<','>=','<=')  <compare_term>]"""
        assert self.cur_token is not None
        self.add_term()
        if self.cur_token.is_logic_op():
            op = self.cur_token
            self.next_token()
            self.compare_term()
            if not self.cur_expr.pushop(op):
                self.error(op.srcline, ErrorCode.TYPE)

    def add_term(self) -> None:
        """<add_term> ::= <mod_term> [('+'|'-') <add_term>]"""
        assert self.cur_token is not None
        self.mod_term()
        if self.match_current(TokenType.PLUS) or self.match_current(TokenType.MINUS):
            op = self.cur_token
            self.next_token()
            self.add_term()
            if not self.cur_expr.pushop(op):
                self.error(op.srcline, ErrorCode.TYPE)

    def mod_term(self) -> None:
        """<mod_term> ::= <mult_term> [MOD <mod_term>]"""
        assert self.cur_token is not None
        self.mult_term()
        if self.match_current(TokenType.MOD):
            op = self.cur_token
            self.next_token()
            self.mod_term()
            if not self.cur_expr.pushop(op):
                self.error(op.srcline, ErrorCode.TYPE)

    def mult_term(self) -> None:
        """<mult_term> ::= <negate_term> [('*'|'/'|'\\' <mult_term>] """
        assert self.cur_token is not None
        self.negate_term()
        if self.match_current(TokenType.SLASH) or self.match_current(TokenType.LSLASH) or self.match_current(TokenType.ASTERISK):
            op = self.cur_token
            self.next_token()
            self.mult_term()
            if not self.cur_expr.pushop(op):
                self.error(op.srcline, ErrorCode.TYPE)

    def negate_term(self) -> None:
        """<negate_term> ::= ['-'] <sub_term> """
        assert self.cur_token is not None
        if self.match_current(TokenType.MINUS):
            op = self.cur_token
            self.next_token()
            self.sub_term()
            if not self.cur_expr.pushop(Token('NEG', TokenType.NEG, op.srcline)):
                self.error(op.srcline, ErrorCode.TYPE)
        else:
            self.sub_term()

    def sub_term(self) -> None:
        """ <sub_term> ::= '(' <expression> ')' | <factor> """
        assert self.cur_token is not None
        if self.match_current(TokenType.LPAR):
            partoken = self.cur_token
            self.next_token()
            self.expression()
            if self.match_current(TokenType.RPAR):
                self.next_token()
            else:
                self.error(partoken.srcline, ErrorCode.SYNTAX)
        else:
            self.factor()

    def factor(self) -> None:
        """<factor> ::= ID | INTEGER | REAL | STRING | <function>"""
        assert self.cur_token is not None
        if self.match_current(TokenType.IDENT):
            sym = self.symtab_search(self.cur_token.text)
            if sym is not None:
                # store the token in the expression with the name keep in the
                # symbols table
                token = Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline)
                self.cur_expr.pushval(token, sym.valtype)
                sym.inc_reads()
                self.next_token()
            else:
                self.error(self.cur_token.srcline, ErrorCode.NOIDENT)
        elif self.match_current(TokenType.INTEGER):
            self.cur_expr.pushval(self.cur_token, BASTypes.INT)
            self.next_token()
        elif self.match_current(TokenType.REAL):
            self.cur_expr.pushval(self.cur_token, BASTypes.REAL)
            self.next_token()
        elif self.match_current(TokenType.STRING):
            # create a constant variable to assign the string literal and 
            # add that variable to the expression
            strexpr = Expression()
            strexpr.pushval(self.cur_token, BASTypes.STR)
            sym = self.symtab_newtmpvar(self.cur_token.srcline, strexpr)
            if sym is not None:
                self.cur_expr.pushval(Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline), BASTypes.STR)
                self.next_token()
        else:
            fname = self.cur_token.text.replace('$', 'S').upper()
            function_rule = getattr(self, "function_" + fname, None)
            if function_rule is None:
                self.error(self.cur_token.srcline, f"function {self.cur_token.text} is not supported yet")
            else:
                function_rule()
