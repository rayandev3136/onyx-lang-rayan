// Onyx Playground

let pyodide = null;
let ready = false;

const RUNTIME_FILES = [
    'tokens.py',
    'lexer.py',
    'ast_nodes.py',
    'parser.py',
    'types_onyx.py',
    'typechecker.py',
    'environment.py',
    'suggestions.py',
    'evaluator.py',
    'module_cache.py',
    'colors.py',
];

const MODULE_FILES = [
    'math.onyx',
    'string.onyx',
    'random.onyx',
    'io.onyx',
    'list.onyx',
    'dict.onyx',
    'time.onyx',
    'os.onyx',
];

const EXAMPLES = {
    hello: `// Hello World in Onyx

say("Hello, Onyx!");

set name = "world";
say("Hello,", name);

fn greet(who) {
    return "Hi, " + who + "!";
}

say(greet("Onyx"));`,

    math: `// Math demo
use math;

say("PI =", math.pi);
say("sqrt(16) =", math.sqrt(16));
say("2^10 =", math.pow(2, 10));

fn area(r) {
    return math.pi * r * r;
}

for r in 1..4 {
    say("Area of r=", r, " is", math.round(area(r)));
}`,

    fib: `// Fibonacci
fn fib(n) {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

for i in 0..10 {
    say("fib(", i, ") =", fib(i));
}`,

    fizzbuzz: `// FizzBuzz
for i in 1..21 {
    if (i - (i / 3) * 3 == 0 and i - (i / 5) * 5 == 0) {
        say("FizzBuzz");
    } else if (i - (i / 3) * 3 == 0) {
        say("Fizz");
    } else if (i - (i / 5) * 5 == 0) {
        say("Buzz");
    } else {
        say(i);
    }
}`,

    string: `// String playground
use string;

set text = "  Onyx is a programming language  ";

say("Original: [" + text + "]");
say("Trimmed:  [" + string.strip(text) + "]");
say("Upper:    " + string.upper(text));
say("Lower:    " + string.lower(text));
say("Length:   " + str(string.length(text)));

set words = string.split(string.strip(text), " ");
say("Words:");
for w in words {
    say("  -", w);
}

say(string.join(words, " | "));`,
};

// ============================================================
//   Helpers
// ============================================================

const out = () => document.getElementById('output');

function log(msg) {
    console.log('[onyx]', msg);
    out().textContent += msg + '\n';
}

function logError(msg) {
    console.error('[onyx]', msg);
    out().textContent += 'ERROR: ' + msg + '\n';
    out().classList.add('error');
}

function setStatus(text) {
    document.getElementById('status').textContent = text;
    console.log('[onyx-status]', text);
}

// ============================================================
//   Init
// ============================================================

async function init() {
    out().textContent = '';
    setStatus('Starting...');
    log('=== Onyx Playground ===');
    log('Loading Pyodide...');

    try {
        if (typeof loadPyodide === 'undefined') {
            throw new Error('loadPyodide not defined. pyodide.js failed to load.');
        }

        const indexURL = window.ONYX_PYODIDE_INDEX;
        log('  indexURL: ' + indexURL);

        pyodide = await loadPyodide({ indexURL: indexURL });
        log('  Pyodide initialized');
        setStatus('Loading Onyx runtime...');

        // Load runtime .py files
        for (const f of RUNTIME_FILES) {
            const res = await fetch('runtime/' + f);
            if (!res.ok) throw new Error('HTTP ' + res.status + ' fetching runtime/' + f);
            const content = await res.text();
            pyodide.FS.writeFile('/home/pyodide/' + f, content);
        }
        log('  Runtime files loaded (' + RUNTIME_FILES.length + ')');

        // Create modules dir
        try {
            pyodide.FS.mkdir('/home/pyodide/onyx_modules');
        } catch (e) { /* exists */ }

        // Load .onyx modules
        for (const f of MODULE_FILES) {
            const res = await fetch('modules/' + f);
            if (!res.ok) throw new Error('HTTP ' + res.status + ' fetching modules/' + f);
            const content = await res.text();
            pyodide.FS.writeFile('/home/pyodide/onyx_modules/' + f, content);
        }
        log('  Modules loaded (' + MODULE_FILES.length + ')');

        // Setup cwd and path
        pyodide.runPython(`
import os, sys
os.chdir('/home/pyodide')
if '/home/pyodide' not in sys.path:
    sys.path.insert(0, '/home/pyodide')
        `);
        log('  Working dir set');

        // Test imports
        pyodide.runPython(`
from lexer import Lexer
from parser import Parser
from typechecker import TypeChecker
from evaluator import Evaluator
from environment import RuntimeError_Onyx
        `);
        log('  Imports OK');

        // Redirect Python stdout to output panel
        pyodide.setStdout({
            batched: (s) => {
                out().textContent += s + '\n';
            }
        });

        ready = true;
        document.getElementById('run-btn').disabled = false;
        setStatus('Ready.');

        out().textContent = '';
        loadFromUrl();

    } catch (err) {
        logError(err.message || String(err));
        console.error(err);
        setStatus('Failed: ' + (err.message || err));
    }
}

// ============================================================
//   Run
// ============================================================

async function runCode() {
    if (!ready) {
        logError('Runtime not ready.');
        return;
    }

    const code = document.getElementById('editor').value;

    out().textContent = '';
    out().classList.remove('error');

    pyodide.FS.writeFile('/home/pyodide/user_code.onyx', code);

    try {
        await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, '/home/pyodide')

from lexer import Lexer, LexerError
from parser import Parser, ParseError
from typechecker import TypeChecker
from evaluator import Evaluator
from environment import RuntimeError_Onyx

with open('user_code.onyx', 'r', encoding='utf-8') as f:
    source = f.read()

try:
    tokens = Lexer(source).tokenize()
    tree = Parser(tokens).parse()
    errors = TypeChecker().check(tree)
    if errors:
        print("Type check failed (" + str(len(errors)) + " error(s)):")
        for e in errors:
            print("  - " + e)
    else:
        Evaluator().run(tree)
except (LexerError, ParseError) as e:
    print("Error: " + str(e))
except RuntimeError_Onyx as e:
    print("Runtime error: " + str(e))
except Exception as e:
    import traceback
    print("Unexpected error: " + str(e))
    traceback.print_exc()
        `);
    } catch (err) {
        logError(err.message || String(err));
        if (err.stack) log(err.stack);
    }
}

// ============================================================
//   Share / URL
// ============================================================

function encodeCode(code) {
    return btoa(unescape(encodeURIComponent(code)));
}

function decodeCode(b64) {
    return decodeURIComponent(escape(atob(b64)));
}

function shareLink() {
    const code = document.getElementById('editor').value;
    const url = location.origin + location.pathname + '#code=' + encodeCode(code);

    if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => {
            alert('Link copied to clipboard!');
        }).catch(() => {
            prompt('Copy this link:', url);
        });
    } else {
        prompt('Copy this link:', url);
    }
}

function loadFromUrl() {
    const hash = location.hash;
    const prefix = '#code=';
    if (hash.startsWith(prefix)) {
        try {
            const code = decodeCode(hash.slice(prefix.length));
            document.getElementById('editor').value = code;
            return;
        } catch (e) {
            console.error('bad share link', e);
        }
    }
    document.getElementById('editor').value = EXAMPLES.hello;
}

// ============================================================
//   Events
// ============================================================

document.getElementById('run-btn').addEventListener('click', runCode);

document.getElementById('clear-btn').addEventListener('click', () => {
    out().textContent = '';
    out().classList.remove('error');
});

document.getElementById('share-btn').addEventListener('click', shareLink);

document.getElementById('examples').addEventListener('change', (e) => {
    const key = e.target.value;
    if (key && EXAMPLES[key]) {
        document.getElementById('editor').value = EXAMPLES[key];
    }
    e.target.value = '';
});

document.getElementById('editor').addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runCode();
    }
});

// Start
init();