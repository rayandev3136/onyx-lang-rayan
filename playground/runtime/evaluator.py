# evaluator.py
# Tree-walking evaluator with module caching

import os
import time as _time
import math as _math
import random as _random
import shutil as _shutil

from ast_nodes import (
    Program, VarDecl, UseStmt, IfStmt, WhileStmt, ForStmt,
    BreakStmt, ContinueStmt, FnDecl, ReturnStmt, ExprStmt,
    NumberLit, StringLit, BoolLit, NoneLit, Ident, BinOp, UnaryOp,
    CallExpr, AssignExpr, ListLit, DictLit, IndexExpr, RangeExpr,
    MemberExpr,
)
from environment import Environment, RuntimeError_Onyx
from lexer import Lexer, LexerError
from parser import Parser, ParseError
import module_cache


def _list_sort(lst):
    lst.sort()
    return lst

def _list_reverse(lst):
    lst.reverse()
    return lst

def _list_contains(lst, item):
    return item in lst

def _list_index_of(lst, item):
    try:
        return lst.index(item)
    except ValueError:
        return -1

def _list_slice(lst, start, end):
    return lst[start:end]

def _list_first(lst):
    if not lst:
        raise RuntimeError_Onyx("list.first on empty list")
    return lst[0]

def _list_last(lst):
    if not lst:
        raise RuntimeError_Onyx("list.last on empty list")
    return lst[-1]

def _list_concat(a, b):
    return a + b

def _list_repeat(lst, n):
    return lst * n

def _list_sum(lst):
    total = 0
    for x in lst:
        if not isinstance(x, (int, float)):
            raise RuntimeError_Onyx("list.sum requires numeric list")
        total += x
    return total

def _list_min(lst):
    if not lst:
        raise RuntimeError_Onyx("list.min on empty list")
    return min(lst)

def _list_max(lst):
    if not lst:
        raise RuntimeError_Onyx("list.max on empty list")
    return max(lst)


def _dict_merge(a, b):
    result = dict(a)
    result.update(b)
    return result

def _dict_get(d, key, default=None):
    return d.get(key, default)

def _dict_items(d):
    return [[k, v] for k, v in d.items()]

def _dict_remove(d, key):
    d.pop(key, None)
    return d

def _dict_size(d):
    return len(d)


def _time_now():
    return _time.time()

def _time_sleep(seconds):
    _time.sleep(seconds)
    return None

def _time_format(ts, fmt):
    return _time.strftime(fmt, _time.localtime(ts))


def _os_cwd():
    return os.getcwd()

def _os_listdir(path):
    return os.listdir(path)

def _os_mkdir(path):
    os.makedirs(path, exist_ok=True)
    return None

def _os_remove(path):
    if os.path.isdir(path):
        _shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)
    return None

def _os_path_exists(path):
    return os.path.exists(path)

def _os_is_file(path):
    return os.path.isfile(path)

def _os_is_dir(path):
    return os.path.isdir(path)


NATIVES = {
    # math
    "math.sqrt":  _math.sqrt,
    "math.pow":   _math.pow,
    "math.sin":   _math.sin,
    "math.cos":   _math.cos,
    "math.tan":   _math.tan,
    "math.log":   _math.log,
    "math.log10": _math.log10,
    "math.exp":   _math.exp,
    "math.floor": _math.floor,
    "math.ceil":  _math.ceil,
    "math.abs":   abs,
    "math.round": round,
    "math.min":   min,
    "math.max":   max,

    # string
    "string.upper":      lambda s: s.upper(),
    "string.lower":      lambda s: s.lower(),
    "string.strip":      lambda s: s.strip(),
    "string.split":      lambda s, sep: s.split(sep),
    "string.join":       lambda lst, sep: sep.join(lst),
    "string.replace":    lambda s, a, b: s.replace(a, b),
    "string.contains":   lambda s, sub: sub in s,
    "string.startswith": lambda s, p: s.startswith(p),
    "string.endswith":   lambda s, p: s.endswith(p),
    "string.length":     len,

    # random
    "random.int":     lambda a, b: _random.randint(a, b),
    "random.float":   lambda: _random.random(),
    "random.choice":  lambda lst: _random.choice(lst),
    "random.shuffle": lambda lst: (_random.shuffle(lst), lst)[1],

    # io
    "io.read":    lambda path: open(path, 'r', encoding='utf-8').read(),
    "io.write":   lambda path, content: (open(path, 'w', encoding='utf-8').write(content), None)[1],
    "io.exists":  os.path.exists,
    "io.listdir": lambda path: os.listdir(path),

    # list
    "list.sort":     _list_sort,
    "list.reverse":  _list_reverse,
    "list.contains": _list_contains,
    "list.index_of": _list_index_of,
    "list.slice":    _list_slice,
    "list.first":    _list_first,
    "list.last":     _list_last,
    "list.concat":   _list_concat,
    "list.repeat":   _list_repeat,
    "list.sum":      _list_sum,
    "list.min":      _list_min,
    "list.max":      _list_max,

    # dict
    "dict.merge":  _dict_merge,
    "dict.get":    _dict_get,
    "dict.items":  _dict_items,
    "dict.remove": _dict_remove,
    "dict.size":   _dict_size,

    # time
    "time.now":    _time_now,
    "time.sleep":  _time_sleep,
    "time.format": _time_format,

    # os
    "os.cwd":         _os_cwd,
    "os.listdir":     _os_listdir,
    "os.mkdir":       _os_mkdir,
    "os.remove":      _os_remove,
    "os.path_exists": _os_path_exists,
    "os.is_file":     _os_is_file,
    "os.is_dir":      _os_is_dir,
}


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class Function:
    def __init__(self, name, param_names, body, closure):
        self.name = name
        self.param_names = param_names
        self.body = body
        self.closure = closure


class Module:
    def __init__(self, name, env):
        self.name = name
        self.env = env


class Evaluator:
    def __init__(self, verbose=False):
        self.globals = Environment()
        self._module_cache = {}
        self.verbose = verbose
        self._install_builtins()

    def _install_builtins(self):
        def builtin_say(*args):
            print(" ".join(self.stringify(a) for a in args))
            return None

        def builtin_ask(prompt="", type_hint=None):
            try:
                raw = input(prompt)
            except EOFError:
                raw = ""
            if type_hint is None or type_hint == "string":
                return raw
            if type_hint == "int":
                try:
                    return int(raw)
                except ValueError:
                    raise RuntimeError_Onyx(f"invalid int input: '{raw}'")
            if type_hint == "float":
                try:
                    return float(raw)
                except ValueError:
                    raise RuntimeError_Onyx(f"invalid float input: '{raw}'")
            if type_hint == "bool":
                low = raw.strip().lower()
                if low in ("true", "1", "yes", "y"):
                    return True
                if low in ("false", "0", "no", "n"):
                    return False
                raise RuntimeError_Onyx(f"invalid bool input: '{raw}'")
            raise RuntimeError_Onyx(f"unknown type hint: '{type_hint}'")

        def builtin_str(x):
            return self.repr_onyx(x)

        def builtin_int(x):
            try:
                return int(x)
            except (ValueError, TypeError):
                raise RuntimeError_Onyx(f"cannot convert '{x}' to int")

        def builtin_float(x):
            try:
                return float(x)
            except (ValueError, TypeError):
                raise RuntimeError_Onyx(f"cannot convert '{x}' to float")

        def builtin_len(x):
            try:
                return len(x)
            except TypeError:
                raise RuntimeError_Onyx(f"cannot get length of '{x}'")

        def builtin_range(*args):
            return list(range(*args))

        def builtin_push(lst, item):
            if not isinstance(lst, list):
                raise RuntimeError_Onyx("push expects a list as first argument")
            lst.append(item)
            return None

        def builtin_pop(lst):
            if not isinstance(lst, list):
                raise RuntimeError_Onyx("pop expects a list")
            if not lst:
                raise RuntimeError_Onyx("cannot pop from an empty list")
            return lst.pop()

        def builtin_keys(d):
            if not isinstance(d, dict):
                raise RuntimeError_Onyx("keys expects a dict")
            return list(d.keys())

        def builtin_values(d):
            if not isinstance(d, dict):
                raise RuntimeError_Onyx("values expects a dict")
            return list(d.values())

        def builtin_has(d, key):
            if not isinstance(d, dict):
                raise RuntimeError_Onyx("has expects a dict as first argument")
            return key in d

        def builtin_native(name):
            if not isinstance(name, str):
                raise RuntimeError_Onyx("native expects a string argument")
            if name not in NATIVES:
                raise RuntimeError_Onyx(f"native: '{name}' not registered")
            return NATIVES[name]

        self.globals.define("say", builtin_say, is_const=True)
        self.globals.define("ask", builtin_ask, is_const=True)
        self.globals.define("str", builtin_str, is_const=True)
        self.globals.define("int", builtin_int, is_const=True)
        self.globals.define("float", builtin_float, is_const=True)
        self.globals.define("len", builtin_len, is_const=True)
        self.globals.define("range", builtin_range, is_const=True)
        self.globals.define("push", builtin_push, is_const=True)
        self.globals.define("pop", builtin_pop, is_const=True)
        self.globals.define("keys", builtin_keys, is_const=True)
        self.globals.define("values", builtin_values, is_const=True)
        self.globals.define("has", builtin_has, is_const=True)
        self.globals.define("native", builtin_native, is_const=True)

    def default_for_type(self, type_node, line):
        if type_node is None:
            raise RuntimeError_Onyx(
                f"[line {line}] variable with no value must have an explicit type"
            )
        name = type_node.name
        if name == "int":    return 0
        if name == "float":  return 0.0
        if name == "string": return ""
        if name == "bool":   return False
        if name == "none":   return None
        if name == "any":    return None
        if name == "list":   return []
        if name == "dict":   return {}
        raise RuntimeError_Onyx(f"[line {line}] unknown type: {name}")

    def run(self, program, env=None):
        if env is None:
            env = self.globals
        self.exec_block(program.statements, env)

    def exec_block(self, statements, env):
        for stmt in statements:
            self.exec_stmt(stmt, env)

    def exec_stmt(self, stmt, env):
        if isinstance(stmt, VarDecl):
            if stmt.has_value:
                value = self.eval_expr(stmt.value, env)
            else:
                value = self.default_for_type(stmt.type_annotation, stmt.line)
            env.define(stmt.name, value, is_const=stmt.is_const)
            return

        if isinstance(stmt, UseStmt):
            self.load_module(stmt.module, env, stmt.line)
            return

        if isinstance(stmt, IfStmt):
            cond = self.eval_expr(stmt.condition, env)
            if self.truthy(cond):
                self.exec_block(stmt.then_block, Environment(parent=env))
            elif stmt.else_block is not None:
                self.exec_block(stmt.else_block, Environment(parent=env))
            return

        if isinstance(stmt, WhileStmt):
            while self.truthy(self.eval_expr(stmt.condition, env)):
                try:
                    self.exec_block(stmt.body, Environment(parent=env))
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
            return

        if isinstance(stmt, ForStmt):
            iterable = self.eval_expr(stmt.iterable, env)
            if not isinstance(iterable, (list, str)):
                raise RuntimeError_Onyx(
                    f"[line {stmt.line}] for expects a list or string, got {type(iterable).__name__}"
                )
            for item in iterable:
                loop_env = Environment(parent=env)
                loop_env.define(stmt.var_name, item)
                try:
                    self.exec_block(stmt.body, loop_env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
            return

        if isinstance(stmt, BreakStmt):
            raise BreakSignal()

        if isinstance(stmt, ContinueStmt):
            raise ContinueSignal()

        if isinstance(stmt, FnDecl):
            param_names = [p.name for p in stmt.params]
            fn = Function(stmt.name, param_names, stmt.body, env)
            env.define(stmt.name, fn, is_const=True)
            return

        if isinstance(stmt, ReturnStmt):
            value = None
            if stmt.value is not None:
                value = self.eval_expr(stmt.value, env)
            raise ReturnSignal(value)

        if isinstance(stmt, ExprStmt):
            self.eval_expr(stmt.expr, env)
            return

        raise RuntimeError_Onyx(f"unknown statement: {type(stmt).__name__}")

    def load_module(self, name, env, line):
        if env.has(name):
            return

        if name in self._module_cache:
            env.define(name, self._module_cache[name], is_const=True)
            return

        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(os.getcwd(), "onyx_modules", f"{name}.onyx"),
            os.path.join(script_dir, "onyx_modules", f"{name}.onyx"),
        ]
        module_path = None
        for c in candidates:
            if os.path.exists(c):
                module_path = c
                break

        if module_path is None:
            raise RuntimeError_Onyx(
                f"[line {line}] module '{name}' not found in onyx_modules/"
            )

        tree = module_cache.load_cached(name, module_path)
        cache_hit = tree is not None

        if tree is None:
            with open(module_path, 'r', encoding='utf-8') as f:
                source = f.read()
            try:
                tokens = Lexer(source).tokenize()
                tree = Parser(tokens).parse()
            except LexerError as e:
                raise RuntimeError_Onyx(f"lexical error in module '{name}': {e}")
            except ParseError as e:
                raise RuntimeError_Onyx(f"syntax error in module '{name}': {e}")
            module_cache.save_cached(name, module_path, tree)

        if self.verbose:
            status = "cached" if cache_hit else "parsed"
            print(f"[onyx] loaded module '{name}' ({status})")

        mod_env = Environment(parent=self.globals)

        try:
            self.exec_block(tree.statements, mod_env)
        except ReturnSignal:
            raise RuntimeError_Onyx(f"return outside function in module '{name}'")
        except (BreakSignal, ContinueSignal):
            raise RuntimeError_Onyx(f"break/continue outside loop in module '{name}'")

        module = Module(name, mod_env)
        self._module_cache[name] = module
        env.define(name, module, is_const=True)

    def eval_expr(self, node, env):
        if isinstance(node, NumberLit):
            return node.value
        if isinstance(node, StringLit):
            return node.value
        if isinstance(node, BoolLit):
            return node.value
        if isinstance(node, NoneLit):
            return None

        if isinstance(node, Ident):
            return env.get(node.name, node.line)

        if isinstance(node, AssignExpr):
            value = self.eval_expr(node.value, env)
            env.set(node.name, value, node.line)
            return value

        if isinstance(node, BinOp):
            return self.eval_binop(node, env)

        if isinstance(node, UnaryOp):
            v = self.eval_expr(node.operand, env)
            if node.op == "-":
                return -self.to_number(v, node.line)
            if node.op == "!":
                return not self.truthy(v)
            raise RuntimeError_Onyx(f"unknown unary operator: {node.op}")

        if isinstance(node, CallExpr):
            return self.eval_call(node, env)

        if isinstance(node, ListLit):
            return [self.eval_expr(e, env) for e in node.elements]

        if isinstance(node, DictLit):
            result = {}
            for k, v in zip(node.keys, node.values):
                key = self.eval_expr(k, env)
                value = self.eval_expr(v, env)
                result[key] = value
            return result

        if isinstance(node, IndexExpr):
            target = self.eval_expr(node.target, env)
            index = self.eval_expr(node.index, env)
            return self.do_index(target, index, node.line)

        if isinstance(node, RangeExpr):
            start = self.eval_expr(node.start, env)
            end = self.eval_expr(node.end, env)
            if not isinstance(start, int) or not isinstance(end, int):
                raise RuntimeError_Onyx(f"[line {node.line}] range '..' expects integers")
            return list(range(start, end))

        if isinstance(node, MemberExpr):
            target = self.eval_expr(node.target, env)
            return self.get_member(target, node.member, node.line)

        raise RuntimeError_Onyx(f"unknown expression: {type(node).__name__}")

    def get_member(self, target, member, line):
        if isinstance(target, Module):
            if target.env.has(member):
                return target.env.get(member, line)
            raise RuntimeError_Onyx(
                f"[line {line}] member '{member}' not found in module '{target.name}'"
            )
        raise RuntimeError_Onyx(
            f"[line {line}] cannot access member '{member}' on {type(target).__name__}"
        )

    def do_index(self, target, index, line):
        if isinstance(target, (list, str)):
            if not isinstance(index, int):
                raise RuntimeError_Onyx(f"[line {line}] list index must be int")
            if index < 0:
                index += len(target)
            if index < 0 or index >= len(target):
                raise RuntimeError_Onyx(
                    f"[line {line}] index out of range: {index} (size {len(target)})"
                )
            return target[index]
        if isinstance(target, dict):
            if index not in target:
                raise RuntimeError_Onyx(f"[line {line}] key '{index}' not found in dict")
            return target[index]
        raise RuntimeError_Onyx(
            f"[line {line}] cannot index {type(target).__name__}"
        )

    def eval_binop(self, node, env):
        op = node.op

        if op == "and":
            left = self.eval_expr(node.left, env)
            if not self.truthy(left):
                return left
            return self.eval_expr(node.right, env)
        if op == "or":
            left = self.eval_expr(node.left, env)
            if self.truthy(left):
                return left
            return self.eval_expr(node.right, env)

        left = self.eval_expr(node.left, env)
        right = self.eval_expr(node.right, env)

        if op == "==":
            return left == right
        if op == "!=":
            return left != right

        if op in ("<", ">", "<=", ">="):
            if not self._comparable(left, right):
                raise RuntimeError_Onyx(
                    f"[line {node.line}] cannot compare {type(left).__name__} with {type(right).__name__}"
                )
            if op == "<":  return left < right
            if op == ">":  return left > right
            if op == "<=": return left <= right
            if op == ">=": return left >= right

        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return self.stringify(left) + self.stringify(right)
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            return self.to_number(left, node.line) + self.to_number(right, node.line)
        if op == "-":
            return self.to_number(left, node.line) - self.to_number(right, node.line)
        if op == "*":
            if isinstance(left, str) and isinstance(right, int):
                return left * right
            if isinstance(left, list) and isinstance(right, int):
                return left * right
            return self.to_number(left, node.line) * self.to_number(right, node.line)
        if op == "/":
            r = self.to_number(right, node.line)
            if r == 0:
                raise RuntimeError_Onyx(f"[line {node.line}] division by zero")
            return self.to_number(left, node.line) / r

        raise RuntimeError_Onyx(f"unknown operator: {op}")

    def eval_call(self, node, env):
        fn = self.eval_expr(node.callee, env)
        args = [self.eval_expr(a, env) for a in node.args]
        name = self.callee_name(node.callee)

        if isinstance(fn, Function):
            if len(args) != len(fn.param_names):
                raise RuntimeError_Onyx(
                    f"[line {node.line}] function '{name}' expects "
                    f"{len(fn.param_names)} arguments, got {len(args)}"
                )
            fn_env = Environment(parent=fn.closure)
            for pname, val in zip(fn.param_names, args):
                fn_env.define(pname, val)
            try:
                self.exec_block(fn.body, fn_env)
            except ReturnSignal as sig:
                return sig.value
            return None

        if callable(fn):
            try:
                return fn(*args)
            except RuntimeError_Onyx:
                raise
            except Exception as e:
                raise RuntimeError_Onyx(
                    f"[line {node.line}] error in '{name}': {e}"
                )

        raise RuntimeError_Onyx(f"[line {node.line}] '{name}' is not a function")

    def callee_name(self, node):
        if isinstance(node, Ident):
            return node.name
        if isinstance(node, MemberExpr):
            return f"{self.callee_name(node.target)}.{node.member}"
        return "<expr>"

    def truthy(self, value):
        if value is None: return False
        if value is False: return False
        if value == 0: return False
        if value == "": return False
        if isinstance(value, (list, dict)) and len(value) == 0: return False
        return True

    def to_number(self, value, line):
        if isinstance(value, bool):
            raise RuntimeError_Onyx(
                f"[line {line}] cannot use bool in arithmetic operation"
            )
        if isinstance(value, (int, float)):
            return value
        raise RuntimeError_Onyx(
            f"[line {line}] expected number, got {type(value).__name__} ({value!r})"
        )

    def _comparable(self, a, b):
        if isinstance(a, bool) or isinstance(b, bool):
            return False
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return True
        if isinstance(a, str) and isinstance(b, str):
            return True
        return False

    def stringify(self, value):
        if value is None: return "None"
        if value is True: return "true"
        if value is False: return "false"
        if isinstance(value, str): return value
        if isinstance(value, Function): return f"<function {value.name}>"
        if isinstance(value, Module): return f"<module {value.name}>"
        if isinstance(value, (list, dict)): return self.repr_onyx(value)
        return str(value)

    def repr_onyx(self, value):
        if value is None: return "None"
        if value is True: return "true"
        if value is False: return "false"
        if isinstance(value, str): return f'"{value}"'
        if isinstance(value, Function): return f"<function {value.name}>"
        if isinstance(value, Module): return f"<module {value.name}>"
        if isinstance(value, list):
            return "[" + ", ".join(self.repr_onyx(v) for v in value) + "]"
        if isinstance(value, dict):
            items = ", ".join(
                f"{self.repr_onyx(k)}: {self.repr_onyx(v)}"
                for k, v in value.items()
            )
            return "{" + items + "}"
        return str(value)