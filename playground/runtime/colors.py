# colors.py
# ANSI terminal colors

import os
import sys


def _supports_color():
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


COLORS_ENABLED = _supports_color() or os.environ.get("ONYX_COLORS") == "1"


def _c(code, text):
    if not COLORS_ENABLED:
        return text
    return "\033[" + code + "m" + text + "\033[0m"


def red(text):     return _c("31;1", text)
def green(text):   return _c("32;1", text)
def yellow(text):  return _c("33;1", text)
def blue(text):    return _c("34;1", text)
def magenta(text): return _c("35;1", text)
def cyan(text):    return _c("36;1", text)
def bold(text):    return _c("1", text)
def dim(text):     return _c("2", text)


def error_prefix():   return red("error: ")
def warning_prefix(): return yellow("warning: ")
def info_prefix():    return blue("info: ")
def success_prefix(): return green("[OK] ")
def lexical_prefix(): return red("lexical error: ")
def syntax_prefix():  return red("syntax error: ")
def type_prefix():    return red("type error: ")
def runtime_prefix(): return red("runtime error: ")