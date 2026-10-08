# onyx.py
# Onyx Language CLI (package manager + runner)

import sys
import os
import re
import time
from lexer import Lexer, LexerError
from parser import Parser, ParseError
from typechecker import TypeChecker
from evaluator import Evaluator
from environment import RuntimeError_Onyx
import module_cache
import colors as col


VERSION = "0.4.0"


_POS_PATTERN = re.compile(r"\[line (\d+)(?:, col (\d+))?\]")


def extract_position(msg):
    m = _POS_PATTERN.search(msg)
    if not m:
        return 0, 0
    line = int(m.group(1))
    col = int(m.group(2)) if m.group(2) else 1
    return line, col


def clean_message(msg):
    return _POS_PATTERN.sub("", msg).strip()


def print_help():
    lines = [
        "",
        col.cyan("=============================================="),
        col.bold(col.cyan("         Onyx Language CLI v" + VERSION)),
        col.cyan("=============================================="),
        "",
        col.bold("Usage:"),
        "  python onyx.py <file.onyx>         run a file",
        "  python onyx.py run <file.onyx>     run a file (explicit)",
        "  python onyx.py check <file.onyx>   type-check without running",
        "  python onyx.py list                list installed modules",
        "  python onyx.py info <module>       show module info",
        "  python onyx.py new <project>       create a new project",
        "  python onyx.py cache               show cache statistics",
        "  python onyx.py clean               clear the module cache",
        "  python onyx.py version             show version",
        "  python onyx.py help                show this help",
        "",
        col.bold("Examples:"),
        "  " + col.dim("python onyx.py examples/hello.onyx"),
        "  " + col.dim("python onyx.py check examples/type_errors.onyx"),
        "  " + col.dim("python onyx.py info math"),
        "  " + col.dim("python onyx.py new myapp"),
        "  " + col.dim("python onyx.py clean"),
        "",
    ]
    print("\n".join(lines))


def run_file(filename):
    if not os.path.exists(filename):
        print(col.error_prefix() + "file not found: " + filename)
        return 1

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(col.error_prefix() + "cannot read file: " + str(e))
        return 1

    try:
        tokens = Lexer(source).tokenize()
    except LexerError as e:
        print(col.lexical_prefix() + str(e))
        return 1

    try:
        tree = Parser(tokens).parse()
    except ParseError as e:
        print(col.syntax_prefix() + str(e))
        return 1

    errors = TypeChecker().check(tree)
    if errors:
        print(col.type_prefix() + "type check failed (" + str(len(errors)) + " error(s)):")
        print("")
        for e in errors:
            print("  " + col.red("-") + " " + e)
        return 1

    verbose = os.environ.get("ONYX_VERBOSE") == "1"
    try:
        Evaluator(verbose=verbose).run(tree)
    except RuntimeError_Onyx as e:
        print(col.runtime_prefix() + str(e))
        return 1

    return 0


def check_file(filename):
    if not os.path.exists(filename):
        print(f"{filename}:1:1: error: file not found")
        return 1

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"{filename}:1:1: error: cannot read file: {e}")
        return 1

    try:
        tokens = Lexer(source).tokenize()
    except LexerError as e:
        msg = str(e)
        line, col = extract_position(msg)
        clean = clean_message(msg)
        print(f"{filename}:{line}:{col}: error: {clean}")
        return 1

    try:
        tree = Parser(tokens).parse()
    except ParseError as e:
        msg = str(e)
        line, col = extract_position(msg)
        clean = clean_message(msg)
        print(f"{filename}:{line}:{col}: error: {clean}")
        return 1

    errors = TypeChecker().check(tree)
    found_errors = False
    for e in errors:
        line, col = extract_position(e)
        clean = clean_message(e)
        print(f"{filename}:{line}:{col}: error: {clean}")
        found_errors = True

    if found_errors:
        return 1
    return 0


def find_modules_dir():
    if os.path.isdir("onyx_modules"):
        return "onyx_modules"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(script_dir, "onyx_modules")
    if os.path.isdir(p):
        return p
    return None


def read_module_metadata(path):
    metadata = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("// @"):
                    rest = stripped[4:].strip()
                    if ' ' in rest:
                        k, v = rest.split(' ', 1)
                        metadata[k] = v.strip()
                    else:
                        metadata[rest] = ""
                elif stripped.startswith("//"):
                    continue
                else:
                    break
    except Exception:
        pass
    return metadata


def cmd_version():
    print("")
    print("Onyx Language " + col.cyan("v" + VERSION))
    print(col.dim("Python " + sys.version.split()[0]))
    print(col.dim("Platform: " + sys.platform))
    print("")
    return 0


def cmd_list():
    d = find_modules_dir()
    if d is None:
        print(col.warning_prefix() + "onyx_modules/ not found")
        return 1

    files = sorted(f for f in os.listdir(d) if f.endswith(".onyx"))
    if not files:
        print(col.warning_prefix() + "no modules installed")
        return 0

    print("")
    print(col.bold("Installed modules (" + str(len(files)) + "):"))
    print("")
    for f in files:
        name = f[:-5]
        path = os.path.join(d, f)
        meta = read_module_metadata(path)
        desc = meta.get("description", "")
        version = meta.get("version", "")

        line = "  " + col.cyan("* " + name.ljust(12))
        if version:
            line += col.dim("  v" + version)
        if desc:
            line += col.dim("  - " + desc)
        print(line)
    print("")
    return 0


def cmd_info(name):
    d = find_modules_dir()
    if d is None:
        print(col.warning_prefix() + "onyx_modules/ not found")
        return 1

    path = os.path.join(d, name + ".onyx")
    if not os.path.exists(path):
        print(col.error_prefix() + "module '" + name + "' not found")
        return 1

    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()

    meta = read_module_metadata(path)

    exports_const = []
    exports_fn = []
    for line in source.splitlines():
        s = line.strip()
        if s.startswith("const "):
            rest = s[6:]
            name_part = rest.split('=', 1)[0].strip()
            name_part = "".join(c for c in name_part if c.isalnum() or c == '_')
            if name_part:
                exports_const.append(name_part)
        elif s.startswith("fn "):
            rest = s[3:].strip()
            p = rest.find('(')
            if p > 0:
                fn_name = rest[:p].strip()
                fn_name = "".join(c for c in fn_name if c.isalnum() or c == '_')
                if fn_name:
                    exports_fn.append(fn_name)

    size = os.path.getsize(path)
    line_count = len(source.splitlines())

    print("")
    print(col.bold("Module info: ") + col.cyan(name))
    print("")
    print("  " + col.dim("Path:        ") + path)
    print("  " + col.dim("Size:        ") + str(size) + " bytes")
    print("  " + col.dim("Lines:       ") + str(line_count))

    if 'description' in meta:
        print("  " + col.dim("Description: ") + meta['description'])
    if 'version' in meta:
        print("  " + col.dim("Version:     ") + col.green("v" + meta['version']))
    if 'author' in meta:
        print("  " + col.dim("Author:      ") + meta['author'])
    if 'license' in meta:
        print("  " + col.dim("License:     ") + meta['license'])

    if exports_const:
        print("")
        print("  " + col.yellow("Constants (" + str(len(exports_const)) + "):"))
        for c in exports_const:
            print("      " + col.yellow("* ") + c)

    if exports_fn:
        print("")
        print("  " + col.magenta("Functions (" + str(len(exports_fn)) + "):"))
        for fn in exports_fn:
            print("      " + col.magenta("* ") + fn)

    print("")
    return 0


def cmd_new(project_name):
    if os.path.exists(project_name):
        print(col.error_prefix() + "directory '" + project_name + "' already exists")
        return 1

    try:
        os.makedirs(project_name)
        os.makedirs(os.path.join(project_name, "onyx_modules"))
        os.makedirs(os.path.join(project_name, "examples"))
    except Exception as e:
        print(col.error_prefix() + "cannot create directories: " + str(e))
        return 1

    main_content = (
        "// New Onyx project\n"
        "// Run: python ../onyx.py main.onyx\n"
        "\n"
        "say(\"Hello from Onyx!\");\n"
        "\n"
        "set name = ask(\"What is your name? \");\n"
        "say(\"Welcome,\", name, \"!\");\n"
        "\n"
        "fn add(a, b) {\n"
        "    return a + b;\n"
        "}\n"
        "\n"
        "say(\"2 + 3 =\", add(2, 3));\n"
    )
    with open(os.path.join(project_name, "main.onyx"), 'w', encoding='utf-8') as f:
        f.write(main_content)

    readme_content = (
        "# " + project_name + "\n"
        "\n"
        "Onyx project.\n"
        "\n"
        "## Run\n"
        "\n"
        "```\n"
        "python ../onyx.py main.onyx\n"
        "```\n"
        "\n"
        "## License\n"
        "\n"
        "MIT\n"
    )
    with open(os.path.join(project_name, "README.md"), 'w', encoding='utf-8') as f:
        f.write(readme_content)

    gitignore_content = (
        "__pycache__/\n"
        "*.pyc\n"
        ".onyx_cache/\n"
        "onyx_test.txt\n"
    )
    with open(os.path.join(project_name, ".gitignore"), 'w', encoding='utf-8') as f:
        f.write(gitignore_content)

    print("")
    print(col.success_prefix() + "project '" + col.cyan(project_name) + "' created")
    print("")
    print("  " + col.cyan(project_name + "/"))
    print("     |-- main.onyx")
    print("     |-- README.md")
    print("     |-- .gitignore")
    print("     |-- onyx_modules/")
    print("     |-- examples/")
    print("")
    print(col.bold("To run:"))
    print("  " + col.dim("cd " + project_name))
    print("  " + col.dim("python ../onyx.py main.onyx"))
    print("")
    return 0


def cmd_cache():
    count, size = module_cache.cache_stats()
    print("")
    print(col.bold("Module cache:"))
    print("")
    if count == 0:
        print("  " + col.dim("(empty)"))
    else:
        print("  " + col.dim("Files: ") + col.cyan(str(count)))
        print("  " + col.dim("Size:  ") + col.cyan(str(size) + " bytes"))
        print("  " + col.dim("Dir:   ") + module_cache.CACHE_DIR)
    print("")
    return 0


def cmd_clean():
    count = module_cache.clear_cache()
    if count == 0:
        print(col.dim("cache is already empty"))
    else:
        print(col.success_prefix() + "cleared " + col.cyan(str(count)) + " cached file(s)")
    return 0


def main():
    args = sys.argv[1:]

    if not args:
        print_help()
        return 0

    first = args[0]

    if first in ("help", "--help", "-h"):
        print_help()
        return 0

    if first in ("version", "--version", "-v"):
        return cmd_version()

    if first == "run":
        if len(args) < 2:
            print(col.error_prefix() + "usage: python onyx.py run <file.onyx>")
            return 1
        return run_file(args[1])

    if first == "check":
        if len(args) < 2:
            print(col.error_prefix() + "usage: python onyx.py check <file.onyx>")
            return 1
        return check_file(args[1])

    if first == "list":
        return cmd_list()

    if first == "info":
        if len(args) < 2:
            print(col.error_prefix() + "usage: python onyx.py info <module>")
            return 1
        return cmd_info(args[1])

    if first == "new":
        if len(args) < 2:
            print(col.error_prefix() + "usage: python onyx.py new <project_name>")
            return 1
        return cmd_new(args[1])

    if first == "cache":
        return cmd_cache()

    if first == "clean":
        return cmd_clean()

    return run_file(first)


if __name__ == "__main__":
    sys.exit(main())