# typechecker.py
# Static type checker

from ast_nodes import (
    Program, VarDecl, UseStmt, IfStmt, WhileStmt, ForStmt,
    BreakStmt, ContinueStmt, FnDecl, ReturnStmt, ExprStmt,
    NumberLit, StringLit, BoolLit, NoneLit, Ident, BinOp, UnaryOp,
    CallExpr, AssignExpr, ListLit, DictLit, IndexExpr, RangeExpr,
    MemberExpr,
)
from types_onyx import (
    Type, ANY, INT, FLOAT, STRING, BOOL, NONE_T, LIST, DICT,
    list_of, dict_of, is_numeric, is_compatible, unify,
)
from suggestions import find_similar


class FunctionSig:
    def __init__(self, param_types, return_type, param_names=None, variadic=False):
        self.param_types = param_types
        self.return_type = return_type
        self.param_names = param_names or []
        self.variadic = variadic

    def __str__(self):
        ps = ", ".join(str(p) for p in self.param_types)
        if self.variadic:
            ps += ", ..."
        return f"fn({ps}) -> {self.return_type}"


class TypeEnv:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def define(self, name, t):
        self.vars[name] = t

    def lookup(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None

    def all_names(self):
        names = set(self.vars.keys())
        if self.parent is not None:
            names.update(self.parent.all_names())
        return names


class TypeChecker:
    def __init__(self):
        self.errors = []
        self.current_return = ANY

    def check(self, program):
        env = TypeEnv()
        self._install_builtins(env)

        for stmt in program.statements:
            if isinstance(stmt, FnDecl):
                env.define(stmt.name, self._sig_of(stmt))

        for stmt in program.statements:
            self.check_stmt(stmt, env)

        return self.errors

    def _install_builtins(self, env):
        env.define("say", FunctionSig([], ANY, variadic=True))
        # ask is variadic and returns ANY (because type hint changes return type)
        env.define("ask", FunctionSig([], ANY, variadic=True))
        env.define("str", FunctionSig([ANY], STRING))
        env.define("int", FunctionSig([ANY], INT))
        env.define("float", FunctionSig([ANY], FLOAT))
        env.define("len", FunctionSig([ANY], INT))
        env.define("range", FunctionSig([INT], list_of(INT), variadic=True))
        env.define("push", FunctionSig([LIST, ANY], NONE_T))
        env.define("pop", FunctionSig([LIST], ANY))
        env.define("keys", FunctionSig([DICT], list_of(ANY)))
        env.define("values", FunctionSig([DICT], list_of(ANY)))
        env.define("has", FunctionSig([DICT, ANY], BOOL))
        env.define("native", FunctionSig([STRING], ANY))

    def _sig_of(self, fn_decl):
        ptypes = []
        pnames = []
        for p in fn_decl.params:
            pnames.append(p.name)
            if p.type_node is not None:
                ptypes.append(self._type_from_node(p.type_node))
            else:
                ptypes.append(ANY)
        rtype = ANY
        if fn_decl.return_type is not None:
            rtype = self._type_from_node(fn_decl.return_type)
        return FunctionSig(ptypes, rtype, pnames)

    def _type_from_node(self, node):
        if node is None:
            return ANY
        name = node.name
        args = [self._type_from_node(a) for a in node.args]

        if name == "int":    return INT
        if name == "float":  return FLOAT
        if name == "string": return STRING
        if name == "bool":   return BOOL
        if name == "none":   return NONE_T
        if name == "any":    return ANY
        if name == "list":
            return list_of(args[0]) if args else LIST
        if name == "dict":
            if len(args) >= 2:
                return dict_of(args[0], args[1])
            return DICT
        return ANY

    def check_block(self, stmts, env):
        for s in stmts:
            self.check_stmt(s, env)

    def check_stmt(self, stmt, env):
        if isinstance(stmt, VarDecl):
            if stmt.has_value:
                value_type = self.infer(stmt.value, env)
                if stmt.type_annotation is not None:
                    declared = self._type_from_node(stmt.type_annotation)
                    if not is_compatible(value_type, declared):
                        self.errors.append(
                            f"[line {stmt.line}] cannot assign value of type "
                            f"{value_type} to variable '{stmt.name}' of type {declared}"
                        )
                    env.define(stmt.name, declared)
                else:
                    env.define(stmt.name, value_type)
            else:
                if stmt.type_annotation is None:
                    self.errors.append(
                        f"[line {stmt.line}] variable '{stmt.name}' "
                        f"must have a value or explicit type"
                    )
                    env.define(stmt.name, ANY)
                else:
                    declared = self._type_from_node(stmt.type_annotation)
                    env.define(stmt.name, declared)
            return

        if isinstance(stmt, UseStmt):
            env.define(stmt.module, ANY)
            return

        if isinstance(stmt, FnDecl):
            new_env = TypeEnv(parent=env)
            for p in stmt.params:
                if p.type_node is not None:
                    new_env.define(p.name, self._type_from_node(p.type_node))
                else:
                    new_env.define(p.name, ANY)
            saved = self.current_return
            self.current_return = (
                self._type_from_node(stmt.return_type)
                if stmt.return_type is not None else ANY
            )
            self.check_block(stmt.body, new_env)
            self.current_return = saved
            return

        if isinstance(stmt, IfStmt):
            self.infer(stmt.condition, env)
            self.check_block(stmt.then_block, TypeEnv(parent=env))
            if stmt.else_block:
                self.check_block(stmt.else_block, TypeEnv(parent=env))
            return

        if isinstance(stmt, WhileStmt):
            self.infer(stmt.condition, env)
            self.check_block(stmt.body, TypeEnv(parent=env))
            return

        if isinstance(stmt, ForStmt):
            it_type = self.infer(stmt.iterable, env)
            element_type = ANY
            if it_type.name == "list" and it_type.args:
                element_type = it_type.args[0]
            elif it_type == STRING:
                element_type = STRING
            loop_env = TypeEnv(parent=env)
            loop_env.define(stmt.var_name, element_type)
            self.check_block(stmt.body, loop_env)
            return

        if isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                rt = self.infer(stmt.value, env)
                if not is_compatible(rt, self.current_return):
                    self.errors.append(
                        f"[line {stmt.line}] return type {rt} does not match "
                        f"expected type {self.current_return}"
                    )
            return

        if isinstance(stmt, ExprStmt):
            self.infer(stmt.expr, env)
            return

        if isinstance(stmt, (BreakStmt, ContinueStmt)):
            return

    def _var_not_found(self, name, env, line):
        similar = find_similar(name, list(env.all_names()))
        msg = f"[line {line}] variable '{name}' is not defined"
        if similar:
            msg += " -- did you mean: " + ", ".join("'" + s + "'" for s in similar) + "?"
        self.errors.append(msg)

    def _fn_not_found(self, name, env, line):
        fns = [n for n in env.all_names() if isinstance(env.lookup(n), FunctionSig)]
        similar = find_similar(name, fns)
        msg = f"[line {line}] function '{name}' is not defined"
        if similar:
            msg += " -- did you mean: " + ", ".join("'" + s + "'" for s in similar) + "?"
        self.errors.append(msg)

    def infer(self, node, env):
        if isinstance(node, NumberLit):
            if isinstance(node.value, float):
                return FLOAT
            return INT

        if isinstance(node, StringLit):
            return STRING
        if isinstance(node, BoolLit):
            return BOOL
        if isinstance(node, NoneLit):
            return NONE_T

        if isinstance(node, Ident):
            t = env.lookup(node.name)
            if t is None:
                self._var_not_found(node.name, env, node.line)
                return ANY
            if isinstance(t, FunctionSig):
                return ANY
            return t

        if isinstance(node, AssignExpr):
            value_type = self.infer(node.value, env)
            existing = env.lookup(node.name)
            if existing is None:
                self._var_not_found(node.name, env, node.line)
            elif isinstance(existing, FunctionSig):
                self.errors.append(
                    f"[line {node.line}] cannot assign to function '{node.name}'"
                )
            elif not is_compatible(value_type, existing):
                self.errors.append(
                    f"[line {node.line}] cannot assign {value_type} to "
                    f"'{node.name}' of type {existing}"
                )
            return value_type

        if isinstance(node, BinOp):
            lt = self.infer(node.left, env)
            rt = self.infer(node.right, env)
            return self._binop_type(node.op, lt, rt, node.line)

        if isinstance(node, UnaryOp):
            self.infer(node.operand, env)
            if node.op == "!":
                return BOOL
            return ANY

        if isinstance(node, CallExpr):
            if isinstance(node.callee, Ident):
                name = node.callee.name
                sig = env.lookup(name)
                if sig is None:
                    self._fn_not_found(name, env, node.line)
                    return ANY
                if not isinstance(sig, FunctionSig):
                    self.errors.append(
                        f"[line {node.line}] '{name}' is not a function"
                    )
                    return ANY
                arg_types = [self.infer(a, env) for a in node.args]
                if sig.variadic:
                    for i, at in enumerate(arg_types):
                        if i < len(sig.param_types):
                            pt = sig.param_types[i]
                            if not is_compatible(at, pt):
                                self.errors.append(
                                    f"[line {node.line}] argument {i+1} to '{name}': "
                                    f"expected {pt}, got {at}"
                                )
                else:
                    if len(arg_types) != len(sig.param_types):
                        self.errors.append(
                            f"[line {node.line}] function '{name}' expects "
                            f"{len(sig.param_types)} arguments, got {len(arg_types)}"
                        )
                    else:
                        for i, (at, pt) in enumerate(zip(arg_types, sig.param_types)):
                            if not is_compatible(at, pt):
                                self.errors.append(
                                    f"[line {node.line}] argument {i+1} to '{name}': "
                                    f"expected {pt}, got {at}"
                                )
                return sig.return_type
            else:
                for a in node.args:
                    self.infer(a, env)
                self.infer(node.callee, env)
                return ANY

        if isinstance(node, ListLit):
            if not node.elements:
                return LIST
            elem_types = [self.infer(e, env) for e in node.elements]
            unified = elem_types[0]
            for t in elem_types[1:]:
                unified = unify(unified, t)
            if unified == ANY:
                return LIST
            return list_of(unified)

        if isinstance(node, DictLit):
            if not node.keys:
                return DICT
            kt = self.infer(node.keys[0], env)
            vt = self.infer(node.values[0], env)
            for k in node.keys[1:]:
                kt = unify(kt, self.infer(k, env))
            for v in node.values[1:]:
                vt = unify(vt, self.infer(v, env))
            if kt == ANY and vt == ANY:
                return DICT
            return dict_of(kt, vt)

        if isinstance(node, IndexExpr):
            target = self.infer(node.target, env)
            self.infer(node.index, env)
            if target.name == "list" and target.args:
                return target.args[0]
            if target == STRING:
                return STRING
            if target.name == "dict" and len(target.args) >= 2:
                return target.args[1]
            return ANY

        if isinstance(node, RangeExpr):
            self.infer(node.start, env)
            self.infer(node.end, env)
            return list_of(INT)

        if isinstance(node, MemberExpr):
            self.infer(node.target, env)
            return ANY

        return ANY

    def _binop_type(self, op, lt, rt, line):
        if op in ("and", "or"):
            return ANY if (lt == ANY or rt == ANY) else BOOL

        if op in ("==", "!="):
            return BOOL
        if op in ("<", ">", "<=", ">="):
            if lt == ANY or rt == ANY:
                return BOOL
            if is_numeric(lt) and is_numeric(rt):
                return BOOL
            if lt == STRING and rt == STRING:
                return BOOL
            self.errors.append(
                f"[line {line}] cannot compare {lt} with {rt}"
            )
            return BOOL

        if op == "+":
            if lt == ANY or rt == ANY:
                return ANY
            if lt == STRING or rt == STRING:
                return STRING
            if lt.name == "list" and rt.name == "list":
                return lt if lt.args else rt
            if is_numeric(lt) and is_numeric(rt):
                return FLOAT if (lt == FLOAT or rt == FLOAT) else INT
            self.errors.append(f"[line {line}] cannot add {lt} and {rt}")
            return ANY

        if op == "-":
            if lt == ANY or rt == ANY:
                return ANY
            if is_numeric(lt) and is_numeric(rt):
                return FLOAT if (lt == FLOAT or rt == FLOAT) else INT
            self.errors.append(f"[line {line}] cannot subtract {rt} from {lt}")
            return ANY

        if op == "*":
            if lt == ANY or rt == ANY:
                return ANY
            if lt == STRING and rt == INT:
                return STRING
            if lt == INT and rt == STRING:
                return STRING
            if lt.name == "list" and rt == INT:
                return lt
            if is_numeric(lt) and is_numeric(rt):
                return FLOAT if (lt == FLOAT or rt == FLOAT) else INT
            self.errors.append(f"[line {line}] cannot multiply {lt} by {rt}")
            return ANY

        if op == "/":
            if lt == ANY or rt == ANY:
                return FLOAT
            if is_numeric(lt) and is_numeric(rt):
                return FLOAT
            self.errors.append(f"[line {line}] cannot divide {lt} by {rt}")
            return FLOAT

        return ANY