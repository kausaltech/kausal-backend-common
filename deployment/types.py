from __future__ import annotations

import os
from enum import Enum
from functools import cache
from warnings import warn


class DeploymentEnvironmentType(Enum):
    PRODUCTION = 'production'
    STAGING = 'staging'
    TESTING = 'testing'
    WIP = 'wip'
    DEV = 'development'
    CI = 'ci'


def is_production_deployment() -> bool:
    return get_deployment_environment() == DeploymentEnvironmentType.PRODUCTION


def is_development_environment() -> bool:
    return get_deployment_environment() == DeploymentEnvironmentType.DEV


@cache
def get_deployment_environment() -> DeploymentEnvironmentType:
    dt_val: str
    try:
        from django.conf import settings

        dt_val = settings.DEPLOYMENT_TYPE
    except Exception:
        dt_val = os.getenv('DEPLOYMENT_TYPE') or 'development'
    try:
        dt = DeploymentEnvironmentType(value=dt_val)
    except ValueError:
        warn("Invalid deployment environment type: %s; defaulting to 'development'", stacklevel=1)
        return DeploymentEnvironmentType.DEV
    return dt
