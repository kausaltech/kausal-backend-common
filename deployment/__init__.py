import os


def get_deployment_build_id() -> str | None:
    return os.getenv('BUILD_ID', None)


def get_deployment_git_rev() -> str | None:
    return os.getenv('GIT_REV', None)
