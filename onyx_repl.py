# onyx_repl.py
# Onyx interactive REPL

import os
from lexer import Lexer, LexerError
from parser import Parser, ParseError
from evaluator import Evaluator
from environment import Environment, RuntimeError_Onyx
from ast_nodes import ExprStmt, dump
import colors as col


BUILTIN_NAMES = {
    "say", "ask", "str", "int", "float", "len", "range",
    "push", "pop", "keys", "values", "has", "native",
}


class Repl:
    def __init__(self):
        self.evaluator = Evaluator()
        self.env = self.evaluator.globals
        self.show_ast = False

    def banner(self):
        print("")
        print(col.cyan("=========================================="))
        print(col.bold(col.cyan("         Onyx REPL v0.5")))
        print(col.cyan("=========================================="))
        print(col.dim("Type ") + col.yellow(":help") + col.dim(" for help, ") + col.yellow(":quit") + col.dim(" to exit"))
        print("")

    def print_help(self):
        print("")
        print(col.bold("REPL commands:"))
        print("  " + col.yellow(":help") + "           show this help")
        print("  " + col.yellow(":quit") + " / " + col.yellow(":q") + "      exit")
        print("  " + col.yellow(":vars") + "           list defined variables")
        print("  " + col.yellow(":clear") + "          clear the screen")
        print("  " + col.yellow(":reset") + "          remove all variables")
        print("  " + col.yellow(":ast") + "            toggle AST display")
        print("  " + col.yellow(":run <file>") + "     run a file")
        print("")

    def list_vars(self):
        user_vars = {
            k: v for k, v in self.env.values.items()
            if k not in BUILTIN_NAMES and k != "_"
        }
        if not user_vars:
            print(col.dim("(no variables defined)"))
            return
        for name in sorted(user_vars.keys()):
            value = user_vars[name]
            print("  " + col.cyan(name) + " = " + self.evaluator.repr_onyx(value))

    def reset(self):
        self.evaluator = Evaluator()
        self.env = self.evaluator.globals
        print(col.green("[OK] ") + "all variables cleared")

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def is_complete(self, source):
        depth = 0
        in_string = False
        escape = False
        for ch in source:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in "({[":
                depth += 1
            elif ch in ")}]":
                depth -= 1
        return depth <= 0

    def normalize(self, source):
        s = source.rstrip()
        if not s:
            return s
        if s.endswith(";") or s.endswith("}") or s.endswith("{"):
            return s
        return s + "\n;"

    def run_source(self, source):
        try:
            tokens = Lexer(source).tokenize()
        except LexerError as e:
            print(col.lexical_prefix() + str(e))
            return None, False

        try:
            tree = Parser(tokens).parse()
        except ParseError as e:
            print(col.syntax_prefix() + str(e))
            return None, False

        if self.show_ast:
            print(col.dim(dump(tree)))

        last_value = None
        has_value = False
        try:
            stmts = tree.statements
            for i, stmt in enumerate(stmts):
                is_last = (i == len(stmts) - 1)
                if is_last and isinstance(stmt, ExprStmt):
                    last_value = self.evaluator.eval_expr(stmt.expr, self.env)
                    has_value = True
                else:
                    self.evaluator.exec_stmt(stmt, self.env)
        except RuntimeError_Onyx as e:
            print(col.runtime_prefix() + str(e))
            return None, False

        return last_value, has_value

    def loop(self):
        self.banner()
        buffer = ""

        while True:
            prompt = col.dim("... ") if buffer else col.cyan(">>> ")
            try:
                line = input(prompt)
            except (EOFError, KeyboardInterrupt):
                print("")
                break

            if not buffer:
                stripped = line.strip()

                if stripped.startswith(":"):
                    if stripped in (":quit", ":q", ":exit"):
                        break
                    elif stripped == ":help":
                        self.print_help()
                    elif stripped == ":vars":
                        self.list_vars()
                    elif stripped == ":clear":
                        self.clear_screen()
                        self.banner()
                    elif stripped == ":reset":
                        self.reset()
                    elif stripped == ":ast":
                        self.show_ast = not self.show_ast
                        state = col.green("on") if self.show_ast else col.dim("off")
                        print("AST display: " + state)
                    elif stripped.startswith(":run "):
                        filename = stripped[5:].strip()
                        try:
                            with open(filename, 'r', encoding='utf-8') as f:
                                src = f.read()
                            self.run_source(src)
                        except FileNotFoundError:
                            print(col.error_prefix() + "file not found: " + filename)
                    else:
                        print(col.error_prefix() + "unknown command: " + stripped)
                    continue

                if not stripped:
                    continue

            buffer += line + "\n"

            if not self.is_complete(buffer):
                continue

            source = self.normalize(buffer)
            buffer = ""

            value, has_value = self.run_source(source)

            if has_value and value is not None:
                self.env.values["_"] = value
                print(self.evaluator.repr_onyx(value))


def main():
    Repl().loop()


if __name__ == "__main__":
    main()