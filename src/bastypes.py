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
    LEFTS = 173
    LEN = 174
    LET = 175
    LINE_INPUT = 176
    LIST = 177
    LOAD = 178
    LOCATE = 179
    LOG = 180
    LOG10 = 181
    LOWERS = 182
    MASK = 183
    MAX = 184
    MEMORY = 185
    MERGE = 186
    MIDS = 187
    MIN = 188
    MODE = 189
    MOVE = 190
    MOVER = 191
    NEW = 192
    NEXT = 193
    NOT = 194
    ON_GOSUB = 195
    ON_GOTO = 196
    ON_BREAL_CONT = 197
    ON_BREAK_GOSUB = 198
    ON_BREAK_STOP = 199
    ON_ERROR_GOTO  = 200
    ON_SQ_GOSUB = 201
    OPENIN = 202
    OPENOUT = 203
    OR = 204
    ORIGIN = 205
    OUT = 206
    PAPER = 207
    PEEK = 208
    PEN = 209
    PI = 210
    PLOT = 211
    PLOTR = 212
    POKE = 213
    POS = 214
    PRINT = 215
    PRINT_SPC = 216
    PRINT_TAB = 217
    PRINT_USING = 218
    RAD = 219
    RANDOMIZE = 220
    READ = 221
    RELEASE = 222
    REM = 223
    REMAIN = 224
    RENUM = 225
    RESTORE = 226
    RESUME = 227
    RETURN = 228
    RIGHTS = 229
    RND = 230
    ROUND = 231
    RUN = 232
    SAVE = 233
    SGN = 234
    SIN = 235
    SOUND = 236
    SPACES = 237
    SPEED_INK = 238
    SPEED_KEY = 239
    SPEED_WRITE = 240
    SQ = 241
    SQR = 242
    STOP = 243
    STRS = 244
    STRINGS = 245
    SYMBOL = 246
    SYMBOL_AFTER = 247
    TAG = 248
    TAGOFF = 249
    TAN = 250
    TEST = 251
    TESTR = 252
    TIME = 253
    TRON = 254
    TROFF = 255
    UNT = 256
    UPPERS = 257
    VAL = 258
    VPOS = 259
    WAIT = 260
    WEND = 261
    WHILE = 262
    WIDTH = 263
    WINDOW = 264
    WINDOW_SWAP = 265
    WRITE = 266
    XOR = 267
    XPOS = 268
    YPOS = 269
    ZONE = 270

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
    def __init__(self, tktext, tktype):
        self.text = tktext   # The token's actual text. Used for identifiers, strings, and numbers.
        self.type = tktype   # The TokenType that this token is classified as.
 
    @staticmethod
    def get_keyword(tktext):
        for tktype in TokenType:
            # Relies on all keyword enum values being 1XX.
            if tktype.name == tktext and tktype.value > TokenType.ABS.value and tktype.value < TokenType.TK_NUM_OPS.value:
                return tktype
        return None

    def is_keyword(self):
        # Check if the token is in the list of keywords.
        return Token.get_keyword(self.text) != None

    def is_num_op(self):
        # Check if the token is in the list of numerical operations.
        return self.text != '' and (self.text in "+-*/\\" or self.text == 'MOD')

    def is_logic_op(self):
        # Check if the token is in the list of logical operations.
        return self.text in ['=','<>','>','<','>=','<=']

class Symbol:
    """
    symbols can be variables or labels. Variables point to values
    of type INT, REAL or STR.
    """

    SYMVAR   = 0
    SYMLAB   = 1

    VINT    = 0
    VSTR    = 1
    VREAL   = 2
    VNONE   = 3

    def __init__(self, sname, stype):
        self.symbol = sname
        self.symtype = stype
        self.value = None
        self.valtype = Symbol.VNONE
        self.extrainfo = None
        self.puts = 0
        self.gets = 0
    
    def set_value(self, value, valtype):
        self.value = value
        self.valtype = valtype
    
    def is_var(self):
        return self.type == Symbol.SYMVAR
    
    def inc_reads(self):
        """ To control the number of times the symbol value is used """
        self.gets = self.gets + 1

    def inc_writes(self):
        """ To control the number of times the symbol value is changed """
        self.puts = self.puts + 1

class SymbolTable:
    """ table of symbols found during the compilation process """

    def __init__(self):
        self.symbols = {}
    
    def add(self, sname, stype):
        symbol = Symbol(sname, stype)
        self.symbols[sname] = symbol
        return symbol

    def search(self, sname):
        if sname in self.symbols.keys():
            return self.symbols[sname]
        return None
