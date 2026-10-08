# types_onyx.py
# Onyx type system

from dataclasses import dataclass


@dataclass(frozen=True)
class Type:
    name: str
    args: tuple = ()

    def __str__(self):
        if self.args:
            inner = ", ".join(str(a) for a in self.args)
            return f"{self.name}[{inner}]"
        return self.name


ANY    = Type("any")
INT    = Type("int")
FLOAT  = Type("float")
STRING = Type("string")
BOOL   = Type("bool")
NONE_T = Type("none")
LIST   = Type("list")
DICT   = Type("dict")


def list_of(t):
    return Type("list", (t,))

def dict_of(k, v):
    return Type("dict", (k, v))


def is_numeric(t):
    return t in (INT, FLOAT)


def is_compatible(actual, expected):
    if expected == ANY or actual == ANY:
        return True
    if actual == expected:
        return True
    if expected == FLOAT and actual == INT:
        return True
    if actual.name == expected.name == "list":
        if not expected.args or not actual.args:
            return True
        return is_compatible(actual.args[0], expected.args[0])
    if actual.name == expected.name == "dict":
        if not expected.args or not actual.args:
            return True
        if len(actual.args) >= 2 and len(expected.args) >= 2:
            return (is_compatible(actual.args[0], expected.args[0])
                    and is_compatible(actual.args[1], expected.args[1]))
        return True
    return False


def unify(a, b):
    if a == ANY:
        return b
    if b == ANY:
        return a
    if a == b:
        return a
    if {a, b} == {INT, FLOAT}:
        return FLOAT
    return ANY