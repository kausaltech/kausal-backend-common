#!/usr/bin/env python

from __future__ import annotations

import sys
from pathlib import Path

from mypy.main import process_options


def filter_mypy_sources():
    sources, _ = process_options(['.'])
    source_paths = {Path(s.path).resolve() for s in sources if s.path is not None}

    repo_root = Path.cwd().resolve()

    for line in sys.stdin:
        file_path = (repo_root / line.strip()).resolve()
        if file_path in source_paths:
            print(line.strip())


if __name__ == '__main__':
    filter_mypy_sources()
