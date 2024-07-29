from enum import Enum


class DeploymentEnvironmentType(Enum):
    PRODUCTION = 'production'
    STAGING = 'staging'
    TESTING = 'testing'
    WIP = 'wip'


def is_production_deployment() -> bool:
    from django.conf import settings
    return settings.DEPLOYMENT_TYPE == DeploymentEnvironmentType.PRODUCTION
