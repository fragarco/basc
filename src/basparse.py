"""
Syntactic analyzer of Amstrad locomotive BASIC code. It supports some
enhancements like having a body for THEN clausules.

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

Use example:

program = "
10 FOR I = 1 TO 5
20   PRINT I
30 NEXT I
40 WHILE I < 10
50   I = I + 1
60 WEND
70 IF I > 5 THEN
80   PRINT "OK"
90 ELSE
100  PRINT "FAIL"
110 END IF
"

parser = LocBasParser(program)
ast = parser.parse_program()

for line in ast.lines:
    print(f"LINE {line.number}:")
    for stmt in line.statements:
        print(f"  {stmt}")

"""

from __future__ import annotations
from typing import Callable, Optional, cast, NoReturn
from dataclasses import dataclass
from enum import Enum, auto
from math import log
from functools import wraps
from baserror import BasError
from baserror import WarningLevel as WL
from baspp import CodeLine
from baslex import LocBasLexer, TokenType, Token
from symbols import SymTable, SymEntry, SymType
import astlib as AST

class BlockType(Enum):
    IF = auto()
    FOR = auto()
    WHILE = auto()
    SUB = auto()
    FUNCTION = auto()
    SELECT = auto()
 
@dataclass
class CodeBlock:
    type: BlockType
    until_keywords: tuple
    start_node: AST.Statement
    tk: Token
    options: int = 0

class LocBasParser:
    def __init__(self, code: list[CodeLine], tokens: list[Token], warning_level: WL=WL.ALL):
        self.tokens = tokens
        self.lines = code
        self.pos = 0
        self.codeblocks: list[CodeBlock] = []
        self.warning_level: WL = warning_level
        self.symtable = SymTable()
        self.context = ""
        self.current_usrlabel = ""
        self.current_linelabel = ""
        self.unsignedmode = False
        self.hasevents = False

    @staticmethod
    def astnode(func: Callable[[LocBasParser], AST.ASTNode]):
        """ Decorator to store token line and col in the required AST nodes """
        @wraps(func)
        def inner(inst, *args, **kwargs):
            tk = inst._current()
            node = func(inst, *args, **kwargs)
            node.set_origin(tk.line,tk.col)
            return node
        return inner

    # ----------------- Error management -----------------

    def _raise_error(self, codenum: int, tk: Token, info: str = "") -> NoReturn:
        # Token lines start at 1
        if tk.line >= len(self.lines):
            # For example, EOF found while parsing the last line
            codeline = self.lines[-1]
        else:
            codeline = self.lines[tk.line - 1]
        raise BasError(
            codenum,
            codeline.source,
            codeline.code,
            codeline.line,
            tk.col,
            info
        ) 

    def _raise_warning(self, level: WL, msg: str, node: Optional[AST.ASTNode] = None) -> None:
        if level <= self.warning_level:
            current: AST.ASTNode | Token = node if node is not None else self._current()
            # tokens start line counting in 1
            codeline = self.lines[current.line - 1]
            print(f"[WARNING{int(level):02d}] {codeline.source}:{codeline.line}:{current.col}: {msg} in {codeline.code}")

    # ----------------- Token management -----------------

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _match(self, type: TokenType, lex: Optional[str] = None) -> Optional[Token]:
        if self._current_is(type, lex):
            return self._advance()
        return None

    def _expect(self, type: TokenType, lex: Optional[str] = None) -> Token:
        if not self._current_is(type, lex):
            info = ""
            current = self._current()
            if current.type == TokenType.KEYWORD:
                info = "unexpected keyword found"
            elif current.type == TokenType.IDENT:
                info = "unexpected identifier found"
            elif current.type == TokenType.COLON:
                info = "unexpected end of statement found"
            elif current.type == TokenType.EOL:
                info = "unexpected end of line found"
            elif current.type == TokenType.EOF:
                info = "unexpected end of file found"
            self._raise_error(2, self._current(), info)
        return self._advance()

    def _current_is(self, type: TokenType, lexeme: Optional[str] = None) -> bool:
        tk = self.tokens[self.pos]
        if tk.type != type: return False
        if lexeme != None:
            return lexeme == tk.lexeme
        return True

    def _current_in(self, types: tuple, lexemes: Optional[tuple] = None) -> bool:
        tk = self.tokens[self.pos]
        if tk.type not in types: return False
        if lexemes is not None:
            return tk.lexeme in lexemes
        return True

    def _next_is(self, type: TokenType, lexeme: Optional[str] = None) -> bool:
        nexttk = self.tokens[self.pos + 1]
        if nexttk.type != type: return False
        if lexeme != None and lexeme != nexttk.lexeme: return False
        return True

    def _next_in(self, types: tuple, lexemes: Optional[tuple] = None) -> bool:
        tk = self.tokens[self.pos + 1]
        if tk.type not in types: return False
        if lexemes is not None:
            return tk.lexeme in lexemes
        return True

    def _end_of_statement(self) -> bool:
        if self._current_in((TokenType.EOL, TokenType.EOF, TokenType.COLON, TokenType.COMMENT)):
            return True
        elif self._current_is(TokenType.KEYWORD, lexeme="ELSE"):
            return True
        return False

    # ----------------- Statements -----------------

    @astnode
    def _parse_ABS(self) -> AST.Function:
        """ <ABS> := ABS(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_num_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="ABS", etype=args[0].etype, args=args)

    @astnode
    def _parse_AFTER(self) -> AST.Command:
        """ <AFTER> ::= AFTER <int_expression>[,<int_expression>] <GOSUB> """
        self._advance()
        delay = self._parse_int_expression()
        args = [delay]
        if self._current_is(TokenType.COMMA):
            self._advance()
            timer = self._parse_int_expression()
            args.append(timer)
        args.append(self._parse_GOSUB())
        self.hasevents = True
        return AST.Command(name="AFTER", args=args)
    
    @astnode
    def _parse_ASC(self) -> AST.Function:
        """ <ASC> ::= ASC(<str_expression>)"""
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_str_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="ASC", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_ASM(self) -> AST.Command:
        """ <ASM> ::= ASM STR[,STR]* """
        self._advance()
        args: list[AST.Statement] = [self._parse_str_expression()]
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_str_expression())
        return AST.Command(name="ASM", args=args)

    @astnode
    def _parse_ATN(self) -> AST.Function:
        """ <ATN> ::= ATN(<num_expression>)"""
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_real_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="ATN", etype=AST.ExpType.Real, args=args)

    @astnode
    def _parse_AUTO(self) -> AST.Command:
        """ <AUTO> ::= AUTO <int_expression>[,<int_expression>] """   
        self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.INT):
            num = self._advance()
            args.append(AST.Integer(value=cast(int, num.value)))
            self._match(TokenType.COMMA)
            if self._current_is(TokenType.INT):
                num = self._advance()
                args.append(AST.Integer(value=cast(int, num.value)))
        return AST.Command(name="AUTO", args=args)
    
    @astnode
    def _parse_BINSS(self) -> AST.Function:
        """ <BINSS> ::= BIN$(<int_expression>[,<int_expression>])"""
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_int_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            width = self._parse_int_expression()
            args.append(width)
        self._expect(TokenType.RPAREN)
        return AST.Function(name="BIN$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_BORDER(self) -> AST.Command:
        """ <BORDER> ::= BORDER <int_expression>[,<int_expression>] """
        self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            color2 = self._parse_int_expression()
            args.append(color2)
        return AST.Command(name="BORDER", args=args)

    @astnode
    def _parse_CALL(self) -> AST.Statement:
        """
        <CALL> ::= CALL <user_fun> | <mem_call> | <asm_call>
        <user_fun> ::= IDENT[(<expression>,<expression>*)]
        <mem_call> ::= <int_expression>[,<expression>*)]
        <asm_call> ::= <str_expression>[,<expression>*)]
        """
        self._advance()
        if self._current_is(TokenType.IDENT) and self._next_is(TokenType.LPAREN):
            # Let's check if we are calling a procedure declared with SUB
            fname = "SUB" + self._current().lexeme
            entry = self.symtable.find(ident=fname, stype=SymType.Procedure, context="")
            if entry is not None:
                return self._parse_user_fun()
        tk = self._current()
        if tk.type == TokenType.INT:
            dir = self._parse_uint_expression()
        else:
            dir = self._parse_expression()
        if dir.etype not in (AST.ExpType.Integer, AST.ExpType.String):
            self._raise_error(13, tk)
        args = [dir]
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_expression())
        return AST.Command(name="CALL", args=args)
 
    @astnode
    def _parse_CASE(self) -> AST.Command:
        """ <CASE> ::= CASE <int_expression> """
        # A direct command that is not allowed in compiled programs
        # but let's the emiter fail 
        tk = self._advance()
        if len(self.codeblocks) == 0 or "END SELECT" not in self.codeblocks[-1].until_keywords:
            self._raise_error(2, tk, "unexpected CASE")
        args: list[AST.Statement] = [self._parse_int_expression()]
        node = self.codeblocks[-1].start_node
        if isinstance(node, AST.SelectCase):
            node.options = node.options + 1
        return AST.Command(name="CASE", args=args)

    @astnode
    def _parse_CASE_DEFAULT(self) -> AST.Command:
        """ <CASE DEFAULT> ::= CASE DEFAULT """
        tk = self._advance()
        if len(self.codeblocks) == 0 or "END SELECT" not in self.codeblocks[-1].until_keywords:
            self._raise_error(2, tk, "unexpected CASE DEFAULT")
        node = self.codeblocks[-1].start_node
        if isinstance(node, AST.SelectCase):
            if node.defaultcase:
                self._raise_error(2, tk, "only one CASE DEFAULT statement is allowed")
            node.defaultcase = True
        return AST.Command(name="CASE DEFAULT")

    @astnode
    def _parse_CAT(self) -> AST.Command:
        """ <CAT> ::= CAT """
        # A direct command that is not allowed in compiled programs
        # but let's the emiter fail 
        self._advance()
        return AST.Command(name="CAT")

    @astnode
    def _parse_CHAIN(self) -> AST.Command:
        """ <CHAIN> ::= CHAIN <str_expression>[,<int_expression>] """
        self._advance()
        args: list[AST.Statement] = [self._parse_str_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        return AST.Command(name="CHAIN", args=args)

    @astnode
    def _parse_CHAIN_MERGE(self) -> AST.Command:
        """ <CHAIN_MERGE> ::= CHAIN MERGE <str_expression>[,<int_expression>][,DELETE <range>] """
        self._advance()
        args: list[AST.Statement] = [self._parse_str_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
            if self._current_is(TokenType.COMMA):
                self._advance()
                self._expect(TokenType.KEYWORD, "DELETE")
                args.append(self._parse_range())
        return AST.Command(name="CHAIN_MERGE", args=args)

    @astnode
    def _parse_CHRSS(self) -> AST.Function:
        """ <CHRSS> ::= CHR$(<int_expression>)"""
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="CHR$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_CINT(self) -> AST.Function:
        """ <CINT> ::= CINT(<num_expression>)"""
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_num_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="CINT", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_CLEAR(self) -> AST.Command:
        """ <CLEAR> ::= CLEAR """
        # This command resets several areas of the BASIC interpreter
        # and doesn't seem to be very useful for a compiled program
        # but let's decide that to the code emiter as we can reuse CLEAR
        # to free some other generated structures
        self._advance()
        return AST.Command(name="CLEAR")

    def _parse_CLEAR_INPUT(self) -> AST.Command:
        """ <CLEAR_INPUT> ::= CLEAR INPUT"""
        # BASIC 1.1
        self._advance()
        return AST.Command(name="CLEAR INPUT")

    @astnode
    def _parse_CLG(self) -> AST.Command:
        """ <CLG> ::= CLG [<int_expression>] """
        self._advance()
        args: list[AST.Statement] = []
        if not self._end_of_statement():
            args = [self._parse_int_expression()]
        return AST.Command(name="CLG", args=args)

    @astnode
    def _parse_CLOSEIN(self) -> AST.Command:
        """ <CLOSEIN> ::= CLOSEIN """
        self._advance()
        return AST.Command(name="CLOSEIN")

    @astnode
    def _parse_CLOSEOUT(self) -> AST.Command:
        """ <CLOSEOUT> ::= CLOSEOUT """
        self._advance()
        return AST.Command(name="CLOSEOUT")

    @astnode
    def _parse_CLS(self) -> AST.Command:
        """ <CLS> := CLS [#<int_expression>] """
        self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.HASH):
            self._advance()
            args = [self._parse_int_expression()]
        return AST.Command(name="CLS", args=args)

    def _check_noconst(self, varname: str, tk: Token) -> None:
        entry = self.symtable.find(varname, SymType.Variable, self.context)
        if entry is not None:
            if entry.const is not None:
                self._raise_error(2, tk, "constant redefinition")

    @astnode
    def _parse_CONST(self) -> AST.Command:
        """ <CONST> := IDENT = INT """
        self._advance()
        tk = self._expect(TokenType.IDENT)
        entry = self.symtable.find(tk.lexeme, SymType.Variable, self.context)
        if entry is not None:
            self._raise_error(2, tk, "constant redefinition")
        self._expect(TokenType.COMP, lex="=")
        value = self._parse_int_expression(allowcast=False)
        self.symtable.add(
            ident=tk.lexeme,
            info=SymEntry(
                symtype=SymType.Variable,
                exptype=AST.ExpType.Integer,
                locals=SymTable(),
                datasz= AST.exptype_memsize(AST.ExpType.Integer),
                const=value
            ),
            context=self.context
        )
        args: list[AST.Statement] = []
        args.append(AST.Variable(tk.lexeme, AST.ExpType.Integer))
        args.append(value)
        return AST.Command(name="CONST", args=args)

    @astnode
    def _parse_CONT(self) -> AST.Command:
        """ <CONT> ::= CONT """
        # A direct command that is not allowed in compiled programs
        # but let's the emiter fail
        self._advance()
        return AST.Command(name="CONT")

    @astnode
    def _parse_COPYCHRSS(self) -> AST.Function:
        """ <COPYCHRSS> ::= COPYCHR$(#<int_expression>) """
        # BASIC 1.1
        self._advance()
        self._expect(TokenType.LPAREN)
        self._expect(TokenType.HASH)
        args = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="COPYCHR$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_COS(self) -> AST.Function:
        """ <COS> ::= COS(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_real_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="COS", etype=AST.ExpType.Real, args=args)
   
    @astnode 
    def _parse_CREAL(self) -> AST.Function:
        """ <CREAL> ::= CREAL(<num_expression>)"""
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_num_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="CREAL", etype=AST.ExpType.Real, args=args)

    @astnode
    def _parse_CURSOR(self) -> AST.Command:
        """ <CURSOR> ::= CURSOR <int_expression>[,<int_expression>] """
        # BASIC 1.1
        self._advance()
        args = [self._parse_int_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        return AST.Command(name="CURSOR", args=args)

    @astnode
    def _parse_DATA(self) -> AST.Data:
        """ <DATA> ::= DATA <constant>[,<constant>]*"""
        tk = self._advance()
        if self.context != "":
            self._raise_error(2, tk, "DATA cannot appear inside subroutines")
        args: list[AST.Statement] = [self._parse_data_constant()]
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_data_constant())
        node = AST.Data(args=args, linelabel=self.current_linelabel, userlabel = self.current_usrlabel)
        self.current_usrlabel = ""
        return node

    @astnode
    def _parse_data_constant(self) -> AST.Statement:
        """ <constant> ::= [-]INT | [-]REAL | "STRING" | IDENT """
        tok = self._current()
        sign: int = 1
        if tok.lexeme == '-':
            sign = -1
            self._advance()
            tok = self._current()
        if tok.type == TokenType.INT:
            tk = self._advance()
            value = cast(int, tok.value) * sign
            nbytes = self._int_to_bytes(tok.lexeme, value)
            if nbytes == 0:
                self._raise_error(6, tk)
            elif nbytes == 4:
                return AST.Real(value=value)
            return AST.Integer(value=value)
        elif tok.type == TokenType.REAL:
            self._advance()
            return AST.Real(value=cast(float, tok.value))
        elif tok.type == TokenType.STRING:
            self._advance()
            return AST.String(cast(str, tok.value))
        else:
            text = self._advance().text
            return AST.String(value=text)

    @astnode
    def _parse_DECSS(self) -> AST.Function:
        """ <DECSS> ::= DEC$(<num_expression>, STRING) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_num_expression()]
        self._expect(TokenType.COMMA)
        tk = self._expect(TokenType.STRING)
        args.append(AST.String(cast(str, tk.value)))
        self._expect(TokenType.RPAREN)
        return AST.Function(name="DEC$", args=args, etype=AST.ExpType.String)

    @astnode
    def _parse_DECLARE(self) -> AST.Command:
        # This allows the user to set a minor size for strings using the formula
        # DECLARE A$ FIXED 50
        # Added from Locomotive BASIC 2 PLUS
        self._advance()
        args: list[AST.Statement] = []
        while True:
            tk = self._expect(TokenType.IDENT)
            entry = self.symtable.find(tk.lexeme, SymType.Variable, context=self.context)
            if entry is not None:
                self._raise_error(2, tk, info="variable already declared")
            var = tk.lexeme
            vartype = AST.exptype_fromname(var)
            datasz = AST.exptype_memsize(vartype)
            fixedexp: Optional[AST.Statement] = None
            if vartype == AST.ExpType.String:
                if self._current_is(TokenType.KEYWORD, lexeme="FIXED"):
                    self._advance()
                    fixedexp = self._parse_int_expression(allowcast=False)
            added = self.symtable.add(
                ident=var,
                info=SymEntry(
                    symtype=SymType.Variable,
                    exptype=vartype,
                    locals=SymTable(),
                    datasz=datasz
                ),
                context=self.context
            )
            if not added:
                self._raise_error(2, tk)
            varnode = AST.Variable(var, vartype, fixedexp)
            varnode.set_origin(tk.line, tk.col)
            args.append(varnode)
            if self._current_is(TokenType.COMMA):
                self._advance()
            else:
                break
        return AST.Command(name="DECLARE", args=args)

    @astnode
    def _parse_DEF(self) -> AST.Command:
        # We decode DEF FN and not only DEF so if we find this
        # is an error
        self._raise_error(2, self._advance())
        return AST.Command(name="DEF")

    def _parse_arguments(self, info: SymEntry) -> tuple[list[AST.Variable|AST.Array], list[AST.ExpType]]:
        fargs: list[AST.Variable | AST.Array] = []
        argtypes: list[AST.ExpType] = []
        param: AST.Variable | AST.Array
        paramname: str = ""
        paramsym: SymType
        if self._match(TokenType.LPAREN):
            if self._next_is(TokenType.LBRACK):
                param = self._parse_array_declaration(onlybracket = True)
                paramtype = param.etype
                paramname = param.name
                paramsym = SymType.ArrayParam
                info.nargs = len(param.sizes)    # type: ignore [union-attr]
                info.indexes = list(param.sizes) # type: ignore [union-attr]
            else:
                tk = self._expect(TokenType.IDENT)
                paramname = tk.lexeme
                if "$." in paramname:
                    self._raise_error(2, tk, "unexpected record access")
                paramtype = AST.exptype_fromname(paramname)
                param = AST.Variable(name=paramname, etype=paramtype)
                paramsym = SymType.Param
            fargs.append(param)
            argtypes.append(paramtype)
            info.exptype = paramtype
            info.symtype = paramsym
            info.locals = SymTable()
            info.memoff = 0
            argoffset = 2
            self.symtable.add(ident=paramname, info=info, context=self.context)
            while self._current_is(TokenType.COMMA):
                self._advance()
                if self._next_is(TokenType.LBRACK):
                    param = self._parse_array_declaration(onlybracket = True)
                    paramtype = param.etype
                    paramname = param.name
                    paramsym = SymType.ArrayParam
                    info.nargs = len(param.sizes)    # type: ignore [union-attr]
                    info.indexes = list(param.sizes) # type: ignore [union-attr]
                else:
                    paramname = self._expect(TokenType.IDENT).lexeme
                    paramtype = AST.exptype_fromname(paramname)
                    param = AST.Variable(name=paramname, etype=paramtype)
                    paramsym = SymType.Param
                fargs.append(param)
                argtypes.append(paramtype)
                info.exptype = paramtype
                info.symtype = paramsym
                info.memoff = argoffset
                argoffset += 2
                self.symtable.add(ident=paramname, info=info, context=self.context)
            self._expect(TokenType.RPAREN)
        return fargs, argtypes

    @astnode
    def _parse_DEF_FN(self) -> AST.DefFN:
        """ <DEF_FN> ::== DEF FNIDENT[(IDENT[,IDENT]*)]=<num_expression>"""
        tk = self._advance()
        if self.context != "":
            # is not possible to define new functions or procs in the body of another
            self._raise_error(2, tk)
        tk = self._expect(TokenType.IDENT)
        fname = "FN" + tk.lexeme
        fargs: list[AST.Variable | AST.Array] = []
        argtypes: list[AST.ExpType] = []
        self.context = fname.upper()
        info = SymEntry(
            symtype=SymType.Function,
            exptype=AST.exptype_fromname(tk.lexeme),
            locals=SymTable(),
            )
        if not self.symtable.add(ident=fname, info=info, context=""):
            self._raise_error(2, tk)
        fargs, argtypes = self._parse_arguments(info)
        self._expect(TokenType.COMP, "=")
        fbody = self._parse_expression()
        self.context = ""
        # Lets update our entry for the function with
        # the last calculated parameters
        info = self.symtable.find(ident=fname, stype=SymType.Function) # type: ignore[assignment]
        if info is None:
            self._raise_error(38, tk)
        if info.exptype != fbody.etype:
            self._raise_error(13, tk)
        info.nargs = len(fargs)
        info.argtypes = list(argtypes)
        info.args = list(fargs)
        # time to set correctly the parameters offset now we know the total number
        for localname in info.locals.syms:
            entry = info.locals.syms[localname]
            entry.memoff = (info.nargs * 2) - entry.memoff - 2
        return AST.DefFN(name=fname, args=fargs, body=fbody)

    @astnode
    def _parse_DEFINT(self) -> AST.Command:
        """ <DEFINT> ::= DEFINT <str_range> """
        self._advance()
        args = [self._parse_range()]
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_range())
        return AST.Command(name="DEFINT", args=args)

    @astnode
    def _parse_DEFREAL(self) -> AST.Command:
        """ <DEFREAL> ::= DEFREAL <str_range> """
        self._advance()
        args = [self._parse_range()]
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_range())
        return AST.Command(name="DEFREAL", args=args)

    @astnode
    def _parse_DEFSTR(self) -> AST.Command:
        """ <DEFSTR> ::= DEFSTR <str_range> """
        self._advance()
        args = [self._parse_range()]
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_range())
        return AST.Command(name="DEFSTR", args=args)

    @astnode
    def _parse_DEG(self) -> AST.Command:
        """ <DEG> ::= DEG """
        self._advance()
        return AST.Command(name="DEG")

    def _parse_DELETE(self) -> AST.Command:
        """ <DELETE> ::= DELETE <int_range> """
        self._advance()
        args = [self._parse_range()]
        return AST.Command(name="DELETE", args=args)

    @astnode
    def _parse_DERR(self) -> AST.Function:
        """ <DERR> ::= DERR """
        self._advance()
        return AST.Function(name="DERR", etype=AST.ExpType.Integer)

    @astnode
    def _parse_DI(self) -> AST.Command:
        """ <DI> ::= DI """
        self._advance()
        return AST.Command(name="DI")

    @astnode
    def _parse_DIM(self) -> AST.Command:
        """ <DIM> ::= DIM <array_declaration>[,<array_declaration>]*"""
        # El numero dado como "size" es el maximo indice que se puede
        # usar, de esta forma es valido 10 DIM I(0): I(0) = 5
        tk = self._advance()
        args: list[AST.Statement] = [self._parse_array_declaration(onlybracket = False)]
        while self._current_is(TokenType.COMMA):
            self._advance()
            var = self._parse_array_declaration(onlybracket = False)
            args.append(var)
        for var in args:
            info = SymEntry(
                symtype=SymType.Array,
                exptype=var.etype,
                locals=SymTable(),
                nargs=len(var.sizes),   # type: ignore [attr-defined]
                indexes=var.sizes,      # type: ignore [attr-defined]
                datasz=var.datasz       # type: ignore [attr-defined]
            )
            if not self.symtable.add(ident=var.name, info=info, context=self.context): #type: ignore[attr-defined]
                self._raise_error(10, tk)
        return AST.Command(name="DIM", args=args)

    @astnode
    def _parse_array_declaration(self, onlybracket = False) -> AST.Array:
        """ <array_declaration> ::= IDENT([INT[,INT]]) """
        var = self._expect(TokenType.IDENT).lexeme
        vartype = AST.exptype_fromname(var)
        datasz = AST.exptype_memsize(vartype)
        sizes = [10]
        sizesexp: list[AST.Statement] = []
        if self._current_is(TokenType.LBRACK):
            self._advance()
            endsym = TokenType.RBRACK
        elif not onlybracket:
            self._expect(TokenType.LPAREN)
            endsym = TokenType.RPAREN
        if not self._current_is(endsym):
            # We set the current elements to BASIC default 10 and leave
            # the optimizer and emitter to deal with real dimensions so expressions
            # can get the oportunity to be reduced to literal integers.
            sizesexp = [self._parse_int_expression(allowcast=False)]
            while self._current_is(TokenType.COMMA):
                self._advance()
                sizesexp.append(self._parse_int_expression(allowcast=False))
                sizes.append(10)
        self._expect(endsym)
        fixedexp: Optional[AST.Statement] = None
        if vartype == AST.ExpType.String and self._current_is(TokenType.KEYWORD, lexeme="FIXED"):
            self._advance()
            fixedexp = self._parse_int_expression(allowcast=False)
        return AST.Array(var, vartype, sizes, sizesexp, datasz, fixedexp)

    @astnode
    def _parse_DRAW(self) -> AST.Command:
        """ <DRAW> ::= DRAW <int_expression>,<int_expression>[,<int_expression>[,<int_expression>]] """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
            if self._current_is(TokenType.COMMA):
                self._advance()
                args.append(self._parse_int_expression())
        return AST.Command(name="DRAW", args=args)

    @astnode
    def _parse_DRAWR(self) -> AST.Command:
        """ <DRAWR> ::= DRAWR <int_expression>,<int_expression>[,<int_expression>] """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        return AST.Command(name="DRAWR", args=args)

    @astnode
    def _parse_EDIT(self) -> AST.Command:
        """ <EDIT> ::= EDIT INT """
        # A direct command that is not allowed in compiled programs    
        self._advance()
        num = self._expect(TokenType.INT)
        args: list[AST.Statement] = [AST.Integer(value = cast(int, num.value))]
        return AST.Command(name="EDIT", args=args)

    @astnode
    def _parse_EI(self) -> AST.Command:
        """ <EI> ::= EI """
        self._advance()
        return AST.Command(name="EI")

    @astnode
    def _parse_ELSE(self) -> AST.BlockEnd:
        """ <ELSE> ::== ELSE """
        tk = self._advance()
        if len(self.codeblocks) == 0 or "ELSE" not in self.codeblocks[-1].until_keywords:
            self._raise_error(37, tk)
        codeblock = self.codeblocks[-1]
        if isinstance(codeblock.start_node, AST.If):
            codeblock.start_node.has_else = True
            codeblock.until_keywords = ("END IF",)
        else:
            self._raise_error(2, tk)
        return AST.BlockEnd(name="ELSE")

    @astnode
    def _parse_END(self) -> AST.Command:
        """ <END> ::= END """
        self._advance()
        return AST.Command(name="END")

    @astnode
    def _parse_ENT(self) -> AST.Command:
        """ <ENT> ::= ENT <int_expression>[,<ent_section>][,<ent_section>][,<ent_section>][,<ent_section>][,<ent_section>] """
        """ <ent_section> ::= <int_expression>,<int_expression>,<int_expression> | <int_expression>,<int_expression> """
        # NOTE: Sections will be integers of 3 bytes: byte, byte, byte or 2-bytes, byte.
        # All sections must be integers and be of one of the two variants.
        tk = self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        while self._current_is(TokenType.COMMA):
            self._advance()
            # Tone values could be preceded by '=' symbols which denotes the start of a 2 values section
            # we ignore that and use the total amount of arguments to decide the kind of section
            self._match(TokenType.COMP, lex="=")
            args.append(self._parse_int_expression())
        totalargs = len(args[1:])
        if totalargs > 5*3 or (totalargs % 2 != 0 and totalargs % 3 != 0):
            self._raise_error(5, tk)
        return AST.Command(name="ENT", args=args)

    @astnode
    def _parse_ENV(self) -> AST.Command:
        """ <ENV> ::= ENV <int_expression>[,<env_section>][,<env_section>][,<env_section>][,<env_section>][,<env_section>] """
        """ <env_section> ::= <INT>,<INT>,<INT> | <INT>,<INT> """
        # NOTE: Sections will be integers of 3 bytes: byte, byte, byte or byte, 2-bytes.
        # All sections must be integers and be of one of the two variants.
        tk = self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        while self._current_is(TokenType.COMMA):
            self._advance()
            # In some BASIC code tone values are preceed by = which seems
            # to be ignored by the BASIC interpreter
            self._match(TokenType.COMP, lex="=")
            args.append(self._parse_int_expression())
        totalargs = len(args[1:])
        if totalargs > 5*3 or (totalargs % 2 != 0 and totalargs % 3 != 0):
            self._raise_error(5, tk)
        return AST.Command(name="ENV", args=args)

    @astnode
    def _parse_EOF(self) -> AST.Function:
        """ <EOF> ::= EOF """
        self._advance()
        return AST.Function(name="EOF", etype=AST.ExpType.Integer)    

    def _parse_ERASE(self) -> AST.Command:
        """ <ERASE> ::= ERASE IDENT[,IDENT]* """
        self._advance()
        args: list[AST.Statement] = []
        tk = self._expect(TokenType.IDENT)
        entry = self.symtable.find(tk.lexeme.upper(), SymType.Array, context=self.context)
        if entry is None:
            self._raise_error(2, tk)
        else:
            args.append(AST.Variable(name=tk.lexeme, etype=entry.exptype))
        while self._current_is(TokenType.COMMA):
            self._advance()
            tk = self._expect(TokenType.IDENT)
            entry = self.symtable.find(tk.lexeme, SymType.Array, context=self.context)
            if entry is None:
                self._raise_error(2, tk)
            else:
                args.append(AST.Variable(name=tk.lexeme, etype=entry.exptype))
        return AST.Command(name="ERASE", args=args)

    @astnode
    def _parse_ERL(self) -> AST.Function:
        """ <ERL> ::= ERL """
        # Will return the line number where the last ERROR command was executed 
        self._advance()
        return AST.Function(name="ERL", etype=AST.ExpType.Integer)

    @astnode
    def _parse_ERR(self) -> AST.Function:
        """ <ERR> ::= ERR """
        # Will return the error code number used in the last executed ERROR command
        self._advance()
        return AST.Function(name="ERR", etype=AST.ExpType.Integer)

    def _parse_ERROR(self) -> AST.Command:
        """ <ERROR> ::= ERROR <int_expression> """
        # Sets the values for ERR and ERL
        self._advance()
        args = [self._parse_int_expression()]
        return AST.Command(name="ERROR", args=args)

    @astnode
    def _parse_EVERY(self) -> AST.Command:
        """ <EVERY> ::= EVERY <int_expression>[,<int_expression>] <GOSUB> """
        self._advance()
        args = [self._parse_int_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        tk = self._current()
        if not self._current_is(TokenType.KEYWORD, lexeme="GOSUB"):
            self._raise_error(2, tk)
        args.append(self._parse_GOSUB())
        self.hasevents = True
        return AST.Command(name="EVERY", args=args)

    @astnode
    def _parse_EXIT_FOR(self) -> AST.Command:
        """ <EXIT FOR> ::= EXIT FOR """
        tk = self._advance()
        cblock: Optional[CodeBlock] = None
        for cblock in reversed(self.codeblocks):
            if "NEXT" in cblock.until_keywords:
                break
            if not "END IF" in cblock.until_keywords:
                break
        if cblock is None or "NEXT" not in cblock.until_keywords:
            self._raise_error(2, tk, info="unexpected EXIT FOR")
        return AST.Command(name="EXIT FOR")

    @astnode
    def _parse_EXIT_WHILE(self) -> AST.Command:
        """ <EXIT WHILE> ::= EXIT WHILE """
        tk = self._advance()
        cblock: Optional[CodeBlock] = None
        for cblock in reversed(self.codeblocks):
            if "WEND" in cblock.until_keywords:
                break
            if not "END IF" in cblock.until_keywords:
                break
        if cblock is None or "WEND" not in cblock.until_keywords:
            self._raise_error(2, tk, info="unexpected EXIT WHILE")
        return AST.Command(name="EXIT WHILE")

    @astnode
    def _parse_EXP(self) -> AST.Function:
        """ <EXP> ::= EXP(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_real_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="EXP", etype=AST.ExpType.Real, args=args)

    @astnode
    def _parse_FILL(self) -> AST.Command:
        """ <FILL> ::= FILL <int_expression> """
        # BASIC 1.1
        self._advance()
        args = [self._parse_int_expression()]
        return AST.Command(name="FILL", args=args)

    @astnode
    def _parse_FIX(self) -> AST.Function:
        """ <FIX> ::= FIX(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_num_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="FIX", etype=AST.ExpType.Integer, args=args)
   
    @astnode 
    def _parse_FN(self) -> AST.Command:
        # DEF parses FN so if we arrive here is a syntax error
        tk = self._advance()
        self._raise_error(2, tk)
        return AST.Command(name="FN")

    @astnode
    def _parse_FOR(self) -> AST.ForLoop:
        """ <FOR> ::= FOR IDENT = <int_expression> TO <int_expression> [STEP <int_expression>] """
        fortk = self._advance()
        # ArrayItems are not suported here so we don't call _parse_ident()
        tk = self._expect(TokenType.IDENT)
        var = tk.lexeme.upper()
        vartype = AST.exptype_fromname(var)
        if not AST.exptype_isint(vartype):
            self._raise_error(13, tk)
        # Let's check that we are not dealing with a constant
        self._check_noconst(var, tk)
        # FOR can declare variables so add it (or increase writes)
        inserted = self.symtable.add(
                ident=var,
                info=SymEntry(
                    symtype=SymType.Variable,
                    exptype=vartype,
                    locals=SymTable(),
                    datasz=AST.exptype_memsize(vartype),
                    writes=2    # do not consider this as only one write so we block "optimizations"
                ),
                context=self.context
            )
        if not inserted:
            self._raise_error(2, tk)
        self._expect(TokenType.COMP, "=")
        start = self._parse_int_expression()
        self._expect(TokenType.KEYWORD, "TO")
        end = self._parse_int_expression()
        step = None
        if self._match(TokenType.KEYWORD, "STEP"):
            step = self._parse_int_expression()
        index = AST.Variable(name=var, etype=vartype)
        index.set_origin(tk.line, tk.col)
        node = AST.ForLoop(var=index, start=start, end=end, step=step)
        self.codeblocks.append(CodeBlock(
            type=BlockType.FOR,
            until_keywords=("NEXT",),
            start_node=node,
            tk=fortk
        ))
        return node

    @astnode
    def _parse_FRAME(self) -> AST.Command:
        """ <FRAME> ::= FRAME """
        # BASIC 1.1
        self._advance()
        return AST.Command(name="FRAME")

    @astnode
    def _parse_FRE(self) -> AST.Function:
        """ <FRE> ::= FRE(0) | FRE("") """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="FRE", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_FUNCTION(self) -> AST.DefFUN:
        """ <SUB> ::== FUNCTION IDENT[(IDENT[,IDENT]*)] """
        tk = self._advance()
        if self.context != "":
            # is not possible to define new functions or procs in the bgody of another
            self._raise_error(2, tk)
        tk = self._expect(TokenType.IDENT)
        if tk.lexeme.upper()[:2] == "FN":
            self._raise_error(2, tk, "FN starting chars are reserved for DEF FN functions")
        fname = "FUN" + tk.lexeme.upper()
        fargs: list[AST.Variable | AST.Array] = []
        argtypes: list[AST.ExpType] = []
        self.context = fname
        rettype = AST.exptype_fromname(tk.lexeme)
        info = SymEntry(
            symtype=SymType.Function,
            exptype=rettype,
            locals=SymTable(),
            datasz=AST.exptype_memsize(rettype)
            )
        if not self.symtable.add(ident=fname, info=info, context=""):
            self._raise_error(2, tk)
        fargs, argtypes = self._parse_arguments(info)
        # Lets update our procedure entry with
        # the last calculated parameters
        info = self.symtable.find(ident=fname, stype=SymType.Function) # type: ignore[assignment]
        if info is None:
            self._raise_error(38, tk)
        info.nargs = len(fargs)
        info.argtypes = list(argtypes)
        info.args = list(fargs)
        # time to set correctly the parameters offset now we know the total number
        for localname in info.locals.syms:
            entry = info.locals.syms[localname]
            entry.memoff = (info.nargs * 2) - entry.memoff - 2
        asm = self._match(TokenType.KEYWORD, lex="ASM") is not None
        node = AST.DefFUN(name=fname, args=fargs, asm=asm)
        self.codeblocks.append(CodeBlock(
            type=BlockType.FUNCTION,
            until_keywords=("END FUNCTION",),
            start_node=node,
            tk=tk
        ))
        return node

    @astnode
    def _parse_GOSUB(self) -> AST.Command:
        """ <GOSUB> ::= GOSUB (INT | IDENT) """
        # some compound commands call here so let's check that GOSUB
        # is really the current keyword
        tk = self._expect(TokenType.KEYWORD, lex="GOSUB")
        args: list[AST.Statement] = []
        if self._current_is(TokenType.INT):
            num = self._advance()
            args = [AST.Integer(value = cast(int, num.value))]
            args[0].line = num.line
            args[0].col = num.col
        elif self._current_is(TokenType.IDENT):
            label = self._advance()
            args = [AST.Label(value = label.lexeme)]
            args[0].line = label.line
            args[0].col = label.col
        else:
            self._raise_error(2, tk, "invalid label")
        return AST.Command(name="GOSUB", args=args)

    @astnode
    def _parse_GOTO(self) -> AST.Command:
        """ <GOTO> ::= GOTO (INT | IDENT) """
        # THEN and ELSE can arrive here parsing just a number/label so we use 
        # match and not advance
        self._match(TokenType.KEYWORD, "GOTO")
        args: list[AST.Statement] = []
        tk = self._current()
        if self._current_is(TokenType.INT):
            num = self._advance()
            args = [AST.Integer(value = cast(int, num.value))]
            args[0].line = num.line
            args[0].col = num.col
        elif self._current_is(TokenType.IDENT):
            label = self._advance()
            args = [AST.Label(value = label.lexeme)]
            args[0].line = label.line
            args[0].col = label.col
        else:
            self._raise_error(2, tk, "invalid label")
        return AST.Command(name="GOTO", args=args)

    @astnode
    def _parse_GRAPHICS_PAPER(self) -> AST.Command:
        """ <GRAPHICS_PAPER> ::= GRAPHICS PAPER <int_expression> """
        # BASIC 1.1
        self._advance()
        args = [self._parse_int_expression()]
        return AST.Command(name="GRAPHICS PAPER", args=args)
 
    @astnode   
    def _parse_GRAPHICS_PEN(self) -> AST.Command:
        """ <GRAPHICS_PEN> ::= GRAPHICS PEN <int_expression>[,<int_expression>] """
        # BASIC 1.1
        self._advance()
        args = [self._parse_int_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        return AST.Command(name="GRAPHICS PEN", args=args)

    @astnode
    def _parse_HEXSS(self) -> AST.Function:
        """ <HEXSS> ::= HEX$(<int_expression>[,<int_expression>]) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_int_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        self._expect(TokenType.RPAREN)
        return AST.Function(name="HEX$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_HIMEM(self) -> AST.Function:
        """ <HIMEN> ::= HIMEN """
        self._advance()
        return AST.Function(name="HIMEM", etype=AST.ExpType.Integer)
 
    @astnode   
    def _parse_IF(self) -> AST.If:
        """ <IF> ::= IF <int_expression> (THEN | GOTO) [<inline_then>[ELSE >inline_else>]] """
        iftk = self._advance()
        condition = self._parse_int_expression()
        tk = self._current()
        if not tk.lexeme in ("THEN", "GOTO"):
            self._raise_error(2, tk, "THEN missing")
        self._advance()
        self._match(TokenType.COMMENT) # ignore any comment after a THEN in a IF block
        if not self._current_is(TokenType.EOL):
            then_body = self._parse_inline_then()
            else_body: list[AST.Statement] = []
            if self._current_is(TokenType.KEYWORD, "ELSE"):
                self._advance()
                else_body = self._parse_inline_else()
            return AST.If(condition=condition, inline_then=then_body, inline_else=else_body)
        node = AST.If(condition=condition)
        self.codeblocks.append(CodeBlock(
            type=BlockType.IF,
            until_keywords=("ELSE","END IF"),
            start_node=node,
            tk=iftk
        ))
        return node 

    def _parse_inline_then(self) -> list[AST.Statement]:
        """ <inline_then> ::= <statement>[:<statement>]* """
        if self._current_is(TokenType.INT):
                return [self._parse_GOTO()]
        then_body: list[AST.Statement] = []
        tk = self._current()
        while not self._current_in((TokenType.EOL, TokenType.EOF)):
            stmt = self._parse_statement()
            then_body.append(stmt)
            if self._current_is(TokenType.COLON):
                self._advance()
            if self._current_is(TokenType.KEYWORD, "ELSE"):
                return then_body
        if len(then_body) == 0:
            self._raise_error(2, tk)
        return then_body

    def _parse_inline_else(self) -> list[AST.Statement]:
        """ <inline_else> ::= <statement>[:<statement>]* """
        if self._current_is(TokenType.INT):
                return [self._parse_GOTO()]
        else_body: list[AST.Statement] = []
        tk = self._current()
        while not self._current_in((TokenType.EOL, TokenType.EOF)):
            stmt = self._parse_statement()
            else_body.append(stmt)
            if self._current_is(TokenType.COLON):
                self._advance()
        if len(else_body) == 0:
            self._raise_error(2, tk)
        return else_body

    @astnode
    def _parse_END_IF(self) -> AST.BlockEnd:
        tk = self._advance()
        if len(self.codeblocks) == 0 or "END IF" not in self.codeblocks[-1].until_keywords:
            self._raise_error(36, tk)
        self.codeblocks.pop()
        return AST.BlockEnd(name="END IF")

    @astnode
    def _parse_END_FUNCTION(self) -> AST.Command:
        """ <END_FUNCTION> ::= END FUNCTION """
        tk = self._advance()
        if len(self.codeblocks) == 0 or not "END FUNCTION" in self.codeblocks[-1].until_keywords:
            self._raise_error(43, tk)
        cblock = self.codeblocks.pop()
        self.context=""
        return AST.Command(name="END FUNCTION", args=[cblock.start_node])

    @astnode
    def _parse_END_SELECT(self) -> AST.BlockEnd:
        tk = self._advance()
        if len(self.codeblocks) == 0 or "END SELECT" not in self.codeblocks[-1].until_keywords:
            self._raise_error(46, tk)
        node = self.codeblocks.pop().start_node
        if isinstance(node, AST.SelectCase):
            if node.options == 0:
                self._raise_error(2, tk, "CASE statement missing")
        return AST.BlockEnd(name="END SELECT")

    @astnode
    def _parse_END_SUB(self) -> AST.Command:
        """ <END_SUB> ::= END SUB """
        tk = self._advance()
        if len(self.codeblocks) == 0 or not "END SUB" in self.codeblocks[-1].until_keywords:
            self._raise_error(41, tk)
        cblock = self.codeblocks.pop()
        self.context=""
        return AST.Command(name="END SUB", args=[cblock.start_node])

    @astnode
    def _parse_INK(self) -> AST.Command:
        """ <INK> ::= INK <int_expression()>,<int_expression>[,<int_expression>] """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        return AST.Command(name="INK", args=args)

    @astnode
    def _parse_INKEY(self) -> AST.Function:
        """ <INKEY> ::= INKEY(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="INKEY", etype=AST.ExpType.Integer, args=args)
 
    @astnode   
    def _parse_INKEYSS(self) -> AST.Function:
        """ <INKEYSS> ::= INKEY$ """
        self._advance()
        return AST.Function(name="INKEY$", etype=AST.ExpType.String)

    @astnode
    def _parse_INP(self) -> AST.Function:
        """ <INP> ::= INP(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="INP", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_INPUT(self) -> AST.Input | AST.ReadIn:
        """ <INPUT> := INPUT [#<int_expression>][STRING(;|,)] <ident> [,<ident>] """
        inputtk = self._advance()
        stream: Optional[AST.Statement] = None; 
        prompt: str = ""
        question: bool = True
        vars: list[AST.Variable | AST.ArrayItem] = []
        if self._current_is(TokenType.HASH):
            self._advance()
            stream = self._parse_int_expression()
            self._expect(TokenType.COMMA)
        if self._current_is(TokenType.STRING):
            tk = self._advance()
            prompt = cast(str, tk.value)
            if not self._current_in((TokenType.COMMA, TokenType.SEMICOLON)):
                self._raise_error(2, tk)
        if self._match(TokenType.COMMA): question = False
        self._match(TokenType.SEMICOLON)
        while True:
            var = self._parse_ident()
            vars.append(var)
            if not self._match(TokenType.COMMA):
                break
        # Input can declare variables so we need to add any new ones to the symtable
        # but only if they are not ArrayItems, which must be declared with DIM.
        # If the variable already exists, this call will increase the number of
        # writes which is used by the optimizer
        for v in vars:
            if isinstance(v, AST.Variable):
                self._check_noconst(v.name, inputtk)
                self.symtable.add(
                    ident=v.name,
                    info=SymEntry(
                        symtype=SymType.Variable,
                        exptype=v.etype,
                        locals=SymTable(),
                        datasz=AST.exptype_memsize(v.etype)
                    ),
                    context=self.context
                )
        if stream is not None and isinstance(stream,AST.Integer) and stream.value == 9:
            # Input used to read from a file
            return AST.ReadIn(vars=vars)
        return AST.Input(stream=stream, prompt=prompt, question=question, vars=vars)

    @astnode
    def _parse_INSTR(self) -> AST.Function:
        """ <INSTR> ::= INSTR([<int_expression>,]<str_expression(),<str_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_expression()]
        remain = 2 if args[0].etype == AST.ExpType.Integer else 1
        while remain:
            self._match(TokenType.COMMA)
            args.append(self._parse_str_expression())
            remain -= 1
        self._expect(TokenType.RPAREN)
        return AST.Function(name="INSTR", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_INT(self) -> AST.Function:
        """ <INT> ::= INT(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_num_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="INT", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_JOY(self) -> AST.Function:
        """ <JOY> ::= JOY(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="JOY", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_KEY(self) -> AST.Command:
        """ <KEY> ::= KEY <int_expression>,<str_expression> """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_str_expression())
        return AST.Command(name="KEY", args=args)

    @astnode
    def _parse_KEY_DEF(self) -> AST.Command:
        """
        <KEY> ::= KEY DEF <int_expression>,<int_expression>[,<keydefoptions>]
        <keydefoptions> ::== <int_expression>[,<int_expression>[,<int_expression>]]
        """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        return AST.Command(name="KEY DEF", args=args)
  
    @astnode  
    def _parse_LABEL(self) -> AST.Label:
        """ <LABEL> ::== LABEL IDENT """
        self._advance()
        label = self._expect(TokenType.IDENT)
        inserted = self.symtable.add(
            ident=label.lexeme,
            info=SymEntry(
                symtype=SymType.Label,
                exptype=AST.ExpType.Void,
                locals=SymTable()),
            context=""
        )
        if not inserted:
            self._raise_error(39, label)
        # last user defined label is used by DATA statements
        self.current_usrlabel = label.lexeme
        return AST.Label(value=label.lexeme)

    @astnode
    def _parse_LBOUND(self) -> AST.Function:
        """ <LBOUND> ::= LBOUND(IDENT[,<int_expression>])"""
        self._advance()
        self._expect(TokenType.LPAREN)
        tk = self._expect(TokenType.IDENT)
        entry = self.symtable.find(tk.lexeme, SymType.Array, context=self.context)
        if entry is None:
            self._raise_error(2, tk, "undefined array")
        args: list[AST.Statement] = [AST.Variable(name=tk.lexeme, etype=entry.exptype)]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        else:
            args.append(AST.Integer(value=1))
        self._expect(TokenType.RPAREN)
        return AST.Function(name="LBOUND", etype=AST.ExpType.Integer, args=args)

    @astnode  
    def _parse_LEFTSS(self) -> AST.Function:
        """ <LEFTSS> ::== LEFT$(<st_expression>,<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_str_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        self._expect(TokenType.RPAREN)
        return AST.Function(name="LEFT$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_LEN(self) -> AST.Function:
        """ <LEN> ::= LEN(<str_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_str_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="LEN", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_LET(self) -> AST.Assignment | AST.Statement:
        """ <LET> ::= LET <assignment> """
        self._advance()
        return self._parse_assignment()

    @astnode
    def _parse_LINE_INPUT(self) -> AST.LineInput:
        """ <LINE_INPUT>::= LINE INPUT [#<int_expression>,][;][STRING](;|,)<ident> """
        self._advance()
        stream: Optional[AST.Statement] = None; 
        prompt: str = ""
        carriage: bool = True
        question: bool = False
        if self._current_is(TokenType.HASH):
            tk = self._advance()
            stream = self._parse_int_expression()
            self._expect(TokenType.COMMA)
        if self._current_is(TokenType.SEMICOLON):
            self._advance()
            if self._current_is(TokenType.IDENT):
                question = True
            else:
                carriage = False
        if self._current_is(TokenType.STRING):
            tk = self._advance()
            prompt = cast(str, tk.value)
            if not self._current_in((TokenType.COMMA, TokenType.SEMICOLON)):
                self._raise_error(2, self._current())
            question = False if self._advance().type == TokenType.COMMA else True
        if not self._current_is(TokenType.IDENT):
            self._raise_error(2, self._current())
        tk = self._current()
        var: AST.Variable | AST.ArrayItem = self._parse_ident()
        if var.etype != AST.ExpType.String:
            self._raise_error(13, tk)
        # LINE INPUT can declare a new variable so we need to add it
        # but only if it is not an ArrayItem.
        # If the variable already exists, this call will increase the number of
        # writes which is used by the optimizer.
        if isinstance(var, AST.Variable):
            self._check_noconst(var.name, tk)
            self.symtable.add(
                ident=var.name,
                info=SymEntry(
                    symtype=SymType.Variable,
                    exptype=var.etype,
                    locals=SymTable(),
                    datasz=AST.exptype_memsize(var.etype)
                ),
                context=self.context
            )
        return AST.LineInput(stream=stream, prompt=prompt, carriage=carriage, question=question, var=var)
 
    @astnode
    def _parse_LIST(self) -> AST.Command:
        """ <LIST> ::= LIST <range>[,#<stream>]"""
        # This command doesn't make sense in a compiled program but
        # leave the emiter fail
        self._advance()
        args: list[AST.Statement] = []
        if not self._end_of_statement():
            args = [self._parse_range()]
            if self._current_is(TokenType.COMMA):
                self._advance()
                self._match(TokenType.HASH)
                args.append(self._parse_int_expression())
        return AST.Command(name="LIST", args=args)

    @astnode
    def _parse_LOAD(self) -> AST.Command:
        """ <LOAD> ::= LOAD <str_expression>[,<int_expression>]"""
        self._advance()
        args = [self._parse_str_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_uint_expression())
        return AST.Command(name="LOAD", args=args)

    @astnode
    def _parse_LOCATE(self) -> AST.Command:
        """ <LOCATE> ::= LOCATE [#<int_expression>,]<int_expression>,<int_expression> """
        self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.HASH):
            self._advance()
            args.append(self._parse_int_expression())
            self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        return AST.Command(name="LOCATE", args=args)

    @astnode
    def _parse_LOG(self) -> AST.Function:
        """ <LOG> ::= LOG(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_real_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="LOG", etype=AST.ExpType.Real, args=args)

    @astnode
    def _parse_LOG10(self) -> AST.Function:
        """ <LOG10> ::= LOG10(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_real_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="LOG10", etype=AST.ExpType.Real, args=args)

    @astnode
    def _parse_LOWERSS(self) -> AST.Function:
        """ <LOWERSS> ::= LOWER$(<str_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_str_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="LOWER$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_LTRIMSS(self) -> AST.Function:
        """ <LTRIMSS> ::= LTRIM$(<str_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_str_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="LTRIM$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_MASK(self) -> AST.Command:
        """ <MASK> ::= MASK <int_expression>[,<int_expression>] """
        self._advance()
        args = [self._parse_int_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        return AST.Command(name="MASK", args=args)

    @astnode
    def _parse_MAX(self) -> AST.Function:
        """ <MAX> ::= MAX(<num_expression>[,<num_expression>]*) """
        tk = self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_num_expression()]
        etype = args[-1].etype
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_num_expression())
            etype = etype if args[-1].etype == etype else AST.ExpType.Real
        self._expect(TokenType.RPAREN)
        if len(args) < 2:
            self._raise_error(2, tk, "wrong number of arguments")
        casted: list[AST.Statement] = []
        for a in args:
            casted.append(self._cast_numtype(a, etype))
        return AST.Function(name="MAX", etype=etype, args=casted)

    @astnode
    def _parse_MEMORY(self) -> AST.Command:
        """ <MEMORY> ::= MEMORY <int_expression>"""
        self._advance()
        args = [self._parse_uint_expression()]
        return AST.Command(name="MEMORY", args=args)

    @astnode
    def _parse_MERGE(self) -> AST.Command:
        """ <MERGE> ::= MERGE <str_expression> """
        self._advance()
        args = [self._parse_str_expression()]
        return AST.Command(name="MERGE", args=args)

    @astnode
    def _parse_MIDSS(self) -> AST.Function:
        """ <MIDSS> ::= MID$(<str_expression>,<int_expression>[,<int_expression>]) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_str_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        self._expect(TokenType.RPAREN)
        return AST.Function(name="MID$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_MIN(self) -> AST.Function:
        """ <MIN> ::= MIN(<num_expression>[,<num_expression>]*) """
        tk = self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_num_expression()]
        etype = args[-1].etype
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_num_expression())
            etype = etype if args[-1].etype == etype else AST.ExpType.Real
        self._expect(TokenType.RPAREN)
        if len(args) < 2:
            self._raise_error(2, tk, "wrong number of arguments")
        casted: list[AST.Statement] = []
        for a in args:
            casted.append(self._cast_numtype(a, etype))
        return AST.Function(name="MIN", etype=etype, args=casted)

    @astnode
    def _parse_MODE(self) -> AST.Command:
        """ <MODEA> ::= MODE <int_expression>"""
        self._advance()
        args = [self._parse_int_expression()]
        return AST.Command(name="MODE", args=args)

    @astnode
    def _parse_MOVE(self) -> AST.Command:
        """ <MOVE> ::= MOVE <int_expression>,<int_expression>[,<int_expression>[,<int_expression>]] """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
            if self._current_is(TokenType.COMMA):
                self._advance()
                args.append(self._parse_int_expression())
        return AST.Command(name="MOVE", args=args)

    @astnode
    def _parse_MOVER(self) -> AST.Command:
        """ <MOVER> ::= MOVER <int_expression>,<int_expression>[,<int_expression>[,<int_expression>]] """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
            if self._current_is(TokenType.COMMA):
                self._advance()
                args.append(self._parse_int_expression())
        return AST.Command(name="MOVER", args=args)
 
    @astnode   
    def _parse_NEW(self) -> AST.Command:
        """ <NEW> ::= NEW """
        tk = self._advance()
        return AST.Command(name="NEW")

    @astnode
    def _parse_NEXT(self) -> AST.BlockEnd:
        """ <NEXT> ::= NEXT [<ident>[,<ident>]*]"""
        tk = self._advance()
        next_vars: list[str] = []
        if len(self.codeblocks) == 0 or "NEXT" not in self.codeblocks[-1].until_keywords:
            self._raise_error(1, tk)
        codeblock = self.codeblocks.pop()
        while self._current_is(TokenType.IDENT):
            tk = self._current()
            var: AST.Variable | AST.ArrayItem = self._parse_ident()
            if not isinstance(var, AST.Variable) or not AST.exptype_isint(var.etype):
                self._raise_error(13, tk)
            node = codeblock.start_node
            next_var = var.name.upper()
            if isinstance(node, AST.ForLoop):
                orgvar = node.var.name.upper()
                if orgvar != next_var:
                    self._raise_error(1, tk)
            else:
                self._raise_error(2, tk)
            next_vars.append(next_var)
            if self._current_is(TokenType.COMMA):
                tk = self._advance()
                if not self._current_is(TokenType.IDENT):
                    self._raise_error(2, tk)
                if len(self.codeblocks) == 0 or "NEXT" not in self.codeblocks[-1].until_keywords:
                    self._raise_error(1, tk)
                codeblock = self.codeblocks.pop()
        return AST.BlockEnd(name="NEXT", vars=next_vars)

    @astnode
    def _parse_ON(self) -> AST.Command:
        """ 
        <ON> ::= ON <int_expression> <on_body> 
        <on_body> ::= (GOTO | GOSUB) INT[,INT]*
        """
        self._advance()
        args = [self._parse_int_expression()]
        if not self._current_in((TokenType.KEYWORD,), ("GOTO","GOSUB")):
            self._raise_error(2, self._current())
        cmd = "ON " + self._advance().lexeme
        while True:
            if self._current_is(TokenType.INT):
                num = self._advance()
                args.append(AST.Integer(value = cast(int, num.value)))
            elif self._current_is(TokenType.IDENT):
                label = self._advance()
                args.append(AST.Label(value = label.lexeme))
            else:
                self._raise_error(2, self._current(), "invalid label")
            if not self._current_is(TokenType.COMMA):
                break
            self._advance()
        return AST.Command(name=cmd, args=args)       

    @astnode
    def _parse_ON_BREAK(self) -> AST.Command:
        """ 
        <ON_BREAK> ::= ON BREAK <on_break_body>
        <on_break_body> ::= COUNT | STOP | GOSUB INT
        """
        self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.KEYWORD, "COUNT"):
            self._advance()
            cmd = "ON BREAK COUNT"
        elif self._current_is(TokenType.KEYWORD, "STOP"):
            self._advance()
            cmd = "ON BREAK STOP"
        elif self._current_is(TokenType.KEYWORD, "GOSUB"):
            self._advance()
            cmd = "ON BREAK GOSUB"
            num = self._expect(TokenType.INT)
            args.append(AST.Integer(value = cast(int, num.value)))
        else:
            self._raise_error(2, self._current())
        return AST.Command(name=cmd, args=args)
 
    @astnode   
    def _parse_ON_ERROR_GOTO(self) -> AST.Command:
        """ <ON_ERROR_GOTO> ::= ON ERROR GOTO (INT|LABEL)"""
        tk = self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.INT):
            num = self._advance()
            args = [AST.Integer(value = cast(int, num.value))]
            args[0].set_origin(num.line, num.col)
        elif self._current_is(TokenType.IDENT):
            label = self._advance()
            args = [AST.Label(value = label.lexeme)]
            args[0].set_origin(label.line, label.col)
        else:
            self._raise_error(2, tk, "invalid label")
        return AST.Command(name="ON ERROR GOTO", args=args)

    @astnode
    def _parse_ON_SQ(self) -> AST.Command:
        """ <ON_SQ> ::= ON SQ(<int_expression>) GOSUB INT """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        if self._current_is(TokenType.KEYWORD, "GOSUB"):
            gosub = self._parse_GOSUB()
            args.append(gosub.args[0])
        else:
            self._raise_error(2, self._current())
        return AST.Command(name="ON SQ", args=args)

    @astnode
    def _parse_OPENIN(self) -> AST.Command:
        """ <OPENIN> ::= OPENIN <str_expression> """
        self._advance()
        args = [self._parse_str_expression()]
        return AST.Command(name="OPENIN", args=args)
  
    @astnode  
    def _parse_OPENOUT(self) -> AST.Command:
        """ <OPENOUT> ::= OPENOUT <str_expression> """
        self._advance()
        args = [self._parse_str_expression()]
        return AST.Command(name="OPENOUT", args=args)

    @astnode
    def _parse_ORIGIN(self) -> AST.Command:
        """
        <ORIGIN> ::= ORIGIN <int_expression>,<int_expression>[<origin_wnd>]
        <origin_wnd> ::= ,<int_expression>,<int_expression>,<int_expression>,<int_expression>
        """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        if self._current_is(TokenType.COMMA):
            for _ in range(4):
                self._expect(TokenType.COMMA)
                args.append(self._parse_int_expression())
        return AST.Command(name="ORIGIN", args=args)

    @astnode
    def _parse_OUT(self) -> AST.Command:
        """ <OUT> ::= OUT <int_expression>,<int_expression> """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        return AST.Command(name="OUT", args=args)

    @astnode
    def _parse_PAPER(self) -> AST.Command:
        """ <PAPER> ::= PAPER [#<int_expression>,]<int_expression> """
        self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.HASH):
            self._advance()
            args = [self._parse_int_expression()]
            self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        return AST.Command(name="PAPER", args=args)

    @astnode
    def _parse_PEEK(self) -> AST.Function:
        """ <PEEK> ::= PEEK(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_uint_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="PEEK", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_PEN(self) -> AST.Command:
        """ <PEN> ::= PEN [#<int_expression>,]<int_expression> """
        self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.HASH):
            self._advance()
            args = [self._parse_int_expression()]
            self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        return AST.Command(name="PEN", args=args)

    @astnode
    def _parse_PI(self) -> AST.Function:
        """ <PI> ::= PI """
        self._advance()
        return AST.Function(name="PI", etype=AST.ExpType.Real)

    @astnode
    def _parse_PLOT(self) -> AST.Command:
        """ <PLOT> ::= PLOT <int_expression>,<int_expression>[,<int_expression>][,<int_expression>] """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        return AST.Command(name="PLOT", args=args)

    @astnode
    def _parse_PLOTR(self) -> AST.Command:
        """ <PLOTR> ::= PLOTR <int_expression>,<int_expression>[,<int_expression>][,<int_expression>] """
        self._advance()
        args = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        while self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        return AST.Command(name="PLOTR", args=args)

    @astnode
    def _parse_POKE(self) -> AST.Command:
        """ <POKE> ::= POKE <int_expression>,<int_expression> """
        self._advance()
        args = [self._parse_uint_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        return AST.Command(name="POKE", args=args)

    @astnode
    def _parse_POS(self) -> AST.Function:
        """ <POS> ::= POS(#<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        self._expect(TokenType.HASH)
        args = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="POS", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_PRINT(self) -> AST.Print:
        """
        <PRINT> ::= PRINT [#<int_expression>,][<print_items>][print_using][print_separator]
        <print_items> ::= <expression>[;|,]<print_items> | <expression>
        <print_using> ::= USING <str_expression>,<expression>[]
        <print_separator> ::= ; | , 
        """
        self._advance()
        stream: Optional[AST.Statement] = None
        items: list[AST.Statement] = []
        if self._current_is(TokenType.HASH):
            self._advance()
            stream = self._parse_int_expression()
            self._match(TokenType.COMMA)
        while not self._end_of_statement():
            if self._current_in((TokenType.COMMA, TokenType.SEMICOLON)):
                sym = self._advance()
                sep = AST.Separator(symbol=sym.lexeme)
                sep.line = sym.line
                sep.col = sym.col
                items.append(sep)
            elif self._current_in((TokenType.KEYWORD,), ("SPC", "TAB")):
                items.append(self._parse_keyword())
            elif self._current_in((TokenType.KEYWORD,), ("USING",)):
                tk = self._advance()
                args = [self._parse_str_expression()]
                self._expect(TokenType.SEMICOLON)
                args.append(self._parse_expression())
                while self._current_is(TokenType.COMMA):
                    self._advance()
                    args.append(self._parse_expression())
                item = AST.Command(name="USING", args=args)
                item.line = tk.line
                item.col = tk.col
                items.append(item)
            else:
                items.append(self._parse_expression())
        return AST.Print(stream=stream, items=items)      

    @astnode
    def _parse_RAD(self) -> AST.Command:
        """ <RAD> ::= RAD """
        self._advance()
        return AST.Command(name="RAD")
  
    @astnode  
    def _parse_RANDOMIZE(self) -> AST.Command:
        """ <RANDOMIZE> ::= RANDOMIZE [<num_expression>] """
        self._advance()
        args: list[AST.Statement] = []
        if not self._end_of_statement():
            args = [self._parse_real_expression()]
        return AST.Command(name="RANDOMIZE", args=args)

    @astnode
    def _parse_READ(self) -> AST.Command:
        """ <READ> ::= READ <ident>[,<ident>]* """
        self._advance()
        vars: list[AST.Statement] = []
        while True:
            var = self._parse_ident()
            vars.append(var)
            # READ can declare new variables so we need to add any new ones to the symtable
            # but not if they are Array items.
            # If the variable already exists, this call will increase the number of
            # writes which is used by the optimizer
            if isinstance(var, AST.Variable):
                tk = self._current()
                self._check_noconst(var.name, tk)
                self.symtable.add(
                    ident=var.name,
                    info=SymEntry(
                        symtype=SymType.Variable,
                        exptype=var.etype,
                        locals=SymTable(),
                        datasz=AST.exptype_memsize(var.etype)
                    ),
                    context=self.context
                )
            if not self._current_is(TokenType.COMMA):
                break
            self._advance()
        return AST.Command(name="READ", args=vars)

    @astnode
    def _parse_READIN(self) -> AST.ReadIn:
        """ <READIN> ::= READIN <ident>[,<ident>]* """
        self._advance()
        vars: list[AST.Variable | AST.ArrayItem] = []
        while True:
            var = self._parse_ident()
            vars.append(var)
            # READIN can declare new variables so we need to add any new ones to the symtable
            # but not if they are Array items.
            # If the variable already exists, this call will increase the number of
            # writes which is used by the optimizer
            if isinstance(var, AST.Variable):
                tk = self._current()
                self._check_noconst(var.name, tk)
                self.symtable.add(
                    ident=var.name,
                    info=SymEntry(
                        symtype=SymType.Variable,
                        exptype=var.etype,
                        locals=SymTable(),
                        datasz=AST.exptype_memsize(var.etype)
                    ),
                    context=self.context
                )
            if not self._current_is(TokenType.COMMA):
                break
            self._advance()
        return AST.ReadIn(vars=vars)

    @astnode
    def _parse_RECORD(self) -> AST.Command:
        """ <RECORD> ::= RECORD IDENT; IDENT[,IDENT]* """
        tk = self._advance()
        if self.context != "":
            self._raise_error(2, tk, "records must be declared in the global scope")
        tk = self._expect(TokenType.IDENT)
        root = tk.lexeme
        self._expect(TokenType.SEMICOLON)
        args: list[AST.Statement] = [AST.String(value=root)]
        while self._current_is(TokenType.IDENT):
            argtk = self._expect(TokenType.IDENT)
            var = root + "." + argtk.lexeme
            vartype = AST.exptype_fromname(argtk.lexeme)
            datasz = AST.exptype_memsize(vartype)
            fixedexp: Optional[AST.Statement] = None
            if vartype == AST.ExpType.String and self._current_is(TokenType.KEYWORD, lexeme="FIXED"):
                self._advance()
                fixedexp = self._parse_int_expression(allowcast=False)
            inserted = self.symtable.add(
                ident=var,
                info=SymEntry(
                    symtype=SymType.Record,
                    exptype=vartype,
                    locals=SymTable(),
                    datasz=datasz,
                ),
            )
            if not inserted:
                self._raise_error(2, tk, info="record redifinition")
            recordvar = AST.Variable(var, vartype, fixedexp)
            recordvar.set_origin(argtk.line, argtk.col)
            args.append(recordvar)
            if self._current_is(TokenType.COMMA):
                self._advance()
            else:
                break
        return AST.Command(name="RECORD", args=args)

    @astnode
    def _parse_RELEASE(self) -> AST.Command:
        """ <RELEASE> ::= RELEASE <int_expression> """
        self._advance()
        args = [self._parse_int_expression()]
        return AST.Command(name="RELEASE", args=args)

    @astnode
    def _parse_REMAIN(self) -> AST.Function:
        """ <REMAIN> ::= REMAIN(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="REMAIN", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_RENUM(self) -> AST.Command:
        """ <RENUM> ::= RENUM [<int_expression>[,<int_expression>[,<int_expression>]]] """
        tk = self._advance()
        # This command doesn't make sense in a compiled program
        self._raise_error(21, tk)
        return AST.Command(name="RENUM")

    @astnode
    def _parse_RESTORE(self) -> AST.Command:
        """ <RESTORE> ::= RESTORE [INT | IDENT] """
        rtk = self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.INT):
            num = self._advance()
            args = [AST.Integer(value = cast(int, num.value))]
            args[0].set_origin(num.line,num.col)
        elif self._current_is(TokenType.IDENT):
            label = self._advance()
            args = [AST.Label(value = label.lexeme)]
            args[0].set_origin(label.line,label.col)
        return AST.Command(name="RESTORE", args=args)

    @astnode
    def _parse_RESUME(self) -> AST.Command:
        """ <RESUME> ::= RESUME [<int_expression> | NEXT] """
        self._advance()
        # Probably this doesn't make sense in a compiled program
        # but leave the emiter to fail if needed
        args: list[AST.Statement] = []
        if not self._end_of_statement():
            if self._current_is(TokenType.KEYWORD, "NEXT"):
                self._advance()
                return AST.Command(name="RESUME", args=[AST.Command(name="NEXT")])
            args = [self._parse_int_expression()]
        return AST.Command(name="RESUME", args=args)

    @astnode
    def _parse_RETURN(self) -> AST.Command:
        """ <RETURN> ::= RETURN """
        self._advance()
        return AST.Command(name="RETURN")
    
    @astnode
    def _parse_RIGHTSS(self) -> AST.Function:
        """ <RIGHTSS> ::== RIGHT$(<str_expression>,<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_str_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        self._expect(TokenType.RPAREN)
        return AST.Function(name="RIGHT$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_RND(self) -> AST.Function:
        """ <RND> ::= RND [(<int_expression>)] """
        self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.LPAREN):
            self._advance()
            args = [self._parse_int_expression()]
            self._expect(TokenType.RPAREN)
        return AST.Function(name="RND", etype=AST.ExpType.Real, args=args)

    @astnode
    def _parse_ROUND(self) -> AST.Function:
        """ <ROUND> ::= ROUND(<num_expression>[,<int_expression>]) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_real_expression()]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        self._expect(TokenType.RPAREN)
        return AST.Function(name="ROUND", etype=AST.ExpType.Real, args=args)

    @astnode
    def _parse_RTRIMSS(self) -> AST.Function:
        """ <RTRIMSS> ::= RTRIM$(<str_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_str_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="RTRIM$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_RUN(self) -> AST.Command:
        """ <RUN> ::= RUN [INT | IDENT | STRING] """
        self._advance()
        args: list[AST.Statement] = []
        tk = self._current()
        if self._current_is(TokenType.INT):
            num = self._advance()
            args = [AST.Integer(value = cast(int, num.value))]
            args[0].set_origin(num.line, num.col)
        elif self._current_is(TokenType.IDENT):
            label = self._advance()
            args = [AST.Label(value = label.lexeme)]
            args[0].set_origin(label.line, label.col)
        elif self._current_is(TokenType.STRING):
            fname = self._advance()
            args = [AST.String(value = cast(str, fname.value))]
            args[0].set_origin(fname.line, fname.col)
        return AST.Command(name="RUN", args=args)

    @astnode
    def _parse_SAVE(self) -> AST.Command:
        """ <SAVE> ::= SAVE STRING[,CHAR][,<int_expression>[,<int_expression>[,<int_expression]]] """
        self._advance()
        args: list[AST.Statement] = [self._parse_str_expression()]
        if not self._end_of_statement():
            self._expect(TokenType.COMMA)
            tk = self._expect(TokenType.IDENT)
            lex = tk.lexeme.upper()
            if lex not in ('A','B','P'):
                self._raise_error(5, tk)
            args.append(AST.String(value=lex))
            while not self._end_of_statement():
                self._expect(TokenType.COMMA)
                args.append(self._parse_uint_expression())
        return AST.Command(name="SAVE", args=args)

    @astnode
    def _parse_SELECT_CASE(self) -> AST.SelectCase:
        """ <SELECT CASE> ::= SELECT CASE <int_expression> """
        tk = self._advance()
        cond: AST.Statement = self._parse_int_expression()
        node = AST.SelectCase(condition=cond)
        self.codeblocks.append(CodeBlock(
            type=BlockType.SELECT,
            until_keywords=("END SELECT",),
            start_node=node,
            tk=tk
        ))
        return node

    @astnode
    def _parse_SGN(self) -> AST.Function:
        """ <SGN> ::= SGN(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_num_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="SGN", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_SHARED(self) -> AST.Command:
        """ <SHARED> ::= IDENT | ARRAY[], [IDENT | ARRAY[]]* """
        # This allows the user to signal a variable or array inside a sub or
        # function as a global variable and not local one.
        # Added from Locomotive BASIC 2 PLUS
        self._advance()
        args: list[AST.Statement] = []
        while True:
            tk = self._expect(TokenType.IDENT)
            var = tk.lexeme
            vartype = AST.exptype_fromname(var)
            added = False
            if self._current_is(TokenType.LBRACK):
                self._advance()
                self._expect(TokenType.RBRACK)
                entry = self.symtable.find(var, SymType.Array)
                if entry is None:
                    self._raise_error(2, tk, "undefined global array")
                else:
                    # local and global share the same SymEntry structure
                    added = self.symtable.add_shared(var, entry, self.context)
            else:
                if "$." in var:
                    self._raise_error(2, tk, info="unexpected record access")
                entry = self.symtable.find(var, SymType.Variable)
                if entry is None:
                    self._raise_error(2, tk, "undefined global variable")
                else:
                    added = self.symtable.add_shared(var, entry, self.context)
                    if entry.const is not None:
                        # SHARED CONSTANT
                        localentry = self.symtable.find(var, SymType.Variable, context=self.context)
                        if localentry is not None:
                            localentry.const = entry.const
            if not added:
                self._raise_error(2, tk, info="variable already declared")
            args.append(AST.Variable(var, vartype))
            if self._current_is(TokenType.COMMA):
                self._advance()
            else:
                break
        return AST.Command(name="SHARED", args=args)

    @astnode
    def _parse_SIN(self) -> AST.Function:
        """ <SIN> ::= SIN(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_real_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="SIN", etype=AST.ExpType.Real, args=args)

    @astnode
    def _parse_SOUND(self) -> AST.Command:
        """ <SOUND> ::= SOUND <int_expression>,<int_expression>[,<int_expression>]* """
        # the extra int parameters are:
        # duration, volume, volume envelope, tone envelope, noise period 
        self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()] # channel
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())                  # tone
        # optative params
        for i in range(5):              
            if not self._current_is(TokenType.COMMA):
                if i == 0:   args.append(AST.Integer(value=20)) # default duration
                elif i == 1: args.append(AST.Integer(value=12)) # default volume
                elif i == 2: args.append(AST.Integer(value=0))  # ENV
                elif i == 3: args.append(AST.Integer(value=0))  # ENT
                elif i == 4: args.append(AST.Integer(value=0))  # Noise
            elif self._next_is(TokenType.COMMA):
                # we do not support the option of leave a default value as ,,
                self._raise_error(2, self._current())
            else:
                self._advance()
                args.append(self._parse_int_expression())
        return AST.Command(name="SOUND", args=args)

    @astnode
    def _parse_SPACESS(self) -> AST.Function:
        """ <SPACESS> ::= SPACE$(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="SPACE$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_SPC(self) -> AST.Command:
        """ <SPC> ::= SPC(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Command(name="SPC", args=args)

    @astnode
    def _parse_SPEED_INK(self) -> AST.Command:
        """ <SPEED_INK> ::= SPEED INK <int_expression>,<int_expression> """
        self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        return AST.Command(name="SPEED INK", args=args)

    @astnode
    def _parse_SPEED_KEY(self) -> AST.Command:
        """ <SPEED_KEY> ::= SPEED KEY <int_expression>,<int_expression> """
        self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        return AST.Command(name="SPEED KEY", args=args)

    @astnode
    def _parse_SPEED_WRITE(self) -> AST.Command:
        """ <SPEED_WRITE> ::= SPEED WRITE <int_expression> """
        self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        return AST.Command(name="SPEED WRITE", args=args)

    @astnode
    def _parse_SQ(self) -> AST.Function:
        """ <SQ> ::= SQ(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="SQ", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_SQR(self) -> AST.Function:
        """ <SQR> ::= SQR(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_real_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="SQR", etype=AST.ExpType.Real, args=args)

    @astnode
    def _parse_STOP(self) -> AST.Command:
        """ <STOP> ::= STOP """
        self._advance()
        return AST.Command(name="STOP")

    @astnode
    def _parse_STRSS(self) -> AST.Function:
        """ <STRSS> ::= STR$(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_num_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="STR$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_STRINGSS(self) -> AST.Function:
        """ <STRINGSS> ::= STRING$(<int_expression>,(<str_expression>|<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        # char o ASCII code number
        tk = self._current()
        args.append(self._parse_expression())
        if args[-1].etype not in (AST.ExpType.Integer, AST.ExpType.String):
            self._raise_error(5, tk)
        self._expect(TokenType.RPAREN)
        return AST.Function(name="STRING$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_SUB(self) -> AST.DefSUB:
        """ <SUB> ::== SUB IDENT[(IDENT[,IDENT]*)] """
        tk = self._advance()
        if self.context != "":
            # is not possible to define new functions or procs in the body of another
            self._raise_error(2, tk, "routine defined inside another routine body")
        tk = self._expect(TokenType.IDENT)
        pname = "SUB" + tk.lexeme.upper()
        pargs: list[AST.Variable | AST.Array] = []
        argtypes: list[AST.ExpType] = []
        self.context = pname
        info = SymEntry(
            symtype=SymType.Procedure,
            exptype=AST.ExpType.Void,
            locals=SymTable(),
            )
        if not self.symtable.add(ident=pname, info=info, context=""):
            self._raise_error(2, tk)
        pargs, argtypes = self._parse_arguments(info)
        # Lets update our procedure entry with
        # the last calculated parameters
        info = self.symtable.find(ident=pname, stype=SymType.Procedure) # type: ignore[assignment]
        if info is None:
            self._raise_error(38, tk)
        info.nargs = len(pargs)
        info.argtypes = list(argtypes)
        info.args = list(pargs)
        # time to set correctly the parameters offset now we know the total number
        for localname in info.locals.syms:
            entry = info.locals.syms[localname]
            entry.memoff = (info.nargs * 2) - entry.memoff - 2
        asm = self._match(TokenType.KEYWORD, lex="ASM") is not None
        node = AST.DefSUB(name=pname, args=pargs, asm=asm)
        self.codeblocks.append(CodeBlock(
            type=BlockType.SUB,
            until_keywords=("END SUB",),
            start_node=node,
            tk=tk
        ))
        return node

    @astnode
    def _parse_SYMBOL(self) -> AST.Command:
        """ <SYMBOL> ::= SYMBOL <int_expression>(,<int_expression>)* """
        self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        for _ in range(8):
            self._expect(TokenType.COMMA)
            args.append(self._parse_int_expression())
        return AST.Command(name="SYMBOL", args=args)

    @astnode
    def _parse_SYMBOL_AFTER(self) -> AST.Command:
        """ <SYMBOL AFTER> ::= SYMBOL AFTER <INT> """
        self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        return AST.Command(name="SYMBOL_AFTER", args=args)

    @astnode
    def _parse_TAB(self) -> AST.Command:
        """ <TAB> ::= TAB(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Command(name="TAB", args=args)

    @astnode
    def _parse_TAG(self) -> AST.Command:
        """ <TAG> ::= TAG [#<int_expression>] """
        self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.HASH):
            self._advance()
            args = [self._parse_int_expression()]
        return AST.Command(name="TAG", args=args)

    @astnode
    def _parse_TAGOFF(self) -> AST.Command:
        """ <TAGOFF> ::= TAGOFF [#<int_expression>] """
        self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.HASH):
            self._advance()
            args = [self._parse_int_expression()]
        return AST.Command(name="TAGOFF", args=args)

    @astnode
    def _parse_TAN(self) -> AST.Function:
        """ <TAN> ::= TAN(<num_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_real_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="TAN", etype=AST.ExpType.Real, args=args)

    @astnode
    def _parse_TEST(self) -> AST.Function:
        """ <TEST> ::= TEST(<int_expression>,<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_num_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        self._expect(TokenType.RPAREN)
        return AST.Function(name="TEST", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_TESTR(self) -> AST.Function:
        """ <TESTR> ::= TESTR(<int_expression>,<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_num_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        self._expect(TokenType.RPAREN)
        return AST.Function(name="TESTR", etype=AST.ExpType.Integer, args=args)

    def _parse_THEN(self):
        """ This is always an error """
        tk = self._advance()
        self._raise_error(2, tk, "unexpected THEN keyword")

    @astnode
    def _parse_TIME(self) -> AST.Function:
        """ <TIME> ::= TIME[(<int_expression>)] """
        self._advance()
        args: list[AST.Statement] = []
        etype = AST.ExpType.Real
        if self._match(TokenType.LPAREN):
            args = [self._parse_int_expression()]
            self._expect(TokenType.RPAREN)
            etype=AST.ExpType.Void
        return AST.Function(name="TIME", etype=etype, args=args)

    @astnode
    def _parse_TRON(self) -> AST.Command:
        """ <TRON> ::= TRON """
        self._advance()
        return AST.Command(name="TRON")
 
    @astnode   
    def _parse_TROFF(self) -> AST.Command:
        """ <TROFF> ::= TROFF """
        self._advance()
        return AST.Command(name="TROFF")

    @astnode
    def _parse_UBOUND(self) -> AST.Function:
        """ <UBOUND> ::= UBOUND(IDENT[,<int_expression>])"""
        self._advance()
        self._expect(TokenType.LPAREN)
        tk = self._expect(TokenType.IDENT)
        entry = self.symtable.find(tk.lexeme, SymType.Array, context=self.context)
        if entry is None:
            self._raise_error(2, tk, "undefined array")
        args: list[AST.Statement] = [AST.Variable(name=tk.lexeme, etype=entry.exptype)]
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        else:
            args.append(AST.Integer(value=1))
        self._expect(TokenType.RPAREN)
        return AST.Function(name="UBOUND", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_UGREATER(self) -> AST.Function:
        """ <UGREATER> ::= UGREATER(<int_expression>,<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_uint_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_uint_expression())
        self._expect(TokenType.RPAREN)
        return AST.Function(name="UGREATER", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_UNSIGNED(self) -> AST.Function:
        """ <UNSIGNED> ::= UNSIGNED(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_uint_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="UNSIGNED", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_UNT(self) -> AST.Function:
        """ <UNT> ::= UNT(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_uint_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="UNT", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_UPPERSS(self) -> AST.Function:
        """ <UPPERSS> ::= UPPER$(<str_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_str_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="UPPER$", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_USTRSS(self) -> AST.Function:
        """ <USTRSS> ::= USTR$(<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_uint_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="USTRSS", etype=AST.ExpType.String, args=args)

    @astnode
    def _parse_VAL(self) -> AST.Function:
        """ <VAL> ::= VAL(<str_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        args: list[AST.Statement] = [self._parse_str_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="VAL", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_VPOS(self) -> AST.Function:
        """ <VPOS> ::= VPOS(#<int_expression>) """
        self._advance()
        self._expect(TokenType.LPAREN)
        self._expect(TokenType.HASH)
        args: list[AST.Statement] = [self._parse_int_expression()]
        self._expect(TokenType.RPAREN)
        return AST.Function(name="VPOS", etype=AST.ExpType.Integer, args=args)

    @astnode
    def _parse_WAIT(self) -> AST.Command:
        """ <WAIT> ::= WAIT <int_expression>,<int_expression>[,<int_expression>]"""
        self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        args.append(self._parse_int_expression())
        if self._current_is(TokenType.COMMA):
            self._advance()
            args.append(self._parse_int_expression())
        return AST.Command(name="WAIT", args=args)

    @astnode
    def _parse_WEND(self) -> AST.BlockEnd:
        """ <WEND> ::= WEND """
        tk = self._advance()
        if len(self.codeblocks) == 0 or "WEND" not in self.codeblocks[-1].until_keywords:
            self._raise_error(30, tk)
        self.codeblocks.pop()
        return AST.BlockEnd(name="WEND")
  
    @astnode  
    def _parse_WHILE(self) -> AST.WhileLoop:
        """ <WHILE> ::= WHILE <int_expression> """
        tk = self._advance()
        cond = self._parse_int_expression()
        node = AST.WhileLoop(condition=cond)
        self.codeblocks.append(CodeBlock(
            type=BlockType.WHILE,
            until_keywords=("WEND",),
            start_node=node,
            tk=tk
        ))
        return node

    @astnode
    def _parse_WIDTH(self) -> AST.Command:
        """ <WIDTH> ::= WIDTH <int_expression> """
        self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        return AST.Command(name="WIDTH", args=args)

    @astnode
    def _parse_WINDOW(self) -> AST.Command:
        """ 
        <WINDOW> ::= WINDOW [#<int_expression>,]<wnd_rect>
        <wnd_rect> ::= <int_expression>,<int_expression>,<int_expression>,<int_expression>
        """
        self._advance()
        args: list[AST.Statement] = []
        if self._current_is(TokenType.HASH):
            self._advance()
            args = [self._parse_int_expression()]
            self._expect(TokenType.COMMA)
        for _ in range(4):
            self._match(TokenType.COMMA)
            args.append(self._parse_int_expression())
        return AST.Command(name="WINDOW", args=args)

    @astnode
    def _parse_WINDOW_SWAP(self) -> AST.Command:
        """ <WINDOWS_SWAP> ::= WINDOWS SWAP [#]<int_expression>,[#]<int_expression> """
        self._advance()
        self._match(TokenType.HASH)
        args: list[AST.Statement] = [self._parse_int_expression()]
        self._expect(TokenType.COMMA)
        self._match(TokenType.HASH)
        args.append(self._parse_int_expression())
        return AST.Command(name="WINDOW SWAP", args=args)
    
    @astnode
    def _parse_WRITE(self) -> AST.Write:
        """ <WRITE> ::= [#<int_expression>,]<expression>* """
        self._advance()
        stream: Optional[AST.Statement] = None
        if self._current_is(TokenType.HASH):
            self._advance()
            stream = self._parse_int_expression()
            self._expect(TokenType.COMMA)
        items: list[AST.Statement] = [self._parse_expression()]
        while self._current_in((TokenType.COMMA, TokenType.SEMICOLON)):
            self._advance()
            items.append(self._parse_expression())
        return AST.Write(stream=stream, items=items)

    @astnode
    def _parse_XPOS(self) -> AST.Function:
        """ <XPOS> ::= XPOS """
        self._advance()
        return AST.Function(name="XPOS", etype=AST.ExpType.Integer)
    
    @astnode
    def _parse_YPOS(self) -> AST.Function:
        """ <YPOS> ::= YPOS """
        self._advance()
        return AST.Function(name="YPOS", etype=AST.ExpType.Integer)

    @astnode
    def _parse_ZONE(self) -> AST.Command:
        """ <ZONE> ::= ZONE <int_expression> """
        self._advance()
        args: list[AST.Statement] = [self._parse_int_expression()]
        return AST.Command(name="ZONE", args=args)

    # ----------------- Expresions -----------------

    r"""
        Numeric operators precedence:
        EXP     ^
        SIGN    -
        MULT    *
        DIV     /  (Real)
        DIV     \  (Int)
        MOD     MOD
        ADD     +
        SUB     -

        Logic operators precedence:
        NOT
        AND
        OR
        XOR
    """

    def _cast_numtype(self, node: AST.Statement, etype: AST.ExpType) -> AST.Statement:
        """ 
        Issue a warning if we cast to a less representation range format:
        Real > Integer
        """
        if etype == AST.ExpType.Integer and node.etype != AST.ExpType.Integer:
            self._raise_warning(WL.MEDIUM, f"implicit cast of REAL to INT", node)
            nnode = AST.Function(name="CINT", etype=AST.ExpType.Integer, args=[node])
            nnode.set_origin(node.line, node.col)
            return nnode
        elif etype == AST.ExpType.Real and node.etype != AST.ExpType.Real:
            nnode = AST.Function(name="CREAL", etype=AST.ExpType.Real, args=[node])
            nnode.set_origin(node.line, node.col)
            return nnode
        return node

    def _cast_numtypes(self, left: AST.Statement, right: AST.Statement, etype: AST.ExpType, tk: Token) -> tuple[AST.Statement, AST.Statement]:
        dtype = AST.exptype_derive(left, right)
        if not AST.exptype_isvalid(dtype) or not AST.exptype_isnum(dtype):
            self._raise_error(13, tk)
        right = self._cast_numtype(right, etype)
        left  = self._cast_numtype(left, etype)
        return left, right

    def _parse_uint_expression(self) -> AST.Statement:
        """ <int_expression> ::= <expression>.type=INT """
        self.unsignedmode = True
        tk = self._current()
        stat = self._parse_num_expression()
        self.unsignedmode = False
        if stat.etype != AST.ExpType.Integer:
            self._raise_error(13, tk)
        return stat

    def _parse_int_expression(self, allowcast = True) -> AST.Statement:
        """ <int_expression> ::= <expression>.type=INT """
        tk = self._current()
        stat = self._parse_num_expression()
        if allowcast:
            return self._cast_numtype(stat, AST.ExpType.Integer)
        else:
            if stat.etype != AST.ExpType.Integer:
                self._raise_error(13, tk)
            return stat

    def _parse_real_expression(self, allowcast = True) -> AST.Statement:
        """ <real_expression> ::= <expression>.type=REAL """
        tk = self._current()
        stat = self._parse_num_expression()
        if allowcast:
            return self._cast_numtype(stat, AST.ExpType.Real)
        else:
            if stat.etype != AST.ExpType.Real:
                self._raise_error(13, tk)
            return stat

    def _parse_num_expression(self) -> AST.Statement:
        """ <int_expression> ::= <expression>.type=(INT|REAL) """
        tk = self._current()
        stat = self._parse_logic_xor()
        if not AST.exptype_isnum(stat.etype):
            self._raise_error(13, tk)
        return stat

    def _parse_str_expression(self) -> AST.Statement:
        """ <int_expression> ::= <expression>.type=STRING """
        tk = self._current()
        stat = self._parse_logic_xor()
        if not AST.exptype_isstr(stat.etype):
            self._raise_error(13, tk)
        return stat

    def _parse_expression(self) -> AST.Statement:
        """ <expression> ::= <logic_xor> """
        return self._parse_logic_xor()

    @astnode
    def _parse_logic_xor(self) -> AST.Statement:
        """ <logic_xor> ::= <logic_or> [XOR <logic_or>] """
        left = self._parse_logic_or()
        while self._current_is(TokenType.OP, "XOR"):
            op = self._advance()
            tk = self._current()
            right = self._parse_logic_or()
            # AND, OR and XOR produce integer results, they round real numbers before
            # performing the operation
            left, right = self._cast_numtypes(left, right, AST.ExpType.Integer, tk)
            left = AST.BinaryOp(op="XOR", left=left, right=right, etype=AST.ExpType.Integer)
            left.set_origin(op.line, op.col)
        return left

    @astnode
    def _parse_logic_or(self) -> AST.Statement:
        """ <logic_or> ::= <logic_and> [OR <logic_and>] """
        left = self._parse_logic_and()
        while self._current_is(TokenType.OP, "OR"):
            op = self._advance()
            tk = self._current()
            right = self._parse_logic_and()
            # AND, OR and XOR produce integer results, they round real numbers before
            # performing the operation
            left, right = self._cast_numtypes(left, right, AST.ExpType.Integer, tk)
            left = AST.BinaryOp(op="OR", left=left, right=right, etype=AST.ExpType.Integer)
            left.set_origin(op.line, op.col)
        return left

    @astnode
    def _parse_logic_and(self) -> AST.Statement:
        """ <logic_and> ::= <comparison> [AND <comparison>] """
        left = self._parse_comparison()
        while self._current_is(TokenType.OP, "AND"):
            op = self._advance()
            tk = self._current()
            right = self._parse_comparison()
            # AND, OR and XOR produce integer results, they round real numbers before
            # performing the operation
            left, right = self._cast_numtypes(left, right, AST.ExpType.Integer, tk)
            left = AST.BinaryOp(op="AND", left=left, right=right, etype=AST.ExpType.Integer)
            left.set_origin(op.line, op.col)
        return left

    @astnode
    def _parse_comparison(self) -> AST.Statement:
        """ <comparison> ::= <term> [(= | < | > | <= | =< | >= | => | <>) <term>] """
        left = self._parse_term()
        while self._current_is(TokenType.COMP):
            op = self._advance()
            right = self._parse_term()
            dtype = AST.exptype_derive(left, right)
            if not AST.exptype_isvalid(dtype):
                self._raise_error(13, op)
            # Logic OP always produces an integer result (0=FALSE, -1=TRUE)
            # but can operate with all types including String, for example, 
            # "STRING1" >= "STRING" which returns -1 (TRUE)
            if left.etype != AST.ExpType.String:
                left = self._cast_numtype(left, dtype)
            if right.etype != AST.ExpType.String:
                right = self._cast_numtype(right, dtype)
            opname = op.lexeme.replace('=>','>=').replace('=<','<=') # one operation one symbol
            left = AST.BinaryOp(op=opname, left=left, right=right, etype=AST.ExpType.Integer)
            left.set_origin(op.line, op.col)
        return left

    @astnode
    def _parse_term(self) -> AST.Statement:
        """ <term> ::= <mod> [( + | - ) <mod>] """
        left = self._parse_mod()
        while self._current_in((TokenType.OP,),  ('+', '-')):
            op = self._advance()
            tk = self._current()
            right = self._parse_mod()
            dtype = AST.exptype_derive(left, right)
            if not AST.exptype_isvalid(dtype):
                self._raise_error(13, op)
            if dtype == AST.ExpType.String:
                if op.lexeme == "-":
                    """ Strings only work with + (concatenate) """
                    self._raise_error(13, op)
            else:
                left, right = self._cast_numtypes(left, right, dtype, tk)
            left = AST.BinaryOp(op=op.lexeme, left=left, right=right, etype=dtype)
            left.set_origin(op.line, op.col)
        return left

    @astnode
    def _parse_mod(self) -> AST.Statement:
        """ <MOD> ::= <factor> [MOD <factor>] """
        left = self._parse_factor()
        while self._current_is(TokenType.OP, "MOD"):
            op = self._advance()
            tk = self._current()
            right = self._parse_factor()
            # MOD always produces an integer result and needs integer operators
            left, right = self._cast_numtypes(left, right, AST.ExpType.Integer, tk)
            left = AST.BinaryOp(op="MOD", left=left, right=right, etype=AST.ExpType.Integer)
            left.set_origin(op.line, op.col)
        return left

    @astnode
    def _parse_factor(self) -> AST.Statement:
        r""" <factor> ::= <pow> [( * | / | \ ) <pow>] """
        left = self._parse_pow()
        while self._current_in((TokenType.OP,), ('*', '/', '\\')):
            op = self._advance()
            tk = self._current()
            right = self._parse_pow()
            if op.lexeme == '\\':
                dtype = AST.ExpType.Integer
            else:
                dtype = AST.exptype_derive(left, right)
            left, right = self._cast_numtypes(left, right, dtype, tk)
            left = AST.BinaryOp(op=op.lexeme, left=left, right=right, etype=dtype)
            left.set_origin(op.line, op.col)
        return left

    @astnode
    def _parse_pow(self) -> AST.Statement:
        """ <pow> ::= <not> ^ <not> | <not> """
        left = self._parse_not()
        if self._current_is(TokenType.OP, lexeme='^'):
            # As per Locomotive BASIC documentation, the pow operation
            # is always Real
            op = self._advance()
            tk = self._current()
            right = self._parse_not()
            dtype = AST.ExpType.Real
            left, right = self._cast_numtypes(left, right, dtype, tk)
            left = AST.BinaryOp(op=op.lexeme, left=left, right=right, etype=dtype)
            left.set_origin(op.line, op.col)
        return left

    @astnode
    def _parse_not(self) -> AST.Statement:
        """ <not> ::= NOT <unary> | <unary> """
        # NOT only works with INT
        if self._current_is(TokenType.OP, lexeme='NOT'):
            self._advance()
            tk = self._current()
            right = self._parse_unary()
            if not AST.exptype_isnum(right.etype):
                self._raise_error(13, tk)
            right = self._cast_numtype(right, AST.ExpType.Integer)
            return AST.UnaryOp(op='NOT', operand=right, etype=right.etype)
        return self._parse_unary()

    @astnode
    def _parse_unary(self) -> AST.Statement:
        """ <unary> ::= -<primary> | <primary> """
        # '-' works with INT and REAL
        if self._current_is(TokenType.OP, lexeme='-'):
            self._advance()
            tk = self._current()
            # We may have the case of negative numbers that must be <primary>
            # instead of (OP(-),NUM)
            if tk.type == TokenType.INT:
                right = AST.Integer(value=tk.value) # type: ignore[arg-type]
                self._advance()
            else:
                right = self._parse_primary()
            if not AST.exptype_isnum(right.etype):
                self._raise_error(13, tk)
            if isinstance(right, AST.Integer):
                right.value = -right.value
                nbytes = self._int_to_bytes('', right.value)
                if nbytes == 0:
                    self._raise_error(6, tk)
                if nbytes > 2:
                    return AST.Real(value=right.value)
                return right
            elif isinstance(right, AST.Real):
                right.value = -right.value
                return right
            return AST.UnaryOp(op='-', operand=right, etype=right.etype)
        return self._parse_primary()

    def _int_to_bytes(self, lex: str, n: int) -> int:
        """
        Returns the bytes needed to represent the number n.
        Options are integers of 16 bits or integers of 32 bits.
        Hex/binary numbers are unsigned while regular numbers are
        signed.
        """
        if '&' not in lex and not self.unsignedmode:
            if n < -32768 or n > 32767:
                return 4
            return 2
        # unsigned or hex
        if n >= 0 and n < 65536:
            return 2
        return 0 # Overflow

    @astnode
    def _parse_primary(self) -> AST.Statement:
        """
        <primary> ::= POINTER | INT | REAL | STRING | (<expression>)
        <primary> ::= <ident> | <fun_keyword> | <fun_user>
        """
        tok = self._current()
        if tok.type == TokenType.AT:
            return self._parse_pointer()
        if tok.type == TokenType.INT:
            self._advance()
            value = cast(int, tok.value)
            nbytes = self._int_to_bytes(tok.lexeme, value)
            if nbytes == 0:
                self._raise_error(6, tok)
            if nbytes == 4:
                return AST.Real(value=value)
            return AST.Integer(value=value)
        if tok.type == TokenType.REAL:
            self._advance()
            return AST.Real(value=cast(float, tok.value))
        if tok.type == TokenType.STRING:
            self._advance()
            return AST.String(cast(str, tok.value))
        if tok.type == TokenType.IDENT:
            # FUNCTIONs must be declared before use
            entry = self.symtable.find("FUN" + tok.lexeme, SymType.Function)
            if self._current().lexeme[:2].upper() == "FN" or entry is not None:
                # this is a user function defined by DEF FN or FUNCTION
                return self._parse_user_fun()
            return self._parse_ident()
        if tok.type == TokenType.KEYWORD:   
            return self._parse_keyword()
        if self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expr
        self._raise_error(2, tok, f"unexpected symbol '{tok.lexeme}'")
        return AST.Nop()
    
    @astnode
    def _parse_ident(self) -> AST.Variable | AST.ArrayItem:
        """ <ident> ::= IDENT | IDENT(<int_expression>[,<int_expression>]) """
        # This is the first pass and some variables can be defined later
        # in the code so we cannot fail if an undefined variable arrives here
        # emiter will do
        tkvar = self._expect(TokenType.IDENT)
        etype = AST.exptype_fromname(tkvar.lexeme)
        if self._current_is(TokenType.LPAREN) or self._current_is(TokenType.LBRACK):
            opensym = self._current()
            # Array item
            self._advance()
            tk = self._current()
            indexes = [self._parse_expression()]
            if not AST.exptype_isint(indexes[0].etype):
                self._raise_error(13, tk, info="invalid index type")
            while self._current_is(TokenType.COMMA):
                self._advance()
                tk = self._current()
                indexes.append(self._parse_expression())
                if not AST.exptype_isint(indexes[-1].etype):
                    self._raise_error(13, tk)
            if opensym.type == TokenType.LPAREN: self._expect(TokenType.RPAREN)
            if opensym.type == TokenType.LBRACK: self._expect(TokenType.RBRACK)
            varname = tkvar.lexeme
            vartype = etype
            tk = self._current()
            if etype == AST.ExpType.String and tk.type == TokenType.IDENT and tk.lexeme[0] == '.':
                # This is a record
                tk = self._advance()
                varname = varname + tk.lexeme
                vartype = AST.exptype_fromname(varname)
                if self.symtable.find(tk.lexeme[1:], SymType.Record) is None:
                    self._raise_error(2, tk, "undefined record item")
            return AST.ArrayItem(name=varname, etype=vartype, args=indexes) # type: ignore[union-attr]
        # regular variable
        return AST.Variable(name=tkvar.lexeme, etype=etype)

    @astnode
    def _parse_user_fun(self) -> AST.Statement:
        """ <user_fun> ::= IDENT([<expression>[,<expression>]])"""
        tk = self._expect(TokenType.IDENT)
        fname = tk.lexeme
        # functions and procedures are always declared in the global context
        # Lets check first for DEF FN functions
        entry = self.symtable.find(ident=fname, stype=SymType.Function, context="")
        if entry is None:
            fname = "FUN" + tk.lexeme
            entry = self.symtable.find(ident=fname, stype=SymType.Function, context="")
        if entry is None:
            fname = "SUB" + tk.lexeme
            entry = self.symtable.find(ident=fname, stype=SymType.Procedure, context="")
        if entry is None:
            self._raise_error(18, tk)
        args: list[AST.Statement] = []
        self._expect(TokenType.LPAREN)
        if not self._current_is(TokenType.RPAREN):
            if self._next_is(TokenType.LBRACK):
                tk = self._advance()
                vartype = AST.exptype_fromname(tk.lexeme)
                self._expect(TokenType.LBRACK)
                self._expect(TokenType.RBRACK)
                args.append(AST.Array(name=tk.lexeme, etype=vartype, sizes=[], sizesexp=[], datasz=2))
            else:
                args.append(self._parse_expression())
            while self._current_is(TokenType.COMMA):
                self._advance()
                if self._next_is(TokenType.LBRACK):
                    tk = self._advance()
                    vartype = AST.exptype_fromname(tk.lexeme)
                    self._expect(TokenType.LBRACK)
                    self._expect(TokenType.RBRACK)
                    args.append(AST.Array(name=tk.lexeme, etype=vartype, sizes=[], sizesexp=[], datasz=2))
                else:
                    args.append(self._parse_expression()) 
        self._expect(TokenType.RPAREN)
        if entry.nargs != len(args): # type: ignore[union-attr]
            self._raise_error(2, tk, "wrong number of arguments")
        # lets check param types
        for i in range(len(args)):
            if isinstance(entry.args[i], AST.Array) and not isinstance(args[i], AST.Array): # type: ignore [union-attr]
                self._raise_error(13, tk)
            if args[i].etype != entry.argtypes[i]:  # type: ignore [union-attr]
                self._raise_error(13, tk)
        if entry: entry.calls += 1
        return AST.UserFun(name=fname, etype=entry.exptype, args=args) # type: ignore[union-attr]

    @astnode
    def _parse_pointer(self) -> AST.Pointer:
        """ <pointer> ::= @<ident> | @LABEL(IDENT) | @DATA """
        self._advance()
        var: AST.Variable | AST.ArrayItem | AST.Label | AST.String
        if self._current_is(TokenType.KEYWORD, lexeme="LABEL"):
            tk = self._advance()
            self._expect(TokenType.LPAREN)
            if self._current_is(TokenType.IDENT):
                tk = self._advance()
                var = AST.Label(value=tk.lexeme)
            elif self._current_is(TokenType.STRING):
                tk = self._advance()
                var = AST.String(value=cast(str, tk.value))
            else:
                self._raise_error(2, tk)
            self._expect(TokenType.RPAREN)
            var.set_origin(tk.line, tk.col)
        elif self._current_is(TokenType.KEYWORD, lexeme="DATA"):
            tk = self._advance()
            var = AST.Label(value="DATA")
            var.set_origin(tk.line, tk.col)
        else:
            var = self._parse_ident()
            if isinstance(var, AST.Variable):
                # Let's contabilize this access as a write so the variable
                # is not considered a constant
                entry = self.symtable.find(var.name, SymType.Variable, self.context)
                if entry is None:
                    self.symtable.add(
                        ident=var.name,
                        info=SymEntry(
                            SymType.Variable,
                            exptype=var.etype,
                            locals=SymTable(),
                            datasz=AST.exptype_memsize(var.etype)
                        ),
                        context=self.context
                    )
                else:
                    entry.writes += 1
        return AST.Pointer(var=var)

    @astnode
    def _parse_range(self) -> AST.Statement:
        """ <range> ::= CHAR[-CHAR] | INT[-INT]"""
        if self._current_is(TokenType.IDENT):
            tk = self._expect(TokenType.IDENT)
            low = tk.lexeme.upper()
            high = low
            if self._current_is(TokenType.OP, lexeme="-"):
                self._advance()
                high = self._expect(TokenType.IDENT).lexeme.upper()
            if len(low) > 1 or len(high) > 1:
                self._raise_error(2, tk, "unsupported range format")
            etype = AST.ExpType.String
        else:
            tk = self._expect(TokenType.INT)
            high = low = tk.value # type: ignore[assignment]
            if self._current_is(TokenType.OP, lexeme="-"):
                self._advance()
                high = self._expect(TokenType.INT).value  # type: ignore[assignment]
            etype = AST.ExpType.Integer
        if low > high:
            self._raise_error(2, tk, "unsupported range format")
        return AST.Range(etype=etype, low=low, high=high)

    # ----------------- AST Generation -----------------
    
    def _parse_assignment(self) -> AST.Assignment | AST.Statement:
        """ <assignment> ::= <ident> = <expression> | <MIDSS> = <str_expression> """
        if self._current_is(TokenType.KEYWORD, lexeme="MID$"):
            # the only exception where a Command can be used on the left of an assignment
            midss = self._parse_MIDSS()
            self._expect(TokenType.COMP, lex="=")
            args = [self._parse_str_expression()] + midss.args
            # source substring, target string, insert point, [ignored]
            return AST.Command(name="REPLACE$", args=args)
        # The asignement is the way to declare variables so
        # we do not check in the sym table if left variables exist
        # BUT routine parameters is an exception
        tk = self._current()
        target = self._parse_ident()
        self._expect(TokenType.COMP, "=")
        source = self._parse_expression()
        # assignament type is always the one from the target variable
        # an assignement is the way to declare new variables except in 
        # the case of Arrays, which must be declared with DIM or parameters
        dtype = AST.exptype_derive(target, source)
        if not AST.exptype_isvalid(dtype):
            self._raise_error(13, tk)
        if dtype != AST.ExpType.String:
            target, source = self._cast_numtypes(target, source, target.etype, tk)
        if isinstance(target, AST.Variable):
            # Simple variables are declared through assinements so we
            # have to add them to the symtable now but let's check that it
            # is not a constant, a parameter or a record access
            self._check_noconst(target.name, tk)
            entry = self.symtable.find(target.name, SymType.Param, self.context)
            if entry is None:
                added = self.symtable.add(
                    ident=target.name,
                    info=SymEntry(
                        SymType.Variable,
                        exptype=target.etype,
                        locals=SymTable(),
                        datasz=AST.exptype_memsize(target.etype)
                    ),
                    context=self.context
                )
                if not added:
                    self._raise_error(2, tk)
        return AST.Assignment(target=target, source=source, etype=target.etype)

    def _parse_RSX(self) -> AST.RSX:
        name = self._advance().lexeme[1:]   # remove '|' symbol
        args: list[AST.Statement] = []
        if  self._current_is(TokenType.COMMA):
            self._advance()
            args = [self._parse_expression()]
            while self._current_is(TokenType.COMMA):
                self._advance()
                args.append(self._parse_expression())
        # names will be used in capitals and 16 chars max
        name = name.upper()[0:16]
        self.symtable.add(name, SymEntry(
            SymType.RSX,
            AST.ExpType.Void,
            SymTable()
        ), "")
        return AST.RSX(command=name, args=args)

    def _parse_keyword(self) -> AST.Statement:
        """ <keyword> ::= <FUNCTION> | <COMMAND> """
        tk = self._current()
        keyword = tk.lexeme
        funcname = "_parse_" + keyword.replace('$','SS').replace(' ', '_')
        parse_keyword = getattr(self, funcname , None)
        if parse_keyword is None:
            self._raise_error(2, tk, f"unknown keyword {keyword}")
        return parse_keyword() # type: ignore[misc]

    @astnode
    def _parse_statement(self) -> AST.Statement:
        """ <statement> ::= <keyword> | COMMENT | RSX | <assignement> """
        tok = self._current()
        lex = tok.lexeme.upper()
        if tok.type == TokenType.KEYWORD:
            if lex == "MID$":
                # This is the only exception where a Command can be in the left of an asigment
                return self._parse_assignment()
            return self._parse_keyword()     
        elif tok.type == TokenType.COMMENT:
            return AST.Comment(text=self._advance().lexeme)
        elif tok.type == TokenType.RSX:
            return self._parse_RSX()
        elif tok.type == TokenType.IDENT and lex[:2] == "FN":
            # User call to a function defined with DEF FN
            return self._parse_user_fun()
        elif tok.type == TokenType.IDENT:
            # Assignment without LET
            return self._parse_assignment()
        self._raise_error(2, tok, f"Unknown statement '{tok.lexeme}'")
        return AST.Nop()

    def _parse_statement_list(self) -> list[AST.Statement]:
        """<statement_list> ::= <statements> [:<statement>]"""
        stmts = [self._parse_statement()]
        while self._current_in((TokenType.COLON, TokenType.COMMENT)):
            self._match(TokenType.COLON)
            # it's possible to end a line with just : and EOL
            if self._current_is(TokenType.EOL):
                break
            stmts.append(self._parse_statement())
        return stmts

    @astnode
    def _parse_line(self) -> AST.Line:
        """<line> ::= LINE_NUMBER <statement_list> EOL"""
        tk = self._expect(TokenType.LINE_NUMBER)
        line_number = cast(int, tk.value)
        inserted = self.symtable.add(
            ident=str(line_number),
            info=SymEntry(symtype=SymType.Label, exptype=AST.ExpType.Integer, locals=SymTable()),
            context=""
        )
        if not inserted:
            self._raise_error(34, tk)
        self.current_linelabel = str(line_number)
        statements = self._parse_statement_list()
        self._expect(TokenType.EOL)
        return AST.Line(number=line_number, statements=statements)

    def parse_program(self) -> tuple[AST.Program, SymTable]:
        """ <program> ::= <line><program> | EOL<program> | EOF"""
        print("Checking syntax...")
        lines = []
        while not self._current_is(TokenType.EOF):
            if self._current_is(TokenType.EOL):
                self._advance()
                continue
            lines.append(self._parse_line())
        if len(self.codeblocks) > 0:
            cblock = self.codeblocks[-1]
            if "NEXT" in cblock.until_keywords:
                self._raise_error(26, info="EOF reached", tk=cblock.tk)
            elif "WEND" in cblock.until_keywords:
                self._raise_error(29, info="EOF reached", tk=cblock.tk)
            elif "END IF" in cblock.until_keywords:
                self._raise_error(35, info="EOF reached", tk=cblock.tk)
            elif "END SUB" in cblock.until_keywords:
                self._raise_error(42, info="EOF reached", tk=cblock.tk)
            elif "END FUNCTION" in cblock.until_keywords:
                self._raise_error(44, info="EOF reached", tk=cblock.tk)
            elif "END SELECT" in cblock.until_keywords:
                self._raise_error(45, info="EOF reached", tk=cblock.tk)
            else:
                self._raise_error(24, self.tokens[-1])
        program = AST.Program(lines=lines)
        program.hasevents = self.hasevents
        return program, self.symtable

