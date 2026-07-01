"""specgen: statically extract the spec/case/rule/link markers from Python
sources into spec.json — the artifact ccr's SpecBuilder consumes.

It parses with `ast` and never imports or runs the target code, so the markers
being no-ops is irrelevant: extraction is purely syntactic. Each entry is keyed
by its symbol-id `<relpath>::<qualname>` (qualname = `func`, `Class.method`, or a
`Class` itself for class-level markers — matching the symbol-id contract). Each
entry also carries `fqn` (the dotted import path, e.g. `pkg.mod.Class`) when
the module is importable — the location-independent id for cross-repo references.

CLI:  python -m spec_case.specgen <src-dir> [-o spec.json] [--root <repo-root>] [--check]
      --check compares against -o and exits 1 if the committed spec.json drifted
      from the markers (renamed/removed symbol, changed marker) — a CI gate.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

_MARKERS = {"spec", "case", "link", "rule"}


def _marker_name(dec: ast.expr) -> str | None:
    """The marker name of a decorator call, if it is one of ours — handles
    @spec(...) (Name) and @m.spec(...) (Attribute). Bare @spec (no call) is
    ignored: all our markers take arguments."""
    if isinstance(dec, ast.Call):
        f = dec.func
        if isinstance(f, ast.Name) and f.id in _MARKERS:
            return f.id
        if isinstance(f, ast.Attribute) and f.attr in _MARKERS:
            return f.attr
    return None


def _str(node: ast.expr | None) -> str:
    """A string literal's value, whitespace-collapsed; "" for anything else
    (specgen only reads literals — no evaluation)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return " ".join(node.value.split())
    return ""


def _arg(call: ast.Call, i: int) -> ast.expr | None:
    return call.args[i] if i < len(call.args) else None


def _kw(call: ast.Call, name: str) -> ast.expr | None:
    return next((k.value for k in call.keywords if k.arg == name), None)


def _entry_for(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> dict | None:
    """Build the spec.json entry from a function's or class's decorators, or None
    if it carries no markers. Classes carry the same decorator_list, so a @rule on
    a class (a type-wide usage constraint, e.g. "per-request only") is extracted
    just like a function's."""
    spec_text = ""
    cases: list[dict] = []
    links: list[str] = []
    rules: list[str] = []
    for dec in node.decorator_list:
        name = _marker_name(dec)
        if name is None:
            continue
        assert isinstance(dec, ast.Call)  # _marker_name only matches Calls
        if name == "spec":
            spec_text = _str(_arg(dec, 0))
        elif name == "case":
            cid = _str(_arg(dec, 0))
            if not cid:
                continue
            c: dict = {"id": cid}
            for key, node in (
                ("desc", _arg(dec, 1)),
                ("input", _kw(dec, "input")),
                ("expect", _kw(dec, "expect")),
                ("forbid", _kw(dec, "forbid")),
            ):
                if (v := _str(node)):
                    c[key] = v
            cases.append(c)
        elif name == "link":
            if (ref := _str(_arg(dec, 0))):
                links.append(ref)
        elif name == "rule":
            if (text := _str(_arg(dec, 0))):
                rules.append(text)

    if not (spec_text or cases or links or rules):
        return None
    entry: dict = {"cases": cases}  # schema requires `cases` (may be empty)
    if spec_text:
        entry["spec"] = spec_text
    if links:
        entry["links"] = links
    if rules:
        entry["rules"] = rules
    return entry


def _emit(out: dict, entry: dict | None, relpath: str, qual: str, module_prefix: str) -> None:
    """Record one symbol's entry under its symbol-id (<relpath>::qual), attaching
    the dotted fqn (module_prefix.qual) when the module is importable."""
    if entry is None:
        return
    if module_prefix:
        entry["fqn"] = f"{module_prefix}.{qual}"
    out[f"{relpath}::{qual}"] = entry


def _visit(node: ast.AST, stack: list[str], relpath: str, out: dict, module_prefix: str) -> None:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _emit(out, _entry_for(child), relpath, ".".join(stack + [child.name]), module_prefix)
            # nested functions don't get symbol-ids (binding is top-level funcs +
            # class methods, matching ccr's splitter), so don't descend into one.
        elif isinstance(child, ast.ClassDef):
            # A class's own markers bind to the class symbol-id (<relpath>::Class) —
            # e.g. @rule on the class is a type-wide usage constraint, surfaced when
            # a diff references the type.
            _emit(out, _entry_for(child), relpath, ".".join(stack + [child.name]), module_prefix)
            _visit(child, stack + [child.name], relpath, out, module_prefix)


def _module_prefix(path: Path) -> str:
    """The dotted importable module for a .py file, from its __init__.py package
    chain (common/middleware/trace.py -> common.middleware.trace) — the prefix of
    each symbol's fqn. Best-effort: a file not inside a package (no
    __init__.py above it) yields just its module stem."""
    parts: list[str] = [] if path.stem == "__init__" else [path.stem]
    d = path.parent
    while (d / "__init__.py").exists():
        parts.append(d.name)
        d = d.parent
    parts.reverse()
    return ".".join(parts)


def extract_file(src: str, relpath: str, module_prefix: str = "") -> dict:
    """Extract the spec.json entries from one Python source string, keyed by
    symbol-id. module_prefix (the file's dotted module) fills each entry's
    fqn. Returns {} on a syntax error (specgen never fails the build)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    out: dict = {}
    _visit(tree, [], relpath, out, module_prefix)
    return out


def extract_tree(src_dir: Path, root: Path) -> dict:
    """Extract spec.json from every .py under src_dir; symbol-id paths are relative
    to root (the repo root, so keys match ccr's review address space)."""
    out: dict = {}
    for path in sorted(src_dir.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        out.update(extract_file(text, path.relative_to(root).as_posix(), _module_prefix(path)))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="specgen", description="Extract spec/case/rule/link markers into spec.json.")
    ap.add_argument("src", help="directory to scan for .py files")
    ap.add_argument("-o", "--out", default="-", help="output path (default: stdout)")
    ap.add_argument("--root", default=None, help="repo root for relpath symbol-ids (default: src)")
    ap.add_argument(
        "--check",
        action="store_true",
        help="compare against -o instead of writing; exit 1 if spec.json is out of date (CI drift gate)",
    )
    ns = ap.parse_args(argv)

    src = Path(ns.src).resolve()
    root = Path(ns.root).resolve() if ns.root else src
    index = extract_tree(src, root)

    if ns.check:
        return _check(ns.out, index)

    text = json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True)
    if ns.out == "-":
        print(text)
    else:
        Path(ns.out).write_text(text + "\n", encoding="utf-8")
        print(f"specgen: {len(index)} symbol(s) -> {ns.out}", file=sys.stderr)
    return 0


def _check(out: str, fresh: dict) -> int:
    """Compare the freshly-extracted index against the committed spec.json at `out`.

    Drift means the markers in the code no longer match the committed spec.json —
    a symbol was renamed/moved (new symbol-id), removed, or its markers changed
    without regenerating. Returns 0 when up to date, 1 on drift, 2 on misuse.
    """
    if out == "-":
        print("specgen --check needs -o <spec.json>", file=sys.stderr)
        return 2
    path = Path(out)
    if not path.exists():
        print(f"specgen --check: {out} does not exist — run specgen to create it", file=sys.stderr)
        return 1
    try:
        committed = json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as exc:
        print(f"specgen --check: {out} is not valid JSON: {exc}", file=sys.stderr)
        return 1

    if committed == fresh:
        print(f"specgen --check: {out} is up to date ({len(fresh)} symbol(s))", file=sys.stderr)
        return 0

    print(f"specgen --check: {out} is out of date — run specgen to regenerate:", file=sys.stderr)
    committed_ids, fresh_ids = set(committed), set(fresh)
    for uid in sorted(fresh_ids - committed_ids):
        print(f"  + {uid}  (marked in code, missing from spec.json)", file=sys.stderr)
    for uid in sorted(committed_ids - fresh_ids):
        print(f"  - {uid}  (in spec.json, but no such marked symbol — renamed/removed)", file=sys.stderr)
    for uid in sorted(committed_ids & fresh_ids):
        if committed[uid] != fresh[uid]:
            print(f"  ~ {uid}  (markers changed)", file=sys.stderr)
    return 1


def cli() -> None:
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
