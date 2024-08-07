import os
from typing import Sequence

import environ
from loguru import logger

deployment_log = logger.bind(name='deployment')


def get_deployment_build_id() -> str | None:
    return os.getenv('BUILD_ID', None)


def get_deployment_git_rev() -> str | None:
    return os.getenv('GIT_REV', None)


def run_deployment_checks():
    from django.core import checks

    msgs: list[checks.CheckMessage] = checks.run_checks(include_deployment_checks=True)
    LEVEL_MAP = {
        checks.DEBUG: 'DEBUG',
        checks.INFO: 'INFO',
        checks.WARNING: 'WARNING',
        checks.ERROR: 'ERROR',
        checks.CRITICAL: 'CRITICAL',
    }

    for msg in msgs:
        msg.hint = None
        deployment_log.log(LEVEL_MAP.get(msg.level, 'WARNING'), str(msg))


BOOLEAN_TRUE_STRINGS = ('true', 'on', 'ok', 'y', 'yes', '1')
BOOLEAN_FALSE_STRINGS = ('false', 'off', 'n', 'no', '0')

def _check_env_match(env_var: str, matches: Sequence[str]):
    val = os.getenv(env_var, None)
    if val is None:
        return False

    val = val.lower().strip()
    return val in matches


def env_bool(env_var: str, default: bool) -> bool:
    """
    Determine a boolean value from an environment variable.

    This function checks the value of the specified environment variable
    and interprets it as a boolean. It uses predefined sets of strings
    to determine true and false values.

    Args:
    ----
        env_var (str): The name of the environment variable to check.
        default (bool): The default value to return if the environment
                        variable is not set or its value is not recognized.

    Returns:
    -------
        bool: The boolean interpretation of the environment variable's value,
              or the default value if the variable is not set or not recognized.

    Note:
    ----
        - True values: 'true', 'on', 'ok', 'y', 'yes', '1' (case-insensitive)
        - False values: 'false', 'off', 'n', 'no', '0' (case-insensitive)

    """
    if default:
        is_false = _check_env_match(env_var, BOOLEAN_FALSE_STRINGS)
        return not is_false
    else:
        is_true = _check_env_match(env_var, BOOLEAN_TRUE_STRINGS)
        return is_true
