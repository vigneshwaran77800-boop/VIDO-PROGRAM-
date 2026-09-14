# VIDO Basic Compiler — v0.1

This is the first working compiler scaffold for the VIDO language.

## Pipeline

VIDO `.vido` source -> generated C -> GCC/Clang -> executable

## Run

```bash
python vido_compiler.py hello.vido --emit-c hello.c
python vido_compiler.py hello.vido -o hello
```

The second command needs GCC or Clang installed.

## Current v0.1 support

- `menu main()`
- `p.<text>..`
- `int`, `float`, `double`, `char`, `string`, `bool`
- variable declarations and assignments
- arithmetic expressions
- `start(condition) { ... }` basic form
- `bye`
- `//` comments
- `.` statement terminator

Many VIDO features already designed (arrays, `mux`, `bank`, `multibank`, `alias`, `ulias`, `rename`, `random`, `abds()`, `length()`, `whole()`, etc.) are intentionally not implemented yet. They should be added one-by-one after the core parser is stabilized.
