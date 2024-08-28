from __future__ import annotations

from collections import OrderedDict
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage as DjangoManifestStorage

if TYPE_CHECKING:
    from collections.abc import Iterator


class ManifestStaticFilesStorage(DjangoManifestStorage):
    """
    A custom static files storage that extends Django's ManifestStaticFilesStorage.

    This storage class assumes that if a subdirectory contains an asset manifest,
    the filenames in that subdirectory already have an immutable content hash.
    It skips processing these files to avoid double-hashing.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def post_process(self, paths: dict[str, Any], dry_run: bool = False, **options: Any) -> Iterator[tuple[str, str, bool]]:  # noqa: ANN401
        new_paths: OrderedDict[str, Any] = OrderedDict(paths)
        ignore_dirs: set[PurePath] = set()
        for key in paths.keys():
            path = PurePath(key)
            if path.name == 'manifest.json':
                ignore_dirs.add(path.parent)

            for ign_dir in ignore_dirs:
                if path.is_relative_to(ign_dir):
                    del new_paths[key]
                    self.hashed_files[key] = key
                    break
        ret = super().post_process(new_paths, dry_run=dry_run, **options)
        return ret  # type: ignore[return-value]
