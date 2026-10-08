# Changelog

All notable changes to Onyx will be documented in this file.

## [0.4.0] - 2026-10-08

### Added
- Static type checker with error suggestions
- 8 built-in modules: math, string, random, io, list, dict, time, os
- Module caching (.onyx_cache/) for fast reloading
- CLI: run, check, list, info, new, cache, clean, version, help
- Interactive REPL with AST display and shared-state commands
- VS Code extension: syntax highlighting, error markers
- Empty variable declarations: `set x: int;`
- Typed input: `ask("Age:", "int")`
- Smart typo suggestions ("did you mean ...?")

### Changed
- All error messages are in English (better terminal rendering)

### Fixed
- Module loading path resolution
- Division by zero now gives a clear error
- String/dict display with proper quoting

## [0.3.0] - 2026-09-20

### Added
- Type system (int, float, string, bool, list, dict)
- Type annotations: `set x: int = 5;`
- Functions with typed parameters: `fn add(a: int, b: int) -> int`

## [0.2.0] - 2026-09-01

### Added
- Lists `[...]` and dicts `{...}`
- Indexing `list[0]`
- for loops: `for i in 0..10 { }`
- break / continue
- First module system: `use math;`

## [0.1.0] - 2026-08-15

### Added
- Initial release
- Variables, constants, functions
- if / else / while
- Basic arithmetic
- Comments