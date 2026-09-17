import os
import subprocess
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).parents[1] / 'docker' / 'docker-entrypoint.sh'


@pytest.mark.parametrize('server', ['gunicorn', 'uwsgi', 'runserver', ''])
def test_web_startup_hooks_run_in_order_before_server(tmp_path: Path, server: str) -> None:
    hooks = tmp_path / 'hooks'
    hooks.mkdir()
    events = tmp_path / 'events'
    for name in ['20-second', '10-first']:
        script = hooks / name
        script.write_text(f'#!/bin/bash\necho {name} >> "$EVENTS"\n')
        script.chmod(0o755)
    (hooks / '30-disabled').write_text('exit 1\n')
    for name in ['gunicorn', 'uwsgi', 'python']:
        binary = tmp_path / name
        binary.write_text('#!/bin/bash\necho server >> "$EVENTS"\n')
        binary.chmod(0o755)
    # The production runserver branch uses /code; avoid depending on that directory locally.
    entrypoint = tmp_path / 'entrypoint.sh'
    entrypoint.write_text(ENTRYPOINT.read_text().replace('cd /code', f'cd "{tmp_path}"'))
    env = {
        **os.environ,
        'PATH': f'{tmp_path}:{os.environ["PATH"]}',
        'KUBERNETES_MODE': '1',
        'PRE_ENTRY_DIR': str(hooks),
        'EVENTS': str(events),
        'PROMETHEUS_MULTIPROC_DIR': '',
    }
    subprocess.run(  # noqa: S603 - scripts and arguments are test-owned
        ['/bin/bash', str(entrypoint), server], env=env, check=True, capture_output=True
    )
    assert events.read_text().splitlines() == ['10-first', '20-second', 'server']


@pytest.mark.parametrize('exists', [True, False])
def test_custom_command_skips_hooks(tmp_path: Path, exists: bool) -> None:
    hooks = tmp_path / 'hooks'
    if exists:
        hooks.mkdir()
        script = hooks / '10-fail'
        script.write_text('#!/bin/bash\nexit 1\n')
        script.chmod(0o755)
    subprocess.run(  # noqa: S603 - scripts and arguments are test-owned
        ['/bin/bash', str(ENTRYPOINT), 'true'], env={**os.environ, 'PRE_ENTRY_DIR': str(hooks)}, check=True
    )


@pytest.mark.parametrize('exists', [True, False])
def test_web_startup_without_hooks(tmp_path: Path, exists: bool) -> None:
    hooks = tmp_path / 'hooks'
    if exists:
        hooks.mkdir()
    binary = tmp_path / 'gunicorn'
    binary.write_text('#!/bin/bash\necho server\n')
    binary.chmod(0o755)
    env = {
        **os.environ,
        'PATH': f'{tmp_path}:{os.environ["PATH"]}',
        'KUBERNETES_MODE': '1',
        'PRE_ENTRY_DIR': str(hooks),
        'PROMETHEUS_MULTIPROC_DIR': '',
    }
    result = subprocess.run(  # noqa: S603 - fixed entrypoint and test-owned environment
        ['/bin/bash', str(ENTRYPOINT), 'gunicorn'],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == 'server'
