"""specgen: statically extract the spec/case/rule/link markers from Python
sources into spec.json — the artifact ccr's SpecBuilder consumes.

It parses with `ast` and never imports or runs the target code, so the markers
being no-ops is irrelevant: extraction is purely syntactic. Each entry is keyed
by its unit-id `<relpath>::<qualname>` (qualname = `func` or `Class.method`,
matching the unit-id contract and ccr's Python splitter).

CLI:  python -m spec_case.specgen <src-dir> [-o spec.json] [--root <repo-root>]
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


def _entry_for(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> dict | None:
    """Build the spec.json entry from a function's decorators, or None if it
    carries no markers."""
    spec_text = ""
    cases: list[dict] = []
    links: list[str] = []
    rules: list[str] = []
    for dec in fn.decorator_list:
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


def _visit(node: ast.AST, stack: list[str], relpath: str, out: dict) -> None:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            entry = _entry_for(child)
            if entry is not None:
                qual = ".".join(stack + [child.name])
                out[f"{relpath}::{qual}"] = entry
            # nested functions don't get unit-ids (binding is top-level funcs +
            # class methods, matching ccr's splitter), so don't descend into one.
        elif isinstance(child, ast.ClassDef):
            _visit(child, stack + [child.name], relpath, out)


def extract_file(src: str, relpath: str) -> dict:
    """Extract the spec.json entries from one Python source string, keyed by
    unit-id. Returns {} on a syntax error (specgen never fails the build)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    out: dict = {}
    _visit(tree, [], relpath, out)
    return out


def extract_tree(src_dir: Path, root: Path) -> dict:
    """Extract spec.json from every .py under src_dir; unit-id paths are relative
    to root (the repo root, so keys match ccr's review address space)."""
    out: dict = {}
    for path in sorted(src_dir.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        out.update(extract_file(text, path.relative_to(root).as_posix()))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="specgen", description="Extract spec/case/rule/link markers into spec.json.")
    ap.add_argument("src", help="directory to scan for .py files")
    ap.add_argument("-o", "--out", default="-", help="output path (default: stdout)")
    ap.add_argument("--root", default=None, help="repo root for relpath unit-ids (default: src)")
    ns = ap.parse_args(argv)

    src = Path(ns.src).resolve()
    root = Path(ns.root).resolve() if ns.root else src
    index = extract_tree(src, root)
    text = json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True)
    if ns.out == "-":
        print(text)
    else:
        Path(ns.out).write_text(text + "\n", encoding="utf-8")
        print(f"specgen: {len(index)} symbol(s) -> {ns.out}", file=sys.stderr)
    return 0


def cli() -> None:
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
