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
from bastypes import CodeBlock, CodeBlockType, ForBlockInfo

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
        # start, limit, step, looplabel, endlabel
        self.block_stack: List[CodeBlock] = []
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
        symname = 'var_' + symname.lower()
        if symname.endswith('$'):
            symname = symname.replace('$', '_str')
            forcedtype = BASTypes.STR
        elif symname.endswith('!'):
            symname = symname.replace('!', '_real')
            forcedtype = BASTypes.REAL
        elif symname.endswith('%'): 
            symname = symname.replace('%', '_int')
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
            # is_compatible will ensure it matches with expression type
            entry.valtype = forcedtype
        if entry.is_compatible(expr.restype):
            entry.set_value(expr)
            return entry
        else:
            self.error(srcline, ErrorCode.TYPE)
            return None

    def symtab_search(self, symname: str) -> Optional[Symbol]:
        symname, _ = self.symtab_name2type(symname)
        return self.symbols.search(symname)

    def symtab_newtmpvar(self, expr: Expression) -> Optional[Symbol]:
        sname = f"tmp{self.temp_vars:03d}"
        sname, _ = self.symtab_name2type(sname)
        entry = self.symbols.add(sname, SymTypes.SYMVAR)
        if entry is not None:
            entry.set_value(expr)
            entry.temporal = True
            self.temp_vars = self.temp_vars + 1
        return entry

    def symtab_newtmplabel(self, srcline: int) -> Optional[Symbol]:
        sname = f"label_{self.temp_vars:03d}"
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
            self.expr_stack.pop()
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
        if len(self.block_stack) > 0:
            cblock = self.block_stack.pop()
            if cblock.type == CodeBlockType.FOR:
                self.abort(ErrorCode.NONEXT)
            elif cblock.type == CodeBlockType.WHILE:
                self.abort(ErrorCode.NOWEND)
            else:
                self.abort(ErrorCode.EOFMET)
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
        """ <line> := INTEGER NEWLINE | INTEGER <statements> NEWLINE"""
        assert self.cur_token is not None
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

    def statements(self) -> None:
         """ <statements>  ::= <statement> [':' <statements>] """
         assert self.cur_token is not None
         self.statement()
         if (self.match_current(TokenType.COLON)):
              self.next_token()
              self.statements()

    def statement(self) -> None:
        """  <statement> = IDENT '=' <expression> | <keyword>"""
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

    #
    # BASIC Build-in Commands and Functions rules
    #

    def function_ASC(self) -> None:
        """ <function_ASC> := ASC(<arg_int>) """
        assert self.cur_token is not None
        self.next_token()
        if not self.match_current(TokenType.LPAR):
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
            return
        self.next_token()
        sym = self.symtab_newtmpvar(Expression.int('0'))
        if sym is not None:
            args: List[Expression] = []
            self.push_curexpr()
            self.arg_str()
            args.append(self.cur_expr)
            self.pop_curexpr()
            self.emitter.rtcall('ASC', args, sym)
            sym.inc_writes()
            tmpident = Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline)
            self.cur_expr.pushval(tmpident, BASTypes.INT)
            if not self.match_current(TokenType.RPAR):
                self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
                return
            self.next_token()

    def function_AT(self) -> None:
        """ <function_AT> := @<ident_factor> """
        assert self.cur_token is not None
        atop = self.cur_token
        self.next_token()
        if self.match_current(TokenType.IDENT):
            self.ident_factor()
            self.cur_expr.pushop(atop)
        else:
            self.error(atop.srcline, ErrorCode.SYNTAX)

    def command_BORDER(self) -> None:
        """ <command_BORDER> := BORDER <arg_int>[,<arg_int>] """
        assert self.cur_token is not None
        self.next_token()
        self.reset_curexpr()
        args: List[Expression] = []
        self.arg_int()
        args.append(self.cur_expr)
        if self.match_current(TokenType.COMMA):
            self.next_token()
            self.reset_curexpr()
            self.arg_int()
            args.append(self.cur_expr)
        else:
            # If there is no second color, the first one must
            # appear twice to avoid the blinking 
            args.append(self.cur_expr)
        self.emitter.rtcall('BORDER', args)

    def function_CHRS(self) -> None:
        """ <function_CHRS> := CHR$(<arg_int>) """
        assert self.cur_token is not None
        self.next_token()
        if not self.match_current(TokenType.LPAR):
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
            return
        self.next_token()
        sym = self.symtab_newtmpvar(Expression.string(""))
        if sym is not None:
            args: List[Expression] = []
            self.push_curexpr()
            self.arg_int()
            args.append(self.cur_expr)
            self.pop_curexpr()
            self.emitter.rtcall('CHRS', args, sym)
            sym.inc_writes()
            tmpident = Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline)
            self.cur_expr.pushval(tmpident, BASTypes.STR)
            if not self.match_current(TokenType.RPAR):
                self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
                return
            self.next_token()

    def command_CLS(self) -> None:
        """ <command_CLS> := CLS <arg_channel> """
        assert self.cur_token is not None
        self.next_token()
        self.arg_channel()
        self.emitter.rtcall('CLS')

    def command_END(self) -> None:
        """ <command_END> := END """
        self.emitter.end()
        self.next_token()

    def command_FOR(self) -> None:
        """ <command_FOR> := FOR IDENT=<arg_int> TO <arg_int> [STEP [-]NUMBER] """
        assert self.cur_token is not None
        self.next_token()
        if self.match_current(TokenType.IDENT):
            symbol = self.cur_token
            self.next_token()
            if self.match_current(TokenType.EQ):
                self.next_token()
                self.arg_int()
                variant = self.symtab_addident(symbol.text, symbol.srcline, self.cur_expr)
                assert variant is not None
                self.emitter.assign(variant.symbol, self.cur_expr)
                self.reset_curexpr()
                if self.cur_token.text.upper() == 'TO':
                    self.next_token()
                    self.arg_int()
                    limit = self.symtab_newtmpvar(self.cur_expr)
                    assert limit is not None
                    self.emitter.assign(limit.symbol, self.cur_expr)
                    self.reset_curexpr()
                    step = None
                    if self.cur_token.text.upper() == 'STEP':
                        self.next_token()
                        step = Expression()
                        reverse = False
                        if self.match_current(TokenType.MINUS):
                            self.next_token()
                            reverse = True
                        if self.match_current(TokenType.INTEGER):
                            step.pushval(self.cur_token, BASTypes.INT)
                            if reverse:
                               step.pushop(Token('NEG', TokenType.NEG, symbol.srcline))
                            self.next_token()
                            if not step.check_types():
                                self.error(symbol.srcline, ErrorCode.TYPE)
                                return
                        else:
                            self.error(symbol.srcline, ErrorCode.SYNTAX)
                            return
                    startlabel = self.symtab_newtmplabel(self.cur_token.srcline)
                    endlabel = self.symtab_newtmplabel(self.cur_token.srcline)
                    assert startlabel is not None and endlabel is not None
                    codeblock = CodeBlock(CodeBlockType.FOR, startlabel, endlabel)
                    codeblock.set_forinfo((variant, limit, step))
                    self.block_stack.append(codeblock)
                    self.emitter.forloop(variant, limit, step, startlabel, endlabel)
                    return
            self.error(symbol.srcline, ErrorCode.SYNTAX)
        else:
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)

    def command_FRAME(self) -> None:
        """ <command_FRAME> := FRAME """
        self.emitter.rtcall('FRAME')
        self.next_token()

    def command_GOTO(self) -> None:
        """ <command_GOTO> := GOTO (NUMBER | IDENT)"""
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

    def function_HEXS(self) -> None:
        """ <function_HEXS> := HEX$(<arg_int> [,<arg_int>])"""
        assert self.cur_token is not None
        self.next_token()
        if not self.match_current(TokenType.LPAR):
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
            return
        self.next_token()
        sym = self.symtab_newtmpvar(Expression.string(""))
        if sym is not None:
            args: List[Expression] = []
            self.push_curexpr()
            self.arg_int()
            args.append(self.cur_expr)
            self.pop_curexpr()
            digits = Expression.int('4')
            if self.match_current(TokenType.COMMA):
                self.next_token()
                self.push_curexpr()
                self.arg_int()
                digits = self.cur_expr
                self.pop_curexpr()
            args.append(digits)
            self.emitter.rtcall('HEXS', args, sym)
            sym.inc_writes()
            tmpident = Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline)
            self.cur_expr.pushval(tmpident, BASTypes.STR)
            if not self.match_current(TokenType.RPAR):
                self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
                return
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
        """ <function_INKEYS> := INKEY$ """
        # no need of pushing current expression as this function has not
        # parameters
        assert self.cur_token is not None
        sym = self.symtab_newtmpvar(Expression.string(""))
        if sym is not None:
            self.emitter.rtcall('INKEYS', [], sym)
            sym.inc_writes()
            tmpident = Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline)
            self.cur_expr.pushval(tmpident, BASTypes.STR)
            self.next_token()


    def command_INPUT(self) -> None:
        """ <command_INPUT> := INPUT <arg_channel>[STRING(;|,)] IDENT [,IDENT] """
        assert self.cur_token is not None
        line = self.cur_token.srcline
        self.next_token()
        self.arg_channel()
        if self.match_current(TokenType.STRING):
            self.str_factor()
            self.emitter.rtcall('PRINT',[self.cur_expr])
            self.reset_curexpr()
            if self.match_current(TokenType.SEMICOLON):
                self.emitter.rtcall('PRINT_QM', []) # print the question mark
            elif not self.match_current(TokenType.COMMA):
                self.error(line, ErrorCode.SYNTAX)
                return
            self.next_token()
        else:
            self.emitter.rtcall('PRINT_QM', []) # print the question mark

        args: List[Expression] = []
        while self.match_current(TokenType.IDENT):
            self.ident_factor()
            # we want addresses in memory to store inputs,
            # so @ is implicit in the syntax
            self.cur_expr.pushop(Token('AT', TokenType.AT, line))
            args.append(self.cur_expr)
            if self.match_current(TokenType.COMMA):
                self.next_token()
            self.reset_curexpr()
        nparams = len(args)
        if nparams > 127:
            self.error(line, ErrorCode.OVERFLOW)
        elif nparams == 0:
            self.error(line, ErrorCode.SYNTAX)
        else:
            self.emitter.rtcall('INPUT', [])
            for var in args:
                if var.is_int_result():
                    self.emitter.rtcall('INPUT_INT', [var])
                elif var.is_real_result():
                    self.emitter.rtcall('INPUT_REAL', [var])
                else:
                    self.emitter.rtcall('INPUT_STR', [var])
    

    def command_MODE(self) -> None:
        """ <command_MODE> := MODE <arg_int> """
        assert self.cur_token is not None
        self.next_token()
        self.arg_int()
        self.emitter.rtcall('MODE', [self.cur_expr])      

    def command_NEXT(self) -> None:
        """ <command_NEXT> := NEXT [IDENT] """
        assert self.cur_token is not None
        self.next_token()
        if len(self.block_stack) == 0:
            assert self.cur_token is not None
            self.error(self.cur_token.srcline, ErrorCode.NEXT)
        else:
            cblock = self.block_stack.pop()
            if cblock.type != CodeBlockType.FOR:
                self.block_stack.append(cblock)
                self.error(self.cur_token.srcline, ErrorCode.NEXT)
                return
            assert cblock.blockinfo and cblock.startlabel and cblock.endlabel is not None
            start, limit, step = cblock.blockinfo
            self.emitter.next(start, limit, step, cblock.startlabel, cblock.endlabel)
            if self.match_current(TokenType.IDENT):
                assert self.cur_token is not None
                entry = self.symtab_search(self.cur_token.text)
                if not entry or entry.symbol != start.symbol:
                    self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
                    self.block_stack.append(cblock)
                else:
                    self.next_token()

    def command_LABEL(self) -> None:
        """
        <command_LABEL> := LABEL IDENT 
        This is an addition we can find in Locomotive BASIC v2 to define jump etiquettes
        """
        assert self.cur_token is not None
        self.next_token()
        if self.match_current(TokenType.IDENT):
            # Label that can be used by GOTO, THEN, GOSUB, etc.
            self.symtab_addlabel(self.cur_token.text, self.cur_token.srcline)
            self.emitter.label(self.cur_token.text)
            self.next_token()
        else:
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)

    def command_LOCATE(self) -> None:
        """ <command_LOCATE> := LOCATE <arg_int>, <arg<int> """
        assert self.cur_token is not None
        self.next_token()
        args: List[Expression] = []
        self.reset_curexpr()
        self.arg_int()
        args.append(self.cur_expr)
        if self.match_current(TokenType.COMMA):
            self.next_token()
            self.reset_curexpr()
            self.arg_int()
            args.append(self.cur_expr)
            self.reset_curexpr()
            self.emitter.rtcall('LOCATE', args)
        else:
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
        
    def function_PEEK(self) -> None:
        """ <function_PEEK> := PEEK(<arg_int>) """
        assert self.cur_token is not None
        self.next_token()
        if not self.match_current(TokenType.LPAR):
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
            return
        self.next_token()
        sym = self.symtab_newtmpvar(Expression.int('0'))
        if sym is not None:
            args: List[Expression] = []
            self.push_curexpr()
            self.arg_int()
            args.append(self.cur_expr)
            self.pop_curexpr()
            self.emitter.rtcall('PEEK', args, sym)
            sym.inc_writes()
            tmpident = Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline)
            self.cur_expr.pushval(tmpident, BASTypes.INT)
            if not self.match_current(TokenType.RPAR):
                self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
                return
            self.next_token()

    def command_PRINT(self) -> None:
        """ <command_PRINT> := PRINT <arg_channel> <arg_print_list>"""
        assert self.cur_token is not None
        line = self.cur_token.srcline
        self.next_token()
        self.arg_channel()
        cblock = CodeBlock(CodeBlockType.PRINT, None, None)
        self.block_stack.append(cblock)
        self.arg_print_list()
        self.block_stack.pop()

    def command_SPC(self) -> None:
        """ <command_SPC> := SPC(<arg_int>)"""
        assert self.cur_token is not None
        if len(self.block_stack) == 0 or self.block_stack[-1].type != CodeBlockType.PRINT:
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
            return
        self.next_token()
        if not self.match_current(TokenType.LPAR):
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
            return
        self.next_token()
        args: List[Expression] = []
        self.push_curexpr()
        self.arg_int()
        args.append(self.cur_expr)
        self.pop_curexpr()
        self.emitter.rtcall('PRINT_SPC', args)
        if not self.match_current(TokenType.RPAR):
            self.error(self.cur_token.srcline, ErrorCode.SYNTAX)
            return
        self.next_token()

    def command_TAB(self) -> None:
        """ 
        <function_TAB> := TAB(<arg_int>)
        Right now, TAB(x) and SPC(x) do the same thing
        """
        self.command_SPC()

    def command_THEN(self) -> None:
        """ THEN out of sequence """
        assert self.cur_token is not None
        self.error(self.cur_token.srcline, ErrorCode.THEN)

    def command_WHILE(self) -> None:
        """ <command_WHILE> := <arg_int> NEWLINE <lines> WEND """
        assert self.cur_token is not None
        line = self.cur_token.srcline
        self.next_token()
        self.arg_int()
        if self.match_current(TokenType.NEWLINE):
            endwhile = self.symtab_newtmplabel(line)
            startwhile = self.symtab_newtmplabel(line)
            if endwhile is not None and startwhile is not None:
                self.emitter.label(startwhile.symbol)
                self.emitter.logical_expr(self.cur_expr, endwhile.symbol)
                cblock = CodeBlock(CodeBlockType.WHILE, startwhile, endwhile)
                self.block_stack.append(cblock)
                return
        self.error(line, ErrorCode.SYNTAX)
        
    def command_WEND(self) -> None:
        """ <command_WEND> := WEND """
        assert self.cur_token is not None
        line = self.cur_token.srcline
        if len(self.block_stack) > 0:
            cblock = self.block_stack.pop()
            if cblock.type != CodeBlockType.WHILE:
                self.error(line, ErrorCode.WEND)
                self.block_stack.append(cblock)
                return
            assert cblock.startlabel and cblock.endlabel is not None
            self.emitter.goto(cblock.startlabel.symbol)
            self.emitter.label(cblock.endlabel.symbol)
            self.next_token()
        else:
            self.error(line, ErrorCode.WEND)

    #
    # Command and Function Argument rules
    #

    def arg_int(self) -> None:
        """<arg_int> = <expression>.t == INT"""
        assert self.cur_token is not None
        line = self.cur_token.srcline
        self.expression()
        if self.cur_expr.is_empty():
            self.error(line, ErrorCode.SYNTAX)
        elif not self.cur_expr.is_int_result():
            self.error(line, ErrorCode.TYPE)

    def arg_real(self) -> None:
        """<arg_real> = <expression>.t == REAL"""
        assert self.cur_token is not None
        line = self.cur_token.srcline
        self.expression()
        if self.cur_expr.is_empty():
            self.error(line, ErrorCode.SYNTAX)
        elif not self.cur_expr.is_real_result():
            self.error(line, ErrorCode.TYPE)

    def arg_str(self) -> None:
        """<arg_str> = <expression>.t == STR"""
        assert self.cur_token is not None
        line = self.cur_token.srcline
        self.expression()
        if self.cur_expr.is_empty():
            self.error(line, ErrorCode.SYNTAX)
        elif not self.cur_expr.is_str_result():
            self.error(line, ErrorCode.TYPE)

    def arg_channel(self) -> None:
        """<arg_channel> := #NUMBER.t == INT"""
        # If channel argument is not pressent, we have to
        # assume 0
        assert self.cur_token is not None
        line = self.cur_token.srcline
        channel = [Expression.int('0')]
        if self.match_current(TokenType.CHANNEL):
            self.push_curexpr()
            self.next_token()
            self.expression()
            if not self.cur_expr.is_int_result():
                self.error(line, ErrorCode.TYPE)
                return
            channel = [self.cur_expr]
            self.pop_curexpr()
        self.emitter.rtcall('CHANNEL_SET', channel)

    def arg_print_list(self) -> None:
        """ <arg_print_list> := <expresion>[(;|,)<expresion>*]"""
        assert self.cur_token is not None
        line = self.cur_token.srcline
        allowedcmd = [TokenType.SPC, TokenType.TAB]
        while self.cur_token.type in allowedcmd:
            cmd_rule = getattr(self, "command_" + self.cur_token.text, None)
            assert cmd_rule is not None
            cmd_rule()
        self.expression()
        while not self.cur_expr.is_empty():
            if self.cur_expr.is_str_result():
                self.emitter.rtcall('PRINT', [self.cur_expr])
            elif self.cur_expr.is_int_result():
                self.emitter.rtcall('PRINT_INT', [self.cur_expr])
            elif self.cur_expr.is_real_result():
                self.emitter.rtcall('PRINT_REAL', [self.cur_expr])
            else:
                self.error(line, ErrorCode.SYNTAX)
                return
            self.reset_curexpr()
            if self.match_current(TokenType.SEMICOLON):
                self.next_token()
                if self.match_current(TokenType.NEWLINE) or self.match_current(TokenType.COLON):
                    return
            elif self.match_current(TokenType.COMMA):
                self.emitter.rtcall('PRINT_SPC', [Expression.int('4')])
                self.next_token()
                if self.match_current(TokenType.NEWLINE) or self.match_current(TokenType.COLON):
                    return
            elif self.match_current(TokenType.NEWLINE):
                break
            while self.cur_token.type in allowedcmd:
                cmd_rule = getattr(self, "command_" + self.cur_token.text, None)
                assert cmd_rule is not None
                cmd_rule()
            self.expression()    
        self.emitter.rtcall('PRINT_LN')
    
    #
    # Expression rules
    #

    def expression(self) -> None:
        """ <expression> ::= <or_term> [XOR <expression>] """
        assert self.cur_token is not None
        line = self.cur_token.srcline
        self.or_term()
        if self.match_current(TokenType.XOR):
            op = self.cur_token
            self.next_token()
            self.expression()
            self.cur_expr.pushop(op)
        try:
            if not self.cur_expr.check_types():
                self.reset_curexpr()
                self.error(line, ErrorCode.TYPE)
        except Exception:
            # bad formed expression
            self.reset_curexpr()
            self.error(line, ErrorCode.SYNTAX)

    def or_term(self) -> None:
        """<or_term> ::= <and_term> [OR <or_term>]"""
        assert self.cur_token is not None
        self.and_term()
        if self.match_current(TokenType.OR):
            op = self.cur_token
            self.next_token()
            self.or_term()
            self.cur_expr.pushop(op)

    def and_term(self) -> None:
        """<and_term> ::= <not_term> [AND <and_term>]"""
        assert self.cur_token is not None
        self.not_term()
        if self.match_current(TokenType.AND):
            op = self.cur_token
            self.next_token()
            self.and_term()
            self.cur_expr.pushop(op)

    def not_term(self) -> None:
        """<not_term> ::= [NOT] <compare_term>"""
        assert self.cur_token is not None
        if self.match_current(TokenType.NOT):
            op = self.cur_token
            self.next_token()
            self.compare_term()
            self.cur_expr.pushop(op)
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
            self.cur_expr.pushop(op)

    def add_term(self) -> None:
        """<add_term> ::= <mod_term> [('+'|'-') <add_term>]"""
        assert self.cur_token is not None
        self.mod_term()
        if self.match_current(TokenType.PLUS) or self.match_current(TokenType.MINUS):
            op = self.cur_token
            self.next_token()
            self.add_term()
            self.cur_expr.pushop(op)

    def mod_term(self) -> None:
        """<mod_term> ::= <mult_term> [MOD <mod_term>]"""
        assert self.cur_token is not None
        self.mult_term()
        if self.match_current(TokenType.MOD):
            op = self.cur_token
            self.next_token()
            self.mod_term()
            self.cur_expr.pushop(op)

    def mult_term(self) -> None:
        """<mult_term> ::= <negate_term> [('*'|'/'|'\\' <mult_term>] """
        assert self.cur_token is not None
        self.negate_term()
        if self.match_current(TokenType.SLASH) or self.match_current(TokenType.LSLASH) or self.match_current(TokenType.ASTERISK):
            op = self.cur_token
            self.next_token()
            self.mult_term()
            self.cur_expr.pushop(op)

    def negate_term(self) -> None:
        """<negate_term> ::= ['-'] <sub_term> """
        assert self.cur_token is not None
        if self.match_current(TokenType.MINUS):
            op = self.cur_token
            self.next_token()
            self.sub_term()
            self.cur_expr.pushop(Token('NEG', TokenType.NEG, op.srcline))
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
                self.reset_curexpr()
                self.error(partoken.srcline, ErrorCode.SYNTAX)
        else:
            self.factor()

    def factor(self) -> None:
        """<factor> ::= <ident_factor> | <int_factor> | <real_factor> | <str_factor> | <fun_call>"""
        assert self.cur_token is not None
        if self.match_current(TokenType.IDENT):
            self.ident_factor()
        elif self.match_current(TokenType.INTEGER):
            self.int_factor()
        elif self.match_current(TokenType.REAL):
            self.real_factor()
        elif self.match_current(TokenType.STRING):
            self.str_factor()
        else:
            self.fun_call()

    def ident_factor(self):
        """ <ident_factor> := IDENT """
        assert self.cur_token is not None
        sym = self.symtab_search(self.cur_token.text)
        if sym is not None:
            # store the token in the expression with the name keep in the
            # symbols table
            token = Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline)
            self.cur_expr.pushval(token, sym.valtype)
            sym.inc_reads()
            self.next_token()
        else:
            self.reset_curexpr()
            self.error(self.cur_token.srcline, ErrorCode.NOIDENT)

    def int_factor(self):
        """ <int_factor> := NUMBER """
        assert self.cur_token is not None
        self.cur_expr.pushval(self.cur_token, BASTypes.INT)
        self.next_token()

    def real_factor(self):
        """ <real_factor> := REAL """
        realexpr = Expression()
        realexpr.pushval(self.cur_token, BASTypes.REAL)
        sym = self.symtab_newtmpvar(realexpr)
        if sym is not None:
            self.cur_expr.pushval(Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline), BASTypes.REAL)
            self.next_token()

    def str_factor(self):
        """ <str_factor> := STRING """
        assert self.cur_token is not None
        strexpr = Expression()
        strexpr.pushval(self.cur_token, BASTypes.STR)
        sym = self.symtab_newtmpvar(strexpr)
        if sym is not None:
            self.cur_expr.pushval(Token(sym.symbol, TokenType.IDENT, self.cur_token.srcline), BASTypes.STR)
            self.next_token()

    def fun_call(self):
        """ <fun_call> := <function_NAME> """
        assert self.cur_token is not None
        fname = self.cur_token.text.replace('$', 'S').upper()
        function_rule = getattr(self, "function_" + fname, None)
        if function_rule is None:
            self.reset_curexpr()
            self.error(self.cur_token.srcline, f"function {self.cur_token.text} is not supported yet")
        else:
            function_rule()