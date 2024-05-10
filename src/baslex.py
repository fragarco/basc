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
from bastypes import TokenType, Token
    
class BASLexer:
    """
    Lexer object keeps track of current position in the source code and produces each token.
    """
    def __init__(self, code):
        self.orgcode = code
        self.reset()

    def reset(self):
        """
        Sets the code as a continuous string, appends a newline to
        simplify lexing/parsing the last token/statement and points
        to the first char in the code.
        """
        self.source = ''.join(l for _, _, l in self.orgcode) + '\n'
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
        """
        Points to the next character in the source code.
        Returns 0 if end-of-file is reached
        """
        self.cur_pos += 1
        if self.cur_pos >= len(self.source):
            self.cur_char = '\0'  # EOF
        else:
            self.cur_char = self.source[self.cur_pos]

    def peek(self):
        """Returns the lookahead character"""
        if self.cur_pos + 1 >= len(self.source):
            return '\0'
        return self.source[self.cur_pos + 1]

    def abort(self, message, extrainfo = ""):
        """Stops with an error message adding file name and original file number"""
        file, linenum, _ = self.orgcode[self.cur_line]
        print("Fatal error in %s:%d: %s -> %s %s" % (file, linenum, self.cur_line.strip(), message, extrainfo))
        sys.exit(1)

    def _get_operator(self):
        """ Returns a token describing an operator (numeric o logical)"""
        if self.cur_char == '+':
            return Token(self.cur_char, TokenType.PLUS)
        elif self.cur_char == '-':
            return Token(self.cur_char, TokenType.MINUS)
        elif self.cur_char == '*':
            return Token(self.cur_char, TokenType.ASTERISK)
        elif self.cur_char == '/':
            return Token(self.cur_char, TokenType.SLASH)
        elif self.cur_char == '\\':
            return Token(self.cur_char, TokenType.LSLASH)
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
            # Check whether this token is < or <=
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
        """ Returns all characters between quotations as a STRING token"""
        self.next_char()
        start_pos = self.cur_pos
        while self.cur_char != '\"':
            self.next_char()
            if self.cur_char == '\n':
                self.abort("strings must be enclosed in quotation marks")
        text = self.source[start_pos : self.cur_pos]
        return Token(text, TokenType.STRING)

    def _get_number(self):
        """
        Returns all consecutive digits (and decimal if there is one) as a
        Numeric token.
        """
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
        """
        Returns all characters that compose a valid word. Words can be
        labels, variables or keywords.
        """
        start_pos = self.cur_pos
        while self.peek().isalnum():
            self.next_char()
        return self.source[start_pos : self.cur_pos + 1].upper()

    def get_token(self):
        """
        Consumes source code characters until a valid Token can be created or
        an error is raised.
        """
        self.lstrip()
        self.skip_comment()
        token = None

        # Check current pointed character to see if we can decide what it is.
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
            token = Token('#', TokenType.STREAM)

        elif self.cur_char.isdigit():
            token = self._get_number()
           
        elif self.cur_char.isalpha():
            # can be an identifier, keyword or special operator (like MOD)
            text = self._get_identifier_text()
            keyword = Token.get_keyword(text)
            if keyword != None:
                token = Token(text, keyword)
            elif text.upper() == 'MOD':
                token = Token('%', TokenType.MOD)
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

