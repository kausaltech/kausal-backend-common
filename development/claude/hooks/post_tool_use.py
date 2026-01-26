from __future__ import annotations  # noqa: INP001

import json
import subprocess
import sys
from pathlib import Path


def get_file_extension(file_path: Path) -> str:
    """Get the file extension from a file path."""
    return file_path.suffix.lower()


def format_python(file_path: Path) -> bool:
    """Format Python files using ruff."""

    try:
        subprocess.run(['ruff', 'format', '--check', '-s', str(file_path)], check=True, capture_output=True)  # noqa: S603, S607
    except subprocess.CalledProcessError:
        pass
    except FileNotFoundError:
        return False
    else:
        return False

    subprocess.run(['ruff', 'format', '-s', str(file_path)], check=True, capture_output=True)  # noqa: S603, S607
    return True


def main():
    tool_data = json.loads(sys.stdin.read().strip())
    path_str = tool_data.get('tool_input', {}).get('file_path', '')
    path = Path(path_str)
    if not path.exists():
        return
    formatted = False
    if get_file_extension(path) == '.py':
        formatted = format_python(path)
    if formatted:
        print(f'Formatted file: {path}')


if __name__ == '__main__':
    main()
