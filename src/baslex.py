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
import os
from bastypes import TokenType, Token
from typing import List, Tuple, Optional

class BASLexer:
    """
    Lexer object keeps track of current position in the source code and produces each token.
    """
    def __init__(self, code: List[Tuple[str, int, str]]) -> None:
        self.orgcode = code
        self.reset()

    def reset(self) -> None:
        """
        Sets the code as a continuous string, appends a newline to
        simplify lexing/parsing the last token/statement and points
        to the first char in the code.
        """
        self.source:    str = ''.join(l for _, _, l in self.orgcode) + '\n'
        self.cur_char:  str = ''   # Current character in the string.
        self.cur_pos:   int = -1    # Current position in the string.
        self.cur_line:  int = 0
        self.last_token: Optional[Token] = None
        self.next_char()

    def get_srccode(self, linenum: int) -> Tuple[str, int , str]:
        if linenum >= len(self.orgcode):
            return (self.orgcode[0][0], -1, "EOF")
        return self.orgcode[linenum]

    def next_char(self) -> None:
        """
        Points to the next character in the source code.
        Returns 0 if end-of-file is reached
        """
        self.cur_pos += 1
        if self.cur_pos >= len(self.source):
            self.cur_char = '\0'  # EOF
        else:
            self.cur_char = self.source[self.cur_pos]

    def peek(self) -> str:
        """Returns the lookahead character"""
        if self.cur_pos + 1 >= len(self.source):
            return '\0'
        return self.source[self.cur_pos + 1]

    def abort(self, message: str, extrainfo: str = "") -> None:
        """Stops with an error message adding file name and original file number"""
        file, linenum, line = self.orgcode[self.cur_line]
        file = os.path.basename(file)
        print("Fatal error in %s:%d: %s -> %s %s" % (file, linenum, line.strip(), message, extrainfo))
        sys.exit(1)

    def _get_operator(self) -> Optional[Token]:
        """ Returns a token describing an operator (numeric o logical). None if the
        current character does not belong to an operator."""
        if self.cur_char == '+':
            return Token(self.cur_char, TokenType.PLUS, self.cur_line)
        elif self.cur_char == '-':
            return Token(self.cur_char, TokenType.MINUS, self.cur_line)
        elif self.cur_char == '*':
            return Token(self.cur_char, TokenType.ASTERISK, self.cur_line)
        elif self.cur_char == '/':
            return Token(self.cur_char, TokenType.SLASH, self.cur_line)
        elif self.cur_char == '\\':
            return Token(self.cur_char, TokenType.LSLASH, self.cur_line)
        elif self.cur_char == '(':
            return Token(self.cur_char, TokenType.LPAR, self.cur_line)
        elif self.cur_char == ')':
            return Token(self.cur_char, TokenType.RPAR, self.cur_line)
        elif self.cur_char == '=':
            return Token(self.cur_char, TokenType.EQ, self.cur_line)
        elif self.cur_char == '>':
            # Check whether this is token is > or >=
            if self.peek() == '=':
                last_char = self.cur_char
                self.next_char()
                return Token(last_char + self.cur_char, TokenType.GTEQ, self.cur_line)
            else:
                return Token(self.cur_char, TokenType.GT, self.cur_line)
        elif self.cur_char == '<':
            # Check whether this token is < or <=
            last_char = self.cur_char
            if self.peek() == '=':
                self.next_char()
                return Token(last_char + self.cur_char, TokenType.LTEQ, self.cur_line)
            elif self.peek() == '>':
                self.next_char()
                return Token(last_char + self.cur_char, TokenType.NOTEQ, self.cur_line)
            else:
                return Token(self.cur_char, TokenType.LT, self.cur_line)
        return None

    def _get_quotedtext(self) -> Token:
        """ Returns all characters between quotations as a STRING token"""
        self.next_char()
        start_pos = self.cur_pos
        while self.cur_char != '\"':
            self.next_char()
            if self.cur_char == '\n':
                self.abort("strings must be enclosed in quotation marks")
        text = self.source[start_pos : self.cur_pos]
        return Token(text, TokenType.STRING, self.cur_line)

    def _get_number(self) -> Token:
        """
        Returns all consecutive digits (and decimal if there is one) as a
        Numeric token.
        """
        start_pos = self.cur_pos
        tktype = TokenType.INTEGER
        while self.peek().isdigit():
            self.next_char()
        if self.peek() == '.': # REAL!
            tktype = TokenType.REAL
            self.next_char()
            # Must have at least one digit after decimal.
            if not self.peek().isdigit(): 
                self.abort("number contains illegal characters")
            while self.peek().isdigit():
                self.next_char()
        text = self.source[start_pos : self.cur_pos + 1]
        return Token(text, tktype, self.cur_line)

    def _get_identifier_text(self) -> str:
        """
        Returns all characters that compose a valid word. Words can be
        labels, variables or keywords.
        """
        start_pos = self.cur_pos
        while self.peek().isalnum():
            self.next_char()
        if self.peek() in ['!', '%', '$']:
            # Type symbols and end character for some functions
            self.next_char()
        return self.source[start_pos : self.cur_pos + 1].upper()

    def rollback(self) -> Optional[Token]:
        if self.last_token is not None:
            self.cur_pos = self.last_token.srcpos
            self.cur_line = self.last_token.srcline
            self.cur_char = self.source[self.cur_pos]
            return self.get_token()
        return None

    def get_token(self) -> Optional[Token]:
        """
        Consumes source code characters until a valid Token can be created or
        an error is raised.
        """
        self.lstrip()
        self.skip_comment()
        token = None
        inipos = self.cur_pos
    
        # Check current pointed character to see if we can decide what it is.
        if self.cur_char == '\n':
            token = Token('', TokenType.NEWLINE, self.cur_line)

        elif self.cur_char == '\0':
            token = Token('', TokenType.CODE_EOF, self.cur_line)

        elif self.cur_char == ':':
            token = Token(':', TokenType.COLON, self.cur_line)

        elif self.cur_char == ';':
            token = Token(';', TokenType.SEMICOLON, self.cur_line)

        elif self.cur_char == ',':
            token = Token(',', TokenType.COMMA, self.cur_line)

        elif self.cur_char in "+-*/=><()":
            token = self._get_operator()
        
        elif self.cur_char == '\"':
            token = self._get_quotedtext()
        
        elif self.cur_char == '#':
            token = Token('#', TokenType.CHANNEL, self.cur_line)

        elif self.cur_char.isdigit():
            token = self._get_number()
           
        elif self.cur_char.isalpha():
            # can be an identifier, keyword or special operator (like MOD)
            text = self._get_identifier_text()
            keyword = Token.get_keyword(text)
            if keyword is not None:
                token = Token(text, keyword, self.cur_line)
            elif text.upper() == 'MOD':
                token = Token('%', TokenType.MOD, self.cur_line)
            else:
                # Identifier or label
                token = Token(text, TokenType.IDENT, self.cur_line)
        else:
            self.abort("unexpected character found '" + self.cur_char + "'")

        if token is not None:
            token.srcpos = inipos
            if token.type == TokenType.NEWLINE:
                # we are going to start a new line of code
                self.cur_line = self.cur_line + 1
            self.last_token = token
        self.next_char()
        return token

    def lstrip(self) -> None:
        """Skip whitespace except newlines, which we will use to indicate the end of a statement."""
        while self.cur_char == ' ' or self.cur_char == '\t' or self.cur_char == '\r':
            self.next_char()

    def skip_comment(self) -> None:
        if self.cur_char == "'":
            while self.cur_char != '\n':
                self.next_char()

