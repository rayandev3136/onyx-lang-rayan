# tokens.py
# Token type definitions for the Onyx language

from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()

    SET = auto()
    CONST = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    BREAK = auto()
    CONTINUE = auto()
    FN = auto()
    RETURN = auto()
    TRUE = auto()
    FALSE = auto()
    NONE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    USE = auto()
    MATCH = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    ASSIGN = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    NOT_OP = auto()

    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COLON = auto()
    COMMA = auto()
    SEMICOLON = auto()
    DOT = auto()
    DOTDOT = auto()
    ARROW = auto()
    FATARROW = auto()

    EOF = auto()


KEYWORDS = {
    "set": TokenType.SET,
    "const": TokenType.CONST,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "fn": TokenType.FN,
    "return": TokenType.RETURN,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "None": TokenType.NONE,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "use": TokenType.USE,
    "match": TokenType.MATCH,
}


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.column})"