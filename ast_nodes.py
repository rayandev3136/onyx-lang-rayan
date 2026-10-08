# ast_nodes.py
# Abstract Syntax Tree node definitions

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TypeNode:
    name: str
    args: List
    line: int


@dataclass
class Param:
    name: str
    type_node: Optional[TypeNode]
    line: int


@dataclass
class Program:
    statements: List


@dataclass
class VarDecl:
    name: str
    type_annotation: Optional[TypeNode]
    value: object
    is_const: bool
    line: int
    has_value: bool = True


@dataclass
class UseStmt:
    module: str
    line: int

@dataclass
class IfStmt:
    condition: object
    then_block: List
    else_block: Optional[List]
    line: int

@dataclass
class WhileStmt:
    condition: object
    body: List
    line: int

@dataclass
class ForStmt:
    var_name: str
    iterable: object
    body: List
    line: int

@dataclass
class BreakStmt:
    line: int

@dataclass
class ContinueStmt:
    line: int

@dataclass
class FnDecl:
    name: str
    params: List[Param]
    return_type: Optional[TypeNode]
    body: List
    line: int

@dataclass
class ReturnStmt:
    value: Optional[object]
    line: int

@dataclass
class ExprStmt:
    expr: object
    line: int


@dataclass
class NumberLit:
    value: object
    line: int

@dataclass
class StringLit:
    value: str
    line: int

@dataclass
class BoolLit:
    value: bool
    line: int

@dataclass
class NoneLit:
    line: int

@dataclass
class Ident:
    name: str
    line: int

@dataclass
class BinOp:
    left: object
    op: str
    right: object
    line: int

@dataclass
class UnaryOp:
    op: str
    operand: object
    line: int

@dataclass
class CallExpr:
    callee: object
    args: List
    line: int

@dataclass
class AssignExpr:
    name: str
    value: object
    line: int

@dataclass
class ListLit:
    elements: List
    line: int

@dataclass
class DictLit:
    keys: List
    values: List
    line: int

@dataclass
class IndexExpr:
    target: object
    index: object
    line: int

@dataclass
class RangeExpr:
    start: object
    end: object
    line: int

@dataclass
class MemberExpr:
    target: object
    member: str
    line: int


def dump(node, indent=0):
    pad = "  " * indent

    if node is None:
        return f"{pad}None"

    if isinstance(node, (int, float, bool, str)):
        return f"{pad}{node!r}"

    if isinstance(node, list):
        if not node:
            return f"{pad}[]"
        lines = [f"{pad}["]
        for item in node:
            lines.append(dump(item, indent + 1))
        lines.append(f"{pad}]")
        return "\n".join(lines)

    if not hasattr(node, "__dataclass_fields__"):
        return f"{pad}{node!r}"

    name = type(node).__name__
    parts = []
    for fname in node.__dataclass_fields__:
        if fname == "line":
            continue
        val = getattr(node, fname)

        if val is None or isinstance(val, (int, float, bool, str)):
            parts.append(f"{fname}={val!r}")
        else:
            sub = dump(val, indent + 2)
            parts.append(f"{fname}=\n{sub}")

    if not parts:
        return f"{pad}{name}()"

    result = f"{pad}{name}(\n"
    for p in parts:
        result += f"{pad}  {p}\n"
    result = result[:-1] + f"\n{pad})"
    return result