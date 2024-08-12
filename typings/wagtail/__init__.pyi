from wagtail.utils.version import get_semver_version as get_semver_version, get_version as get_version

VERSION: tuple[int, int, int, str, int]
__version__: str
__semver__: str

def setup() -> None: ...
