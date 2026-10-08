# lexer.py
# Lexer: converts source code into a list of Tokens

from tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"[line {line}, col {column}] {message}")
        self.line = line
        self.column = column


class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def current_char(self):
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]

    def peek_char(self, offset=1):
        if self.pos + offset >= len(self.source):
            return None
        return self.source[self.pos + offset]

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def tokenize(self):
        while self.pos < len(self.source):
            ch = self.current_char()

            if ch in ' \t\r\n':
                self.advance()
                continue

            if ch == '/' and self.peek_char() == '/':
                while self.current_char() is not None and self.current_char() != '\n':
                    self.advance()
                continue

            if ch.isdigit():
                self.read_number()
                continue

            if ch.isalpha() or ch == '_':
                self.read_identifier()
                continue

            if ch == '"':
                self.read_string()
                continue

            self.read_symbol()

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens

    def read_number(self):
        start_line, start_col = self.line, self.column
        num = ''
        has_dot = False
        while self.current_char() is not None and (self.current_char().isdigit() or self.current_char() == '.'):
            if self.current_char() == '.':
                nxt = self.peek_char()
                if nxt == '.':
                    break
                if nxt is not None and (nxt.isalpha() or nxt == '_'):
                    break
                if has_dot:
                    raise LexerError("number contains more than one decimal point", self.line, self.column)
                has_dot = True
            num += self.advance()
        self.tokens.append(Token(TokenType.NUMBER, num, start_line, start_col))

    def read_identifier(self):
        start_line, start_col = self.line, self.column
        ident = ''
        while self.current_char() is not None and (self.current_char().isalnum() or self.current_char() == '_'):
            ident += self.advance()
        ttype = KEYWORDS.get(ident, TokenType.IDENT)
        self.tokens.append(Token(ttype, ident, start_line, start_col))

    def read_string(self):
        start_line, start_col = self.line, self.column
        self.advance()
        text = ''
        while self.current_char() is not None and self.current_char() != '"':
            if self.current_char() == '\\':
                self.advance()
                esc = self.advance()
                if esc == 'n':
                    text += '\n'
                elif esc == 't':
                    text += '\t'
                elif esc == '"':
                    text += '"'
                elif esc == '\\':
                    text += '\\'
                else:
                    text += esc
            else:
                text += self.advance()
        if self.current_char() is None:
            raise LexerError("unterminated string", start_line, start_col)
        self.advance()
        self.tokens.append(Token(TokenType.STRING, text, start_line, start_col))

    def read_symbol(self):
        ch = self.current_char()
        start_line, start_col = self.line, self.column

        two = ch + (self.peek_char() or '')
        if two == '==':
            self.advance(); self.advance()
            self.tokens.append(Token(TokenType.EQ, '==', start_line, start_col))
            return
        if two == '!=':
            self.advance(); self.advance()
            self.tokens.append(Token(TokenType.NEQ, '!=', start_line, start_col))
            return
        if two == '<=':
            self.advance(); self.advance()
            self.tokens.append(Token(TokenType.LTE, '<=', start_line, start_col))
            return
        if two == '>=':
            self.advance(); self.advance()
            self.tokens.append(Token(TokenType.GTE, '>=', start_line, start_col))
            return
        if two == '..':
            self.advance(); self.advance()
            self.tokens.append(Token(TokenType.DOTDOT, '..', start_line, start_col))
            return
        if two == '=>':
            self.advance(); self.advance()
            self.tokens.append(Token(TokenType.FATARROW, '=>', start_line, start_col))
            return
        if two == '->':
            self.advance(); self.advance()
            self.tokens.append(Token(TokenType.ARROW, '->', start_line, start_col))
            return

        single = {
            '+': TokenType.PLUS,   '-': TokenType.MINUS,
            '*': TokenType.STAR,   '/': TokenType.SLASH,
            '=': TokenType.ASSIGN, '<': TokenType.LT, '>': TokenType.GT,
            '!': TokenType.NOT_OP,
            '(': TokenType.LPAREN, ')': TokenType.RPAREN,
            '{': TokenType.LBRACE, '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET, ']': TokenType.RBRACKET,
            ':': TokenType.COLON,
            '.': TokenType.DOT,
            ',': TokenType.COMMA,  ';': TokenType.SEMICOLON,
        }
        if ch in single:
            self.advance()
            self.tokens.append(Token(single[ch], ch, start_line, start_col))
            return

        raise LexerError(f"unknown symbol: {ch!r}", start_line, start_col)