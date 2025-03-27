from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Sequence, overload

from django.core.exceptions import ImproperlyConfigured

if TYPE_CHECKING:
    import environ

ENV_VARIABLE_PATTERN = re.compile(r'[A-Z][A-Z0-9_]*')


def get_deployment_build_id() -> str | None:
    return os.getenv('BUILD_ID', None)


def get_deployment_git_rev() -> str | None:
    return os.getenv('GIT_REV', None)


def run_deployment_checks():
    from django.core import checks

    from loguru import logger

    deployment_log = logger.bind(name='deployment')

    msgs: list[checks.CheckMessage] = checks.run_checks(include_deployment_checks=True)
    level_map = {
        checks.DEBUG: 'DEBUG',
        checks.INFO: 'INFO',
        checks.WARNING: 'WARNING',
        checks.ERROR: 'ERROR',
        checks.CRITICAL: 'CRITICAL',
    }

    for msg in msgs:
        msg.hint = None
        deployment_log.log(level_map.get(msg.level, 'WARNING'), str(msg))


BOOLEAN_TRUE_STRINGS = ('true', 'on', 'ok', 'y', 'yes', '1')
BOOLEAN_FALSE_STRINGS = ('false', 'off', 'n', 'no', '0')


def coerce_bool(val: str) -> bool | None:
    """
    Coerce a string to a boolean value.

    Returns
    -------
        bool | None:
            The boolean interpretation of the string, or None if the string
            is not recognized.

    """

    val = val.lower().strip()
    if val in BOOLEAN_FALSE_STRINGS:
        return False
    if val in BOOLEAN_TRUE_STRINGS:
        return True
    return None


@overload
def env_bool(env_var: str, default: bool) -> bool: ...


@overload
def env_bool(env_var: str, default: None) -> bool | None: ...


def env_bool(env_var: str, default: bool | None = None) -> bool | None:
    """
    Determine a boolean value from an environment variable.

    This function checks the value of the specified environment variable
    and interprets it as a boolean. It uses predefined sets of strings
    to determine true and false values.

    Args:
    ----
        env_var (str): The name of the environment variable to check.
        default (bool | None):
            The default value to return if the environment variable is not set
            or its value is not recognized.

    Returns:
    -------
        bool | None:
            The boolean interpretation of the environment variable's value,
            or the default value if the variable is not set or not recognized.

    Note:
    ----
        - True values: 'true', 'on', 'ok', 'y', 'yes', '1' (case-insensitive)
        - False values: 'false', 'off', 'n', 'no', '0' (case-insensitive)

    """
    val = os.getenv(env_var, None)
    if val is None:
        return default
    ret = coerce_bool(val)
    if ret is not None:
        return ret
    return default


def set_secret_file_vars(env: environ.Env, directory: str | Path) -> None:
    """
    Scan a directory for files that could be valid environment variables.

    If such files are found, set corresponding *_FILE variables in the
    environ.Env instance.

    :param env: An instance of environ.Env
    :param directory: The directory to scan for secret files (str or Path)
    """

    directory = Path(directory)

    if not directory.is_dir():
        msg = f"The provided path '{directory}' is not a valid directory."
        raise ValueError(msg)

    for file_path in directory.iterdir():
        if file_path.is_file() and ENV_VARIABLE_PATTERN.fullmatch(file_path.name):
            env_var_name = f'{file_path.name}_FILE'
            env.ENVIRON[env_var_name] = str(file_path)


def test_mode_enabled() -> bool:
    from kausal_common.deployment.types import DeploymentEnvironmentType, get_deployment_environment

    if not env_bool('CI', default=False):
        return False

    if not env_bool('TEST_MODE', default=False):
        return False

    if get_deployment_environment() not in (DeploymentEnvironmentType.CI, DeploymentEnvironmentType.DEV):
        raise ImproperlyConfigured('Test mode cannot be enabled in this environment')

    return True
