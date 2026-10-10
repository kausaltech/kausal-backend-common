"""Checks for definition moves without importing audited packages."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kausal_common.development.tools.audit_stub_layout import audit


class StubLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stubs = self.root / 'stubs' / 'example'
        self.source = self.root / 'source' / 'example'

    def write(self, root: Path, path: str, content: str) -> None:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def test_reexport_chain_and_renamed_symbol(self) -> None:
        self.write(self.stubs, '__init__.pyi', 'class Public: ...\n')
        self.write(self.source, '__init__.py', 'raise RuntimeError("must not import")\nfrom .bridge import Public\n')
        self.write(self.source, 'bridge.py', 'from .implementation import Original as Public\n')
        self.write(self.source, 'implementation.py', 'class Original: pass\n')
        findings = audit('example', self.stubs, [self.source])
        moved = [finding for finding in findings if finding.kind == 'moved-definition']
        assert len(moved) == 1
        assert moved[0].targets == ['example.implementation.Original']
        assert moved[0].line == 1

    def test_same_name_is_only_a_candidate(self) -> None:
        self.write(self.stubs, '__init__.pyi', 'class Removed: ...\n')
        self.write(self.source, '__init__.py', '')
        self.write(self.source, 'other.py', 'class Removed: pass\n')
        findings = audit('example', self.stubs, [self.source])
        assert not any(finding.kind == 'moved-definition' for finding in findings)
        candidate = next(finding for finding in findings if finding.kind == 'possible-move')
        assert candidate.targets == ['example.other.Removed']

    def test_conditional_binding_is_not_a_certain_move(self) -> None:
        self.write(self.stubs, '__init__.pyi', 'class Choice: ...\n')
        self.write(self.source, '__init__.py', 'if feature:\n from .a import Choice\nelse:\n from .b import Choice\n')
        self.write(self.source, 'a.py', 'class Choice: pass\n')
        self.write(self.source, 'b.py', 'class Choice: pass\n')
        findings = audit('example', self.stubs, [self.source])
        candidate = next(finding for finding in findings if finding.kind == 'possible-move')
        assert candidate.targets == ['example.a.Choice', 'example.b.Choice']

    def test_cycle_does_not_recurse_forever(self) -> None:
        self.write(self.stubs, '__init__.pyi', 'class Missing: ...\n')
        self.write(self.source, '__init__.py', 'from .loop import Missing\n')
        self.write(self.source, 'loop.py', 'from . import Missing\n')
        findings = audit('example', self.stubs, [self.source])
        assert any(finding.kind == 'unresolved-declaration' for finding in findings)

    def test_stub_only_helpers_and_methods_are_skipped(self) -> None:
        self.write(
            self.stubs,
            '__init__.pyi',
            'from typing import type_check_only\n@type_check_only\nclass Helper: ...\nclass Real:\n def method(self): ...\n',
        )
        self.write(self.source, '__init__.py', 'class Real: pass\n')
        assert audit('example', self.stubs, [self.source]) == []

    def test_nested_relative_import_and_overloads(self) -> None:
        self.write(
            self.stubs,
            'nested/__init__.pyi',
            'from typing import overload\n@overload\ndef function(x: int): ...\n@overload\ndef function(x: str): ...\n',
        )
        self.write(self.source, 'nested/__init__.py', 'from ..implementation import function\n')
        self.write(self.source, 'implementation.py', 'def function(x): pass\n')
        findings = audit('example', self.stubs, [self.source])
        moved = [finding for finding in findings if finding.kind == 'moved-definition']
        assert len(moved) == 1
        assert moved[0].targets == ['example.implementation.function']

    def test_cli_json_and_failure_exit(self) -> None:
        self.write(self.stubs, '__init__.pyi', '')
        self.write(self.source, '__init__.py', '')
        self.write(self.source, 'missing.py', 'class New: pass\n')
        tool = Path(__file__).resolve().parents[1] / 'tools' / 'audit_stub_layout.py'
        result = subprocess.run(  # noqa: S603 -- fixed tool and interpreter; paths belong to this test
            [
                sys.executable,
                str(tool),
                'example',
                '--stub-root',
                str(self.stubs.parent),
                '--source-root',
                str(self.source.parent),
                '--format',
                'json',
                '--fail-on-findings',
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1, result.stderr
        assert json.loads(result.stdout)['counts'] == {'missing-stub-module': 1}


if __name__ == '__main__':
    unittest.main()
