"""
Lexycal scanner for Amstrad locomotive BASIC code.

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
import enum

class BASLexError(Exception):
    """
    Raised when procesing a file and its format is not the expected one.
    """
    def __init__(self, message, file = "", line = -1):
        self.message = message
        self.line = line
        self.file = file

    def __str__(self):
        if self.line != -1:
            return "[baslex] Error: %s\n\tfile %s line %d" % (self.message, self.file, self.line)
        else:
            return "[baslex] Error: %s" % self.message
    
class BASLexer:
    """
    Lexer object keeps track of current position in the source code and produces each token.
    """
    def __init__(self, code):
        self.orgcode = code
        # pass code to lex as a string. Append a newline to simplify lexing/parsing the last token/statement.
        self.source = ''.join(l for _, _, l in code) + '\n'
        self.cur_char = ''   # Current character in the string.
        self.cur_pos = -1    # Current position in the string.
        self.cur_line = 0
        self.last_token = None
        self.next_char()

    def get_currentcode(self):
        if self.cur_line >= len(self.orgcode):
            return (self.orgcode[0][0], -1, "EOF")
        return self.orgcode[self.cur_line]

    def next_char(self):
        """Process the next character."""
        self.cur_pos += 1
        if self.cur_pos >= len(self.source):
            self.cur_char = '\0'  # EOF
        else:
            self.cur_char = self.source[self.cur_pos]

    def peek(self):
        """Return the lookahead character."""
        if self.cur_pos + 1 >= len(self.source):
            return '\0'
        return self.source[self.cur_pos + 1]

    def abort(self, message):
        """raise error message adding file name and original file number"""
        file, linenum, _ = self.orgcode[self.cur_line]
        raise BASLexError(message, file, linenum)

    def _get_operator(self):
        if self.cur_char == '+':
            return Token(self.cur_char, TokenType.PLUS)
        elif self.cur_char == '-':
            return Token(self.cur_char, TokenType.MINUS)
        elif self.cur_char == '*':
            return Token(self.cur_char, TokenType.ASTERISK)
        elif self.cur_char == '/':
            return Token(self.cur_char, TokenType.SLASH)
        elif self.cur_char == '(':
            return Token(self.cur_char, TokenType.LPAR)
        elif self.cur_char == ')':
            return Token(self.cur_char, TokenType.RPAR)
        elif self.cur_char == '=':
            return Token(self.cur_char, TokenType.EQ)
        elif self.cur_char == '>':
            # Check whether this is token is > or >=
            if self.peek() == '=':
                last_char = self.cur_char
                self.next_char()
                return Token(last_char + self.cur_char, TokenType.GTEQ)
            else:
                return Token(self.cur_char, TokenType.GT)
        elif self.cur_char == '<':
            # Check whether this is token is < or <=
            last_char = self.cur_char
            if self.peek() == '=':
                self.next_char()
                return Token(last_char + self.cur_char, TokenType.LTEQ)
            elif self.peek() == '>':
                self.next_char()
                return Token(last_char + self.cur_char, TokenType.NOTEQ)
            else:
                return Token(self.cur_char, TokenType.LT)
        return None

    def _get_quotedtext(self):
         # Get characters between quotations.
        self.next_char()
        start_pos = self.cur_pos
        while self.cur_char != '\"':
            self.next_char()
            if self.cur_char == '\n':
                self.abort("strings must be enclosed in quotation marks")
        text = self.source[start_pos : self.cur_pos]
        return Token(text, TokenType.STRING)

    def _get_number(self):
         # Get all consecutive digits and decimal if there is one.
        start_pos = self.cur_pos
        while self.peek().isdigit():
            self.next_char()
        if self.peek() == '.': # Decimal!
            self.next_char()
            # Must have at least one digit after decimal.
            if not self.peek().isdigit(): 
                self.abort("number contains illegal characters")
            while self.peek().isdigit():
                self.nextChar()
        text = self.source[start_pos : self.cur_pos + 1]
        return Token(text, TokenType.NUMBER)

    def _get_identifier_text(self):
        start_pos = self.cur_pos
        while self.peek().isalnum():
            self.next_char()
        return self.source[start_pos : self.cur_pos + 1].upper()

    def get_token(self):
        self.lstrip()
        self.skip_comment()
        token = None

        # Check the first character of this token to see if we can decide what it is.
        if self.cur_char == '\n':
            token = Token('', TokenType.NEWLINE)

        elif self.cur_char == '\0':
            token = Token('', TokenType.CODE_EOF)

        elif self.cur_char == ':':
            token = Token(':', TokenType.COLON)

        elif self.cur_char == ';':
            token = Token(';', TokenType.SEMICOLON)

        elif self.cur_char == ',':
            token = Token(',', TokenType.COMMA)

        elif self.cur_char in "+-*/=><()":
            token = self._get_operator()
        
        elif self.cur_char == '\"':
            token = self._get_quotedtext()
        
        elif self.cur_char == '#':
            token = Token('#', TokenType.CHANNEL)

        elif self.cur_char.isdigit():
            token = self._get_number()
           
        elif self.cur_char.isalpha():
            # can be an identifier or keyword
            text = self._get_identifier_text()
            keyword = Token.get_keyword(text)
            if keyword != None:
                token = Token(text, keyword)
            else:
                # Identifier or label
                token = Token(text, TokenType.IDENT)   
        else:
            self.abort("unexpected character found '" + self.cur_char + "'")

        self.next_char()
        if self.last_token != None and self.last_token.type == TokenType.NEWLINE:
             # we are processing a new line of the src code
             self.cur_line = self.cur_line + 1
        self.last_token = token
        return token

    def lstrip(self):
        """Skip whitespace except newlines, which we will use to indicate the end of a statement."""
        while self.cur_char == ' ' or self.cur_char == '\t' or self.cur_char == '\r':
            self.next_char()

    def skip_comment(self):
        if self.cur_char == "'":
            while self.cur_char != '\n':
                self.next_char()

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
            if tktype.name == tktext and tktype.value > TokenType.ABS.value and tktype.value < TokenType.END_KEYWORDS.value:
                return tktype
        return None

    def is_keyword(self):
        # Check if the token is in the list of keywords.
        return Token.get_keyword(self.text) != None

    def is_operation(self):
        # Check if the token is in the list of operations.
        return self.text != '' and self.text in "+-*/"

class TokenType(enum.Enum):
    """
    Enum for all supported tokens.
    """
    CODE_EOF = -1
    NEWLINE = 0
    NUMBER = 1
    STRING = 2
    IDENT = 3
    CHANNEL = 4

    # keywords
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
    END_KEYWORDS = 500

    PLUS = 501
    MINUS = 502
    ASTERISK = 503
    SLASH = 504
    LPAR = 505
    RPAR = 506
    COLON = 507
    SEMICOLON = 508
    EQ = 509
    NOTEQ = 510
    LT = 511
    LTEQ = 512
    GT = 513
    GTEQ = 514
    COMMA = 515
