# parser.py
# Parser: converts Tokens into an AST

from tokens import Token, TokenType
from ast_nodes import (
    Program, VarDecl, UseStmt, IfStmt, WhileStmt, ForStmt,
    BreakStmt, ContinueStmt, FnDecl, ReturnStmt, ExprStmt,
    NumberLit, StringLit, BoolLit, NoneLit, Ident, BinOp, UnaryOp,
    CallExpr, AssignExpr, ListLit, DictLit, IndexExpr, RangeExpr,
    TypeNode, Param, MemberExpr,
)


class ParseError(Exception):
    def __init__(self, message, token):
        super().__init__(f"[line {token.line}, col {token.column}] {message}")
        self.token = token


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=1):
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    def advance(self):
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def check(self, *types):
        return self.current().type in types

    def match(self, *types):
        if self.current().type in types:
            return self.advance()
        return None

    def expect(self, ttype, message):
        if self.current().type != ttype:
            tok = self.current()
            raise ParseError(
                f"{message} (found {tok.type.name}: {tok.value!r})",
                tok
            )
        return self.advance()

    def parse(self):
        statements = []
        while not self.check(TokenType.EOF):
            statements.append(self.statement())
        return Program(statements)

    def parse_type(self):
        name_tok = self.expect(TokenType.IDENT, "expected type name")
        args = []
        if self.check(TokenType.LBRACKET):
            self.advance()
            args.append(self.parse_type())
            while self.match(TokenType.COMMA):
                args.append(self.parse_type())
            self.expect(TokenType.RBRACKET, "expected ']' to close type")
        return TypeNode(name_tok.value, args, name_tok.line)

    def statement(self):
        t = self.current()

        if t.type in (TokenType.SET, TokenType.CONST):
            return self.var_decl()
        if t.type == TokenType.USE:
            return self.use_stmt()
        if t.type == TokenType.IF:
            return self.if_stmt()
        if t.type == TokenType.WHILE:
            return self.while_stmt()
        if t.type == TokenType.FOR:
            return self.for_stmt()
        if t.type == TokenType.BREAK:
            self.advance()
            self.expect(TokenType.SEMICOLON, "expected ';' after break")
            return BreakStmt(t.line)
        if t.type == TokenType.CONTINUE:
            self.advance()
            self.expect(TokenType.SEMICOLON, "expected ';' after continue")
            return ContinueStmt(t.line)
        if t.type == TokenType.FN:
            return self.fn_decl()
        if t.type == TokenType.RETURN:
            return self.return_stmt()
        if t.type == TokenType.LBRACE:
            return self.block()

        return self.expr_stmt()

    def var_decl(self):
        keyword = self.advance()
        is_const = (keyword.type == TokenType.CONST)

        name_tok = self.expect(TokenType.IDENT, "expected variable name after set/const")

        type_ann = None
        if self.match(TokenType.COLON):
            type_ann = self.parse_type()

        has_value = False
        value = None

        if self.match(TokenType.ASSIGN):
            value = self.expression()
            has_value = True
        else:
            if type_ann is None:
                raise ParseError(
                    "expected '=' or ':' with a type after variable name",
                    name_tok
                )
            if is_const:
                raise ParseError(
                    "const must be initialized with a value",
                    name_tok
                )

        self.expect(TokenType.SEMICOLON, "expected ';' after declaration")

        return VarDecl(
            name=name_tok.value,
            type_annotation=type_ann,
            value=value,
            is_const=is_const,
            line=keyword.line,
            has_value=has_value,
        )

    def use_stmt(self):
        kw = self.advance()
        name = self.expect(TokenType.IDENT, "expected module name after use")
        self.expect(TokenType.SEMICOLON, "expected ';' after use")
        return UseStmt(module=name.value, line=kw.line)

    def if_stmt(self):
        kw = self.advance()
        self.expect(TokenType.LPAREN, "expected '(' after if")
        cond = self.expression()
        self.expect(TokenType.RPAREN, "expected ')' after condition")
        then_block = self.block()
        else_block = None
        if self.match(TokenType.ELSE):
            if self.check(TokenType.IF):
                else_block = [self.if_stmt()]
            else:
                else_block = self.block()
        return IfStmt(cond, then_block, else_block, kw.line)

    def while_stmt(self):
        kw = self.advance()
        self.expect(TokenType.LPAREN, "expected '(' after while")
        cond = self.expression()
        self.expect(TokenType.RPAREN, "expected ')' after condition")
        body = self.block()
        return WhileStmt(cond, body, kw.line)

    def for_stmt(self):
        kw = self.advance()
        name = self.expect(TokenType.IDENT, "expected variable name after for")
        self.expect(TokenType.IN, "expected 'in' after variable name")
        iterable = self.expression()
        body = self.block()
        return ForStmt(name.value, iterable, body, kw.line)

    def fn_decl(self):
        kw = self.advance()
        name = self.expect(TokenType.IDENT, "expected function name after fn")
        self.expect(TokenType.LPAREN, "expected '(' after function name")

        params = []
        if not self.check(TokenType.RPAREN):
            while True:
                pname = self.expect(TokenType.IDENT, "expected parameter name")
                ptype = None
                if self.match(TokenType.COLON):
                    ptype = self.parse_type()
                params.append(Param(pname.value, ptype, pname.line))
                if not self.match(TokenType.COMMA):
                    break

        self.expect(TokenType.RPAREN, "expected ')' after parameters")

        return_type = None
        if self.match(TokenType.ARROW):
            return_type = self.parse_type()

        body = self.block()
        return FnDecl(name.value, params, return_type, body, kw.line)

    def return_stmt(self):
        kw = self.advance()
        value = None
        if not self.check(TokenType.SEMICOLON):
            value = self.expression()
        self.expect(TokenType.SEMICOLON, "expected ';' after return")
        return ReturnStmt(value, kw.line)

    def expr_stmt(self):
        if (self.current().type == TokenType.IDENT
                and self.peek().type == TokenType.ASSIGN):
            name_tok = self.advance()
            self.advance()
            value = self.expression()
            self.expect(TokenType.SEMICOLON, "expected ';' after assignment")
            return ExprStmt(AssignExpr(name_tok.value, value, name_tok.line), name_tok.line)

        expr = self.expression()
        tok = self.expect(TokenType.SEMICOLON, "expected ';' after statement")
        return ExprStmt(expr, tok.line)

    def block(self):
        self.expect(TokenType.LBRACE, "expected '{' to start block")
        stmts = []
        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            stmts.append(self.statement())
        self.expect(TokenType.RBRACE, "expected '}' to end block")
        return stmts

    def expression(self):
        left = self.or_expr()
        if self.check(TokenType.DOTDOT):
            tok = self.advance()
            right = self.or_expr()
            return RangeExpr(left, right, tok.line)
        return left

    def or_expr(self):
        left = self.and_expr()
        while self.check(TokenType.OR):
            tok = self.advance()
            right = self.and_expr()
            left = BinOp(left, "or", right, tok.line)
        return left

    def and_expr(self):
        left = self.equality()
        while self.check(TokenType.AND):
            tok = self.advance()
            right = self.equality()
            left = BinOp(left, "and", right, tok.line)
        return left

    def equality(self):
        left = self.comparison()
        while self.check(TokenType.EQ, TokenType.NEQ):
            tok = self.advance()
            right = self.comparison()
            op = "==" if tok.type == TokenType.EQ else "!="
            left = BinOp(left, op, right, tok.line)
        return left

    def comparison(self):
        left = self.term()
        while self.check(TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            tok = self.advance()
            right = self.term()
            op_map = {
                TokenType.LT: "<", TokenType.GT: ">",
                TokenType.LTE: "<=", TokenType.GTE: ">=",
            }
            left = BinOp(left, op_map[tok.type], right, tok.line)
        return left

    def term(self):
        left = self.factor()
        while self.check(TokenType.PLUS, TokenType.MINUS):
            tok = self.advance()
            right = self.factor()
            op = "+" if tok.type == TokenType.PLUS else "-"
            left = BinOp(left, op, right, tok.line)
        return left

    def factor(self):
        left = self.unary()
        while self.check(TokenType.STAR, TokenType.SLASH):
            tok = self.advance()
            right = self.unary()
            op = "*" if tok.type == TokenType.STAR else "/"
            left = BinOp(left, op, right, tok.line)
        return left

    def unary(self):
        if self.check(TokenType.MINUS, TokenType.NOT_OP, TokenType.NOT):
            tok = self.advance()
            operand = self.unary()
            op_map = {
                TokenType.MINUS: "-",
                TokenType.NOT_OP: "!",
                TokenType.NOT: "!",
            }
            return UnaryOp(op_map[tok.type], operand, tok.line)
        return self.postfix()

    def postfix(self):
        expr = self.primary()
        while True:
            if self.check(TokenType.LPAREN):
                tok = self.advance()
                args = []
                if not self.check(TokenType.RPAREN):
                    while True:
                        args.append(self.expression())
                        if not self.match(TokenType.COMMA):
                            break
                self.expect(TokenType.RPAREN, "expected ')' after arguments")
                expr = CallExpr(expr, args, tok.line)
            elif self.check(TokenType.LBRACKET):
                tok = self.advance()
                index = self.expression()
                self.expect(TokenType.RBRACKET, "expected ']' after index")
                expr = IndexExpr(expr, index, tok.line)
            elif self.check(TokenType.DOT):
                tok = self.advance()
                member = self.expect(TokenType.IDENT, "expected member name after '.'")
                expr = MemberExpr(expr, member.value, tok.line)
            else:
                break
        return expr

    def primary(self):
        tok = self.current()

        if tok.type == TokenType.NUMBER:
            self.advance()
            value = float(tok.value) if '.' in tok.value else int(tok.value)
            return NumberLit(value, tok.line)

        if tok.type == TokenType.STRING:
            self.advance()
            return StringLit(tok.value, tok.line)

        if tok.type == TokenType.TRUE:
            self.advance()
            return BoolLit(True, tok.line)

        if tok.type == TokenType.FALSE:
            self.advance()
            return BoolLit(False, tok.line)

        if tok.type == TokenType.NONE:
            self.advance()
            return NoneLit(tok.line)

        if tok.type == TokenType.IDENT:
            self.advance()
            return Ident(tok.value, tok.line)

        if tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.expression()
            self.expect(TokenType.RPAREN, "expected ')'")
            return expr

        if tok.type == TokenType.LBRACKET:
            return self.list_lit()

        if tok.type == TokenType.LBRACE:
            return self.dict_lit()

        raise ParseError(
            f"unexpected expression (found {tok.type.name}: {tok.value!r})",
            tok
        )

    def list_lit(self):
        start = self.expect(TokenType.LBRACKET, "expected '['")
        elements = []
        if not self.check(TokenType.RBRACKET):
            while True:
                elements.append(self.expression())
                if not self.match(TokenType.COMMA):
                    break
        self.expect(TokenType.RBRACKET, "expected ']' to close list")
        return ListLit(elements, start.line)

    def dict_lit(self):
        start = self.expect(TokenType.LBRACE, "expected '{'")
        keys = []
        values = []
        if not self.check(TokenType.RBRACE):
            while True:
                key = self.expression()
                self.expect(TokenType.COLON, "expected ':' between key and value")
                value = self.expression()
                keys.append(key)
                values.append(value)
                if not self.match(TokenType.COMMA):
                    break
        self.expect(TokenType.RBRACE, "expected '}' to close dict")
        return DictLit(keys, values, start.line)