"""
Types shared by different components of the BASC compiler

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

import enum
from typing import Optional, List, Tuple, Dict, Union, Type

class ErrorCode:
    NEXT    = "Unexpected NEXT"
    RESUME  = "Unexpected RESUME"
    RETURN  = "Unexpected RETURN"
    WEND    = "Unexpected WEND"
    THEN    = "Unexpected THEN"
    NONEXT  = "NEXT missing"
    NOWEND  = "WEND missing"
    NORESUME= "RESUME missing"
    NOLINE  = "Line does not exist"
    NOIDENT = "Undeclared indentifier"
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
    NOKEYW  = "Keyword not implemented"
    LEXISTS = "Label already defined"
    
class TokenType(enum.Enum):
    """
    Enum for all supported tokens.
    """
    TK_VAR_TYPES = 0
    INTEGER = 1
    STRING = 2
    IDENT = 3
    CHANNEL = 4
    REAL = 5
    AT = 6

    # keywords
    TK_KEYWORDS = 99
    ABS	= 100
    AFTER = 101
    AND = 102
    ASC = 103
    ATN = 104
    AUTO = 105
    BINS = 106
    BORDER = 107
    CALL = 108
    CAT = 109
    CHAIN = 110
    CHAIN_MERGE = 111
    CHRS = 112
    CINT = 113
    CLEAR = 114
    CLEAR_INPUT = 115
    CLG = 116
    CLOSEIN = 117
    CLOSEOUT = 118
    CLS = 119
    CONT = 120
    COPYCHRS = 121
    COS = 122
    CREAL = 123
    CURSOR = 124
    DATA = 125
    DECS = 126
    DEF_FN = 127
    DEFINT = 128
    DEFSTR = 129
    DEFREAL = 130
    DEG = 131
    DELETE = 132
    DERR = 133
    DI = 134
    DIM = 135
    DRAW = 136
    DRAWR = 137
    EDIT = 138
    EI = 139
    ELSE = 140
    END = 141
    ENT = 142
    ENV = 143
    EOF = 144
    ERASE = 145
    ERL = 146
    ERR = 147
    ERROR = 148
    EVERY = 149
    EXP = 150
    FILL = 151
    FIX = 152
    FOR = 153
    FRAME = 154
    FRE = 155
    GOSUB = 156
    GOTO = 157
    GRAPHICS_PAPER = 158
    GRAPHICS_PEN = 159
    HEXS = 160
    HIMEM = 161
    IF = 162
    INK = 163
    INKEY = 164
    INKEYS = 165
    INP = 166
    INPUT = 167
    INSTR = 168
    INT = 169
    JOY = 170
    KEY = 171
    KEY_DEF = 172
    LABEL = 173
    LEFTS = 174
    LEN = 175
    LET = 176
    LINE_INPUT = 177
    LIST = 178
    LOAD = 179
    LOCATE = 180
    LOG = 181
    LOG10 = 182
    LOWERS = 183
    MASK = 184
    MAX = 185
    MEMORY = 186
    MERGE = 187
    MIDS = 188
    MIN = 189
    MODE = 190
    MOVE = 191
    MOVER = 192
    NEW = 193
    NEXT = 194
    NOT = 195
    ON_GOSUB = 196
    ON_GOTO = 197
    ON_BREAL_CONT = 198
    ON_BREAK_GOSUB = 199
    ON_BREAK_STOP = 200
    ON_ERROR_GOTO  = 201
    ON_SQ_GOSUB = 202
    OPENIN = 203
    OPENOUT = 204
    OR = 205
    ORIGIN = 206
    OUT = 207
    PAPER = 208
    PEEK = 209
    PEN = 210
    PI = 211
    PLOT = 212
    PLOTR = 213
    POKE = 214
    POS = 215
    PRINT = 216
    PRINT_SPC = 217
    PRINT_TAB = 218
    PRINT_USING = 219
    RAD = 220
    RANDOMIZE = 221
    READ = 222
    RELEASE = 223
    REM = 224
    REMAIN = 225
    RENUM = 226
    RESTORE = 227
    RESUME = 228
    RETURN = 229
    RIGHTS = 230
    RND = 231
    ROUND = 232
    RUN = 233
    SAVE = 234
    SGN = 235
    SIN = 236
    SOUND = 237
    SPACES = 238
    SPEED_INK = 239
    SPEED_KEY = 240
    SPEED_WRITE = 241
    SQ = 242
    SQR = 243
    STOP = 244
    STRS = 245
    STRINGS = 246
    SYMBOL = 247
    SYMBOL_AFTER = 248
    TAG = 249
    TAGOFF = 250
    TAN = 251
    TEST = 252
    TESTR = 253
    THEN = 254
    TIME = 255
    TRON = 256
    TROFF = 257
    UNT = 258
    UPPERS = 259
    VAL = 260
    VPOS = 261
    WAIT = 262
    WEND = 263
    WHILE = 264
    WIDTH = 265
    WINDOW = 266
    WINDOW_SWAP = 267
    WRITE = 268
    XOR = 269
    XPOS = 270
    YPOS = 271
    ZONE = 272
    SPC  = 273
    TAB  = 274

    # Numeric expression tokens
    TK_NUM_OPS = 500
    LPAR = 501
    RPAR = 502    
    PLUS = 503
    MINUS = 504
    ASTERISK = 505
    SLASH = 506
    LSLASH = 507
    MOD = 508

    # logic operators than can be used in numeric expressions
    TK_LOGIC_OPS=550
    LT = 551
    GT = 552

    # Extra logic expression tokens
    TK_EXTRA_LOGIC_OPS=600
    EQ = 601
    NOTEQ = 602
    LTEQ = 603
    GTEQ = 604
    NEG = 605

    # Separators
    TK_SEPARATORS = 700
    COLON = 701
    SEMICOLON = 702
    COMMA = 703
    CODE_EOF = 704
    NEWLINE = 705

class Token:   
    """
    This class helps to store the original text and the type of a token.
    """
    def __init__(self, tktext: str, tktype: TokenType, srcline: int) -> None:
        self.text = tktext      # The token's actual text. Used for identifiers, strings, and numbers.
        self.type = tktype      # The TokenType that this token is classified as.
        self.srcline = srcline  # line number of the source code where this token belongs to.
        self.srcpos = 0         # optional, position in source code where it starts

    @staticmethod
    def get_keyword(tktext: str) -> Optional[TokenType]:
        if tktext.endswith('$'): tktext = tktext[:-1] + 'S'
        for tktype in TokenType:
            # Relies on all keyword enum values being between [ABS : TK_NUM_OPS]
            if tktype.name == tktext and tktype.value > TokenType.ABS.value and tktype.value < TokenType.TK_NUM_OPS.value:
                return tktype
        return None

    def is_keyword(self) -> bool:
        # Check if the token is in the list of keywords.
        return Token.get_keyword(self.text) != None

    def is_num_op(self) -> bool:
        # Check if the token is in the list of numerical operations.
        return self.text in ['+','-','*','/','\\','MOD']

    def is_logic_op(self) -> bool:
        # Check if the token is in the list of logical operations.
        return self.text in ['=','<>','>','<','>=','<=']

    def is_ident(self) -> bool:
        # Check if the token is an identifier
        return self.type == TokenType.IDENT
    
    def is_str(self) -> bool:
        # Check if the token is a string literal
        return self.type == TokenType.STRING
    
    def is_int(self) -> bool:
        # Check if the token is an integer literal
        return self.type == TokenType.INTEGER
    
    def is_real(self) -> bool:
        # Check if the token is a real literal
        return self.type == TokenType.REAL

    def __str__(self) -> str:
        return f"({self.text},{self.type},{self.srcline})"

class BASTypes(enum.Enum):
    INT     = 0
    REAL    = 1
    STR     = 2
    VOID    = 3
    NONE    = 4

class Expression:

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.expr: List[Tuple[Token, BASTypes]] = []
        self.restype: BASTypes = BASTypes.NONE  # Final result type

    def is_empty(self) -> bool:
        return len(self.expr) == 0

    def is_complex(self) -> bool:
        return len(self.expr) > 1

    def is_simple(self) -> bool:
        return len(self.expr) == 1

    def is_int_result(self) -> bool:
        return self.restype.value == BASTypes.INT.value

    def is_real_result(self) -> bool:
        return self.restype.value == BASTypes.REAL.value

    def is_str_result(self) -> bool:
        return self.restype.value == BASTypes.STR.value

    def is_void_result(self) -> bool:
        return self.restype.value == BASTypes.VOID.value
    
    def is_none_result(self) -> bool:
        return self.restype.value == BASTypes.NONE.value
    
    def is_compatible(self, bastype: BASTypes) -> bool:
        return self.restype == bastype

    def pushval(self, symbol: Token, bastype: BASTypes) -> None:
        if self.restype == BASTypes.NONE:
            self.restype = bastype
        self.expr.append((symbol, bastype))
    
    def pushop(self, symbol: Token) -> None:
        # operators are added without type because checktypes will do it
        # after the expression is parsed to calculate it correctly
        self.expr.append((symbol, BASTypes.NONE))

    def check_types(self) -> bool:
        typestack: List[BASTypes] = []
        for i, (token,bastype) in enumerate(self.expr):
            if token.type not in [TokenType.INTEGER, TokenType.REAL, TokenType.STRING, TokenType.IDENT]:
                top1 = typestack.pop()
                if token.text in ['-','*','/','\\','%']:
                    # operants over numeric types (integers or reals)
                    top2 = typestack.pop()
                    if top1 != top2 or top1 == BASTypes.STR:
                        return False
                    self.expr[i] = (token, top1)
                    bastype = top1
                elif token.text == '+':
                    # supports strings too as it means concat
                    top2 = typestack.pop()
                    if top1 != top2:
                        return False
                    self.expr[i] = (token, top1)
                    bastype = top1
                elif token.text in ['=','>','<','<>','>=','<=','AND','OR']:
                    # logic operations support strings, reals and integers but
                    # the result is always integer (boolean) so we store the
                    # type of the operands but stack INT for the test purposes
                    top2 = typestack.pop()
                    if top1 != top2:
                        return False
                    self.expr[i] = (token, top1)
                    bastype = BASTypes.INT
                elif token.text == 'XOR':
                    # this works only with integers
                    top2 = typestack.pop()
                    if top1 != top2 or top1 != BASTypes.INT:
                        return False
                    self.expr[i] = (token, BASTypes.INT)
                    bastype = BASTypes.INT
                else:
                    # This is one factor operation like NEG or AT
                    # all of them produce INT results right now
                    bastype = BASTypes.INT
                    if token.type != TokenType.AT and top1 != BASTypes.INT:
                        return False
                    self.expr[i] = (token, BASTypes.INT)
                    bastype = BASTypes.INT

            typestack.append(bastype)

        if len(typestack) == 1:
            self.restype = typestack[0]
            return True
        return False

    def __str__(self) -> str:
        text = "["
        for (token, type) in self.expr:
            text = text + f"({token.text},{type})"
        text = text + "]"
        return text
    
    @staticmethod
    def int(literal: str):
        expr = Expression()
        token = Token(literal, TokenType.INTEGER, -1)
        expr.pushval(token, BASTypes.INT)
        return expr
    
    @staticmethod
    def string(literal: str):
        expr = Expression()
        token = Token(literal, TokenType.STRING, -1)
        expr.pushval(token, BASTypes.STR)
        return expr

    @staticmethod
    def real(literal: str):
        expr = Expression()
        token = Token(literal, TokenType.REAL, -1)
        expr.pushval(token, BASTypes.REAL)
        return expr

class SymTypes(enum.Enum):
    SYMVAR   = 0
    SYMLAB   = 1

class Symbol:
    """
    symbols can be variables or labels. Variables point to values
    of type INT, REAL or STR.
    """

    def __init__(self, sname: str, stype: SymTypes) -> None:
        self.symbol = sname
        self.symtype = stype
        self.value: List[Tuple[Token,BASTypes]] = []
        self.valtype = BASTypes.NONE
        self.temporal = False
        self.puts = 0
        self.gets = 0
    
    def set_value(self, expr: Expression):
        self.value = expr.expr
        self.valtype = expr.restype
        self.inc_writes()
    
    def is_ident(self) -> bool:
        return self.symtype == SymTypes.SYMVAR
    
    def is_label(self) -> bool:
        return self.symtype == SymTypes.SYMLAB
    
    def is_constant(self) -> bool:
        return self.puts == 1 and self.is_ident() and len(self.value) == 1

    def is_tmp(self) -> bool:
        return self.symbol.startswith('var_tmp')

    def inc_reads(self):
        """ To control the number of times the symbol value is used """
        self.gets = self.gets + 1

    def inc_writes(self):
        """ To control the number of times the symbol value is changed """
        self.puts = self.puts + 1

    def is_compatible(self, bastype: BASTypes) -> bool:
        if bastype == BASTypes.STR:
            # string type must be declared explicity with $ at the end so
            # NONE is not valid in this case
            return self.valtype == BASTypes.STR
        return self.valtype == BASTypes.NONE or self.valtype == bastype

    def print(self) -> None:
        print(self.symbol + ' -', self.symtype, ':', self.valtype, self.value)
        print("\treads:", self.gets, "writes:", self.puts)

    def __str__(self) -> str:
        return str(self.symbol) + ' - ' + str(self.symtype) + ': ' + str(self.valtype) + ' ' + str(self.value)

class SymbolTable:
    """ table of symbols found during the compilation process """

    def __init__(self) -> None:
        self.symbols: Dict[str, Symbol] = {}
    
    def add(self, sname: str, stype: SymTypes) -> Symbol:
        symbol = Symbol(sname, stype)
        self.symbols[sname] = symbol
        return symbol

    def get(self, sname: str) -> Symbol:
        return self.symbols[sname]

    def search(self, sname: str) -> Optional[Symbol]:
        if sname in self.symbols.keys():
            return self.symbols[sname]
        return None

    def getsymbols(self) -> List[str]:
        return list(self.symbols.keys())

class CodeBlockType(enum.Enum):
    FOR     = 1
    WHILE   = 2
    IF      = 3
    PRINT   = 4

ForBlockInfo = Tuple[Symbol, Symbol, Optional[Expression]] # (variable, limit, step)

class CodeBlock:
    """
    Each entry stores the relevant information about a block of
    code (starting point, end point, type, etc.) like the ones
    created by:
    FOR <expression> <codeblock> NEXT
    WHILE <expression> <codeblock> WEND
    IF <condition> THEN <codeblock> [ELSE <codeblock>] IFEND
    """
    def __init__(self, type: CodeBlockType, startlabel: Optional[Symbol], endlabel: Optional[Symbol]) -> None:
        self.type = type
        self.startlabel = startlabel
        self.endlabel = endlabel
        self.blockinfo: Optional[ForBlockInfo] = None

    def set_forinfo(self, info: ForBlockInfo) -> None:
        """ variant value,  end-condition value, optional step expression"""
        self.blockinfo = info

