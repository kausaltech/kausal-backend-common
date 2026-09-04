#!/usr/bin/env python3
"""
Render mypy JSON diagnostics with clickable source locations.

Usage: mypy -O json <targets...> | scripts/format_mypy_json.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

SOURCE_INDENT = ' ' * 4
PYTHON_SYNTAX = Syntax('', 'python', theme='ansi_dark', background_color='default')
THEME = Theme({
    'diagnostic.error': 'bold red',
    'diagnostic.warning': 'bold yellow',
    'diagnostic.note': 'bold blue',
    'diagnostic.code': 'yellow',
    'diagnostic.marker': 'red',
})


def location_target(file: str, line: int, *, cwd: Path) -> str:
    path = Path(file)
    if not path.is_absolute():
        path = cwd / path
    return f'{path.absolute().as_uri()}#{line}'


def render_header(diagnostic: dict[str, Any], *, cwd: Path) -> Text:
    file = str(diagnostic['file'])
    line = int(diagnostic['line'])
    severity = str(diagnostic['severity'])

    header = Text()
    header.append(f'{file}:{line}', style=f'link {location_target(file, line, cwd=cwd)}')
    header.append(': ')
    header.append(f'{severity}:', style=f'diagnostic.{severity}')
    header.append(f' {diagnostic["message"]}')
    if code := diagnostic.get('code'):
        header.append(f'  [{code}]', style='diagnostic.code')
    return header


def render_source(diagnostic: dict[str, Any], *, cwd: Path) -> tuple[Text, Text] | None:
    file = Path(str(diagnostic['file']))
    if not file.is_absolute():
        file = cwd / file

    try:
        source_line = file.read_text(encoding='utf-8').splitlines()[int(diagnostic['line']) - 1]
    except IndexError, OSError, UnicodeError:
        return None

    raw_column = max(int(diagnostic.get('column') or 0), 0)
    end_line = int(diagnostic.get('end_line') or diagnostic['line'])
    raw_end_column = int(diagnostic.get('end_column') or raw_column + 1)
    column = len(source_line[:raw_column].expandtabs())
    end_column = len(source_line[:raw_end_column].expandtabs())
    marker_width = max(end_column - column, 1) if end_line == int(diagnostic['line']) else 1

    highlighted_source = PYTHON_SYNTAX.highlight(source_line.expandtabs())
    highlighted_source.rstrip()
    source = Text(SOURCE_INDENT)
    source.append_text(highlighted_source)
    marker = Text(f'{SOURCE_INDENT}{" " * column}^{"~" * (marker_width - 1)}', style='diagnostic.marker')
    return source, marker


def render_hints(hint: str) -> list[Text]:
    hints = []
    for line in hint.splitlines():
        rendered = Text(SOURCE_INDENT)
        rendered.append('hint:', style='diagnostic.note')
        rendered.append(f' {line}')
        hints.append(rendered)
    return hints


def main() -> int:
    console = Console(theme=THEME, highlight=False)
    cwd = Path.cwd()
    counts: Counter[str] = Counter()
    files_with_errors: set[str] = set()

    for input_line in sys.stdin:
        if not input_line.strip():
            continue
        try:
            diagnostic = json.loads(input_line)
        except json.JSONDecodeError as error:
            console.print(f'Invalid mypy JSON: {error}', style='diagnostic.error', soft_wrap=True)
            return 2

        severity = str(diagnostic['severity'])
        counts[severity] += 1
        if severity == 'error':
            files_with_errors.add(str(diagnostic['file']))

        console.print(render_header(diagnostic, cwd=cwd), soft_wrap=True)
        if source := render_source(diagnostic, cwd=cwd):
            console.print(*source, sep='\n', soft_wrap=True)
        if hint := diagnostic.get('hint'):
            console.print(*render_hints(str(hint)), sep='\n', soft_wrap=True)

    error_count = counts['error']
    if error_count:
        error_word = 'error' if error_count == 1 else 'errors'
        file_word = 'file' if len(files_with_errors) == 1 else 'files'
        console.print(
            f'Found {error_count} {error_word} in {len(files_with_errors)} {file_word}',
            style='diagnostic.error',
            soft_wrap=True,
        )
        return 1

    console.print('Success: no issues found', style='bold green', soft_wrap=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
