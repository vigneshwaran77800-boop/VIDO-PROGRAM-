#!/usr/bin/env python3
import argparse, re, shutil, subprocess, sys
from pathlib import Path

TYPE_MAP = {"int":"int","float":"float","double":"double","char":"char","string":"char*","bool":"int"}

def strip_comments(src):
    src = re.sub(r"//.*?//", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)

def compile_expr(expr):
    expr = re.sub(r"\btrue\b", "1", expr.strip(), flags=re.I)
    expr = re.sub(r"\bfalse\b", "0", expr, flags=re.I)
    return expr

def parse_prints(src):
    out = []
    def repl(m):
        text = m.group(1).replace("\\","\\\\").replace('"','\\"')
        text = text.replace("\r","").replace("\n","\\n")
        out.append(f'    printf("{text}\\n");')
        return ""
    return re.sub(r"p\.(.*?)\.\.", repl, src, flags=re.S), out

def compile_statement(st, declared):
    st = st.strip()
    m = re.match(r"^(int|float|double|char|string|bool)\s+([A-Za-z_]\w*)\s*=\s*(.+)$", st, flags=re.S)
    if m:
        typ, name, expr = m.groups()
        declared.add(name)
        expr = compile_expr(expr)
        if typ == "string":
            return f'char *{name} = {expr};'
        return f'{TYPE_MAP[typ]} {name} = {expr};'
    m = re.match(r"^(int|float|double|char|string|bool)\s+([A-Za-z_]\w*)$", st)
    if m:
        typ, name = m.groups()
        declared.add(name)
        return f'{TYPE_MAP[typ]} {name};'
    m = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.+)$", st, flags=re.S)
    if m:
        name, expr = m.groups()
        return f"{name} = {compile_expr(expr)};"
    if st == "bye":
        return "return 0;"
    raise SyntaxError(f"Unsupported VIDO statement: {st}")

def translate(src):
    src = strip_comments(src)
    use_math = bool(re.search(r"(?m)^\s*@math\.com\s*$", src))
    src = re.sub(r"(?m)^\s*@math\.com\s*$\n?", "", src)
    if not re.search(r"\bmenu\s+main\s*\(\s*\)", src):
        raise SyntaxError("VIDO program must contain: menu main()")
    src, print_lines = parse_prints(src)
    m = re.search(r"\bmenu\s+main\s*\(\s*\)\s*\{", src)
    start, depth, i = m.end(), 1, m.end()
    while i < len(src) and depth:
        if src[i] == "{": depth += 1
        elif src[i] == "}": depth -= 1
        i += 1
    if depth:
        raise SyntaxError("Unclosed { in menu main()")
    body = src[start:i-1]
    statements, buf, quote = [], "", None
    for ch in body:
        if ch in "\"'" and (not buf or buf[-1] != "\\"):
            quote = None if quote == ch else (ch if quote is None else quote)
        if ch == "." and quote is None:
            if buf.strip(): statements.append(buf.strip())
            buf = ""
        else: buf += ch
    if buf.strip(): statements.append(buf.strip())

    c = ["#include <stdio.h>", "#include <stdlib.h>", "#include <string.h>"]
    if use_math: c.append("#include <math.h>")
    c += ["", "int main(void) {"]
    c.extend(print_lines)
    declared = set()
    for st in statements:
        if st:
            c.append("    " + compile_statement(st, declared))
    c += ["    return 0;", "}", ""]
    return "\n".join(c), use_math

def build(c_file, output, use_math=False):
    cc = shutil.which("clang") or shutil.which("gcc")
    if not cc: raise RuntimeError("Clang/GCC not found. Install clang.")
    cmd = [cc, str(c_file), "-O2", "-o", str(output)]
    if use_math: cmd.append("-lm")
    subprocess.run(cmd, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("-o","--output")
    ap.add_argument("--emit-c")
    args = ap.parse_args()
    src = Path(args.source)
    try:
        c_text, use_math = translate(src.read_text(encoding="utf-8"))
        c_path = Path(args.emit_c) if args.emit_c else src.with_suffix(".c")
        c_path.write_text(c_text, encoding="utf-8")
        if args.output:
            build(c_path, Path(args.output), use_math)
            print(f"VIDO compiled: {args.output}")
        else:
            print(f"C generated: {c_path}")
    except Exception as e:
        print(f"VIDO compiler error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
