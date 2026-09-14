#!/usr/bin/env python3
"""
VIDO Basic compiler v0.1
Current target: VIDO Basic -> C -> GCC/Clang executable.

Supported in this first version:
- menu main() { ... }
- p.<text>..  (text output)
- int/float/double/char/string/bool variables
- assignment
- basic arithmetic expressions
- start / stop / junction condition blocks
- // single-line comments
- . statement terminator

Usage:
  python vido_compiler.py hello.vido
  python vido_compiler.py hello.vido -o hello
  python vido_compiler.py hello.vido --emit-c hello.c
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

TYPE_MAP = {
    "int": "int",
    "float": "float",
    "double": "double",
    "char": "char",
    "string": "char*",
    "bool": "int",
}

def strip_comments(src):
    # Remove // ... // multiline comments first.
    src = re.sub(r"//.*?//", "", src, flags=re.S)
    # Then remove ordinary single-line comments.
    src = re.sub(r"//[^\n]*", "", src)
    return src

def compile_expr(expr):
    expr = expr.strip()
    # VIDO boolean literals.
    expr = re.sub(r"\btrue\b", "1", expr, flags=re.I)
    expr = re.sub(r"\bfalse\b", "0", expr, flags=re.I)
    return expr

def parse_prints(src):
    # p.<text>.. ; text may contain spaces and newlines.
    out = []
    def repl(m):
        text = m.group(1)
        text = text.replace("\\", "\\\\").replace('"', '\\"')
        text = text.replace("\r", "").replace("\n", "\\n")
        out.append(f'    printf("{text}\\n");')
        return ""
    src = re.sub(r"p\.(.*?)\.\.", repl, src, flags=re.S)
    return src, out

def translate(src):
    src = strip_comments(src)
    src, print_lines = parse_prints(src)

    if not re.search(r"\bmenu\s+main\s*\(\s*\)", src):
        raise SyntaxError("VIDO program must contain: menu main()")

    # Extract body between the first { after menu main() and its matching }.
    m = re.search(r"\bmenu\s+main\s*\(\s*\)\s*\{", src)
    start = m.end()
    depth = 1
    i = start
    while i < len(src) and depth:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise SyntaxError("Unclosed { in menu main()")
    body = src[start:i-1]

    # Split VIDO statements at '.' outside quotes.
    statements = []
    buf, quote = "", None
    for ch in body:
        if ch in "\"'" and (not buf or buf[-1] != "\\"):
            quote = None if quote == ch else (ch if quote is None else quote)
        if ch == "." and quote is None:
            if buf.strip():
                statements.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        statements.append(buf.strip())

    c = [
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        "",
        "int main(void) {",
    ]

    # Put p. output at the beginning for this v0.1 compiler.
    # (A later parser will preserve exact statement order.)
    c.extend(print_lines)

    declared = set()

    for st in statements:
        st = st.strip()
        if not st:
            continue

        # Ignore braces left by block syntax in this early version.
        if st in ("{", "}"):
            continue

        # start(condition) { ... } — basic single-line condition support.
        mm = re.match(r"start\s*\((.*?)\)\s*\{(.*?)\}\s*$", st, flags=re.S)
        if mm:
            cond, inner = mm.groups()
            c.append(f"    if ({compile_expr(cond)}) {{")
            inner_parts = [x.strip() for x in re.split(r"\.(?=(?:[^\"']|\"[^\"]*\"|'[^']*')*$)", inner) if x.strip()]
            for p in inner_parts:
                if p.startswith("bye"):
                    c.append("        return 0;")
                else:
                    c.append("        " + compile_statement(p, declared))
            c.append("    }")
            continue

        c.append("    " + compile_statement(st, declared))

    c += [
        "    return 0;",
        "}",
        "",
    ]
    return "\n".join(c)

def compile_statement(st, declared):
    st = st.strip()

    # Variable declaration: type name = expression
    m = re.match(r"^(int|float|double|char|string|bool)\s+([A-Za-z_]\w*)\s*=\s*(.+)$", st, flags=re.S)
    if m:
        typ, name, expr = m.groups()
        declared.add(name)
        expr = compile_expr(expr)
        if typ == "string":
            if not (expr.startswith('"') and expr.endswith('"')):
                expr = f"(char*)({expr})"
            return f"char *{name} = {expr};"
        if typ == "bool":
            return f"int {name} = {expr};"
        return f"{TYPE_MAP[typ]} {name} = {expr};"

    # Declaration without initializer.
    m = re.match(r"^(int|float|double|char|string|bool)\s+([A-Za-z_]\w*)$", st)
    if m:
        typ, name = m.groups()
        declared.add(name)
        if typ == "string":
            return f"char *{name} = NULL;"
        return f"{TYPE_MAP[typ]} {name};"

    # Assignment.
    m = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.+)$", st, flags=re.S)
    if m:
        name, expr = m.groups()
        return f"{name} = {compile_expr(expr)};"

    if st == "bye":
        return "return 0;"

    raise SyntaxError(f"Unsupported VIDO statement: {st}")

def build(c_file, output):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        raise RuntimeError("GCC/Clang not found. Use --emit-c to generate C, or install a C compiler.")
    subprocess.run([cc, str(c_file), "-O2", "-o", str(output)], check=True)

def main():
    ap = argparse.ArgumentParser(description="VIDO Basic compiler v0.1")
    ap.add_argument("source", help="VIDO source (.vido)")
    ap.add_argument("-o", "--output", help="output executable name")
    ap.add_argument("--emit-c", help="write generated C source to this file")
    args = ap.parse_args()

    src_path = Path(args.source)
    if src_path.suffix.lower() != ".vido":
        print("Warning: VIDO source files normally use .vido", file=sys.stderr)

    try:
        c_text = translate(src_path.read_text(encoding="utf-8"))
        c_path = Path(args.emit_c) if args.emit_c else src_path.with_suffix(".c")
        c_path.write_text(c_text, encoding="utf-8")

        if args.output:
            build(c_path, Path(args.output))
            print(f"VIDO compiled: {args.output}")
        else:
            print(f"C generated: {c_path}")
            print("Use -o NAME to compile with GCC/Clang.")
    except (OSError, SyntaxError, RuntimeError, subprocess.CalledProcessError) as e:
        print(f"VIDO compiler error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
