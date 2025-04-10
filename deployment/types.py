from __future__ import annotations

import os
from enum import Enum
from functools import cache
from typing import TYPE_CHECKING, TypedDict
from warnings import warn

if TYPE_CHECKING:
    from django.http import HttpRequest

    from sentry_sdk import Scope


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


class ClusterContext(TypedDict):
    cluster: str | None
    node_name: str | None
    pod_name: str | None


@cache
def get_cluster_context() -> ClusterContext:
    return ClusterContext(cluster=os.getenv('CLUSTER_NAME'), node_name=os.getenv('NODE_NAME'), pod_name=os.getenv('POD_NAME'))


if TYPE_CHECKING:
    from users.models import User

    class LoggedHttpRequest(HttpRequest):
        correlation_id: str
        client_ip: str | None
        scope: Scope
        user: User | None
