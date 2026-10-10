#!/usr/bin/env python3
"""
Compare local stub declarations with an installed package's Python source.

Usage: python kausal_common/development/tools/audit_stub_layout.py wagtail

Use --format json for complete findings, --show-missing-modules for the text
coverage inventory, and --fail-on-findings for CI (exit 1). Setup or parsing
errors exit 2. --source-root can select an unpacked upgrade before installation.
Coverage includes private, test and migration modules; not all need stubs.

No target modules are imported. Explicit re-exports establish definition moves;
same-name matches elsewhere are only suggestions. This complements stubtest,
which checks runtime API compatibility rather than definition locations.
Dynamic exports, wildcard imports, compiled modules and conditional bindings can
require manual review. Methods, signatures and annotation types are not checked.
"""

import argparse
import ast
import json
import sys
import tokenize
from collections import Counter
from dataclasses import asdict, dataclass
from importlib.machinery import PathFinder
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True)
class Declaration:
    module: str
    name: str
    kind: Literal['class', 'function']
    path: Path
    line: int


@dataclass
class Module:
    declarations: list[Declaration]
    # Multiple conditional bindings must not be mistaken for a certain identity.
    bindings: dict[str, set[tuple[str, str]]]


@dataclass
class Finding:
    kind: str
    module: str
    path: str
    line: int
    symbol: str | None
    targets: list[str]


def statements(body: list[ast.stmt]) -> Iterator[ast.stmt]:
    """Visit module-level branches without entering function or class scopes."""
    for node in body:
        yield node
        if isinstance(node, ast.If):
            yield from statements(node.body)
            yield from statements(node.orelse)
        elif isinstance(node, (ast.Try, ast.TryStar)):
            yield from statements(node.body)
            for handler in node.handlers:
                yield from statements(handler.body)
            yield from statements(node.orelse)
            yield from statements(node.finalbody)
        elif isinstance(node, (ast.With, ast.AsyncWith, ast.For, ast.AsyncFor, ast.While)):
            yield from statements(node.body)
            if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                yield from statements(node.orelse)


def module_name(package: str, root: Path, path: Path) -> str:
    parts = list(path.relative_to(root).with_suffix('').parts)
    if parts[-1] == '__init__':
        parts.pop()
    return '.'.join([package, *parts])


def scan_module(name: str, path: Path) -> Module:
    with tokenize.open(path) as source:
        tree = ast.parse(source.read(), filename=str(path))
    module = Module([], {})
    for node in statements(tree.body):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = [ast.unparse(dec) for dec in node.decorator_list]
            if any(dec.rsplit('.', 1)[-1] == 'type_check_only' for dec in decorators):
                continue
            kind: Literal['class', 'function'] = 'class' if isinstance(node, ast.ClassDef) else 'function'
            module.declarations.append(Declaration(name, node.name, kind, path, node.lineno))
            module.bindings.setdefault(node.name, set()).add((name, node.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parent = name.split('.') if path.stem == '__init__' else name.split('.')[:-1]
                parent = parent[: len(parent) - node.level + 1]
                target_module = '.'.join([*parent, *([node.module] if node.module else [])])
            else:
                target_module = node.module or ''
            for alias in node.names:
                if alias.name != '*':
                    module.bindings.setdefault(alias.asname or alias.name, set()).add((target_module, alias.name))
    return module


def scan(package: str, roots: list[Path], suffix: str) -> dict[str, Module]:
    modules: dict[str, Module] = {}
    for root in roots:
        for path in sorted(root.rglob(f'*{suffix}')):
            if '__pycache__' in path.parts:
                continue
            name = module_name(package, root, path)
            module = modules.setdefault(name, Module([], {}))
            scanned = scan_module(name, path)
            module.declarations.extend(scanned.declarations)
            for symbol, bindings in scanned.bindings.items():
                module.bindings.setdefault(symbol, set()).update(bindings)
    return modules


def resolve(
    modules: dict[str, Module], module: str, name: str, seen: frozenset[tuple[str, str]] = frozenset()
) -> tuple[str, str] | None:
    key = (module, name)
    if key in seen or module not in modules:
        return None
    bindings = modules[module].bindings.get(name, set())
    if len(bindings) != 1:
        return None
    target = next(iter(bindings))
    if target == key:
        return key
    return resolve(modules, *target, seen | {key})


def declaration_finding(
    declaration: Declaration, sources: dict[str, Module], candidates: dict[tuple[str, str], set[str]]
) -> Finding | None:
    name = declaration.module
    target = resolve(sources, name, declaration.name)
    if target == (name, declaration.name):
        return None
    if target is not None:
        kind = 'moved-definition'
        targets = ['.'.join(target)]
    else:
        possible = sorted(candidates.get((declaration.name, declaration.kind), set()) - {name})
        kind = 'possible-move' if possible else 'unresolved-declaration'
        targets = [f'{location}.{declaration.name}' for location in possible]
    return Finding(kind, name, str(declaration.path), declaration.line, declaration.name, targets)


def audit(package: str, stub_root: Path, source_roots: list[Path]) -> list[Finding]:
    stubs = scan(package, [stub_root], '.pyi')
    sources = scan(package, source_roots, '.py')
    candidates: dict[tuple[str, str], set[str]] = {}
    for source in sources.values():
        for declaration in source.declarations:
            candidates.setdefault((declaration.name, declaration.kind), set()).add(declaration.module)
    findings = [
        Finding('missing-stub-module', name, str(stub_root), 0, None, []) for name in sorted(sources.keys() - stubs.keys())
    ]
    for name, module in sorted(stubs.items()):
        if name not in sources:
            findings.append(Finding('missing-source-module', name, str(stub_root), 0, None, []))
        checked: set[str] = set()
        for declaration in module.declarations:
            if declaration.name in checked:
                continue  # Overloads are one declaration for layout purposes.
            checked.add(declaration.name)
            if finding := declaration_finding(declaration, sources, candidates):
                findings.append(finding)
    return findings


def installed_roots(package: str) -> list[Path]:
    # Unlike find_spec('package.submodule'), this never imports a parent package.
    spec = PathFinder.find_spec(package, sys.path)
    if spec is None or spec.submodule_search_locations is None:
        raise ValueError(f'{package}: no installed Python package found; use --source-root for an alternate source tree')
    return [Path(location) for location in spec.submodule_search_locations]


def audit_package(package: str, stub_root: Path, source_root: Path | None) -> list[Finding]:
    if not package.isidentifier():
        raise ValueError(f'{package}: specify a top-level package name')
    stubs = stub_root / package
    if not stubs.is_dir() or not any(stubs.rglob('*.pyi')):
        raise ValueError(f'{package}: no stubs under {stubs}')
    roots = [source_root / package] if source_root else installed_roots(package)
    if not all(root.is_dir() and any(root.rglob('*.py')) for root in roots):
        raise ValueError(f'{package}: no Python source found under {roots}')
    return audit(package, stubs, roots)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('packages', nargs='+', help='Top-level package names, e.g. wagtail modeltrans')
    parser.add_argument('--stub-root', type=Path, default=Path(__file__).resolve().parents[2] / 'typings')
    parser.add_argument('--source-root', type=Path, help='Directory containing packages; defaults to the interpreter environment')
    parser.add_argument('--format', choices=['text', 'json'], default='text')
    parser.add_argument(
        '--show-missing-modules',
        action='store_true',
        help='List every missing stub module in text output; otherwise show their count',
    )
    parser.add_argument('--fail-on-findings', action='store_true', help='Exit 1 on findings; setup/parse errors always exit 2')
    args = parser.parse_args()
    findings: list[Finding] = []
    errors: list[str] = []
    for package in args.packages:
        try:
            findings.extend(audit_package(package, args.stub_root, args.source_root))
        except (OSError, SyntaxError, UnicodeError, ValueError) as exc:
            errors.append(str(exc))
    counts = dict(sorted(Counter(finding.kind for finding in findings).items()))
    if args.format == 'json':
        print(json.dumps({'findings': [asdict(finding) for finding in findings], 'counts': counts, 'errors': errors}, indent=2))
    else:
        for finding in findings:
            if finding.kind == 'missing-stub-module' and not args.show_missing_modules:
                continue
            symbol = f'.{finding.symbol}' if finding.symbol else ''
            targets = f' -> {", ".join(finding.targets)}' if finding.targets else ''
            print(f'{finding.path}:{finding.line}: {finding.kind}: {finding.module}{symbol}{targets}')
        print('Summary: ' + (', '.join(f'{kind}={count}' for kind, count in counts.items()) or 'no findings'))
        for error in errors:
            print(f'Error: {error}', file=sys.stderr)
    if errors:
        return 2
    return int(args.fail_on_findings and bool(findings))


if __name__ == '__main__':
    raise SystemExit(main())
