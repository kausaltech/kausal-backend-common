from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlsplit, urlunsplit

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import (
    HashedFilesMixin,
    ManifestStaticFilesStorage as DjangoManifestStorage,
    StaticFilesStorage,
    staticfiles_storage,
)

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

    def post_process(self, paths: dict[str, Any], dry_run: bool = False, **options: Any) -> Iterator[tuple[str, str, bool]]:
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


# The stubs give `url()` different signatures in the two bases; the same holds for Django's manifest storage
class CheckedStaticFilesStorage(HashedFilesMixin, StaticFilesStorage):  # type: ignore[misc]
    """
    Static files storage for the test suite.

    The manifest storage only works after `collectstatic` has written its manifest, and every static
    file added since then fails to resolve. This storage doesn't hash file names, so it needs no
    manifest. Like the manifest storage, it still fails on a reference to a static file that doesn't
    exist, so a mistyped `{% static %}` path keeps breaking the tests.
    """

    def stored_name(self, name: str) -> str:
        # Called by `HashedFilesMixin.url()`, which also handles fragments, directory paths and URL
        # quoting the way the manifest storage does. This mirrors `ManifestFilesMixin.stored_name()`,
        # with the manifest lookup replaced by a check that the file exists, and without hashing.
        parsed_name = urlsplit(unquote(name))
        clean_name = parsed_name.path.strip()
        if not self._is_existing_file(clean_name):
            raise ValueError(f"Static file not found: '{clean_name}'")
        unparsed_name = list(parsed_name)
        unparsed_name[2] = clean_name
        # Special casing for the @font-face hack, as in `ManifestFilesMixin.stored_name()`
        if '?#' in name and not unparsed_name[3]:
            unparsed_name[2] += '?'
        return urlunsplit(unparsed_name)

    def _is_existing_file(self, name: str) -> bool:
        # The finders normalize the path they look up, so they also accept an absolute path inside a
        # static directory, or one with `.`, `..` or empty segments. The manifest storage has entries
        # only for the canonical relative path, so it rejects these, and so must this storage. (An
        # absolute path has an empty first segment.)
        if any(segment in ('', '.', '..') for segment in name.split('/')):
            return False
        # Not cached: a test may change what the finders see, by overriding settings or by creating
        # files, and a lookup is cheap compared to the page render that triggers it.
        found = finders.find(name)
        return isinstance(found, str) and Path(found).is_file()


@dataclass
class ManifestEntry:
    path: str
    integrity_hash: str

    @property
    def url(self) -> str:
        return staticfiles_storage.url(self.path)


def load_from_manifest(root_path: PurePath, entries: list[str]) -> dict[str, ManifestEntry]:
    manifest_fn = finders.find(f'{root_path}/manifest.json')
    if not manifest_fn:
        raise FileNotFoundError(f'Manifest file not found for {root_path}')
    with Path(manifest_fn).open('r') as f:
        manifest = json.load(f)
    out: dict[str, ManifestEntry] = {}
    for entry in entries:
        data = manifest[entry]
        out[entry] = ManifestEntry(path=data['file'], integrity_hash=data['integrity-hash'])
    return out
