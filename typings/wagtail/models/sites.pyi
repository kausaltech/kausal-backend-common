from collections.abc import Iterable
from typing import ClassVar, NamedTuple

from django.db import models
from django.db.models import BooleanField, CharField, ForeignKey, IntegerField, QuerySet
from django.http import HttpRequest
#from wagtail.models import Page

from _typeshed import Incomplete

from wagtail.models import Page

def get_site_for_hostname(hostname: str, port: int) -> Site:
    """Return the wagtailcore.Site object for the given hostname and port."""

class SiteManager(models.Manager[Site]):
    def get_queryset(self) -> QuerySet[Site]: ...
    def get_by_natural_key(self, hostname: str, port: int) -> Site: ...


class SiteRootPath(NamedTuple):
    site_id: int
    root_path: str
    root_url: str
    language_code: str

SITE_ROOT_PATHS_CACHE_KEY: str
SITE_ROOT_PATHS_CACHE_VERSION: int

class Site(models.Model):
    hostname: CharField
    port: IntegerField
    site_name: CharField
    root_page: ForeignKey[Page, Page]
    is_default_site: BooleanField
    objects: ClassVar[SiteManager]

    def natural_key(self) -> tuple[str, int]: ...
    def clean(self) -> None: ...
    @staticmethod
    def find_for_request(request: HttpRequest) -> Site:
        """
        Find the site object responsible for responding to this HTTP
        request object. Try:

        * unique hostname first
        * then hostname and port
        * if there is no matching hostname at all, or no matching
          hostname:port combination, fall back to the unique default site,
          or raise an exception

        NB this means that high-numbered ports on an extant hostname may
        still be routed to a different hostname which is set as the default

        The site will be cached via request._wagtail_site
        """
    @property
    def root_url(self) -> str: ...
    def clean_fields(self, exclude: Iterable[str] | None = None) -> None: ...
    @staticmethod
    def get_site_root_paths() -> list[SiteRootPath]:
        """
        Return a list of `SiteRootPath` instances, most specific path
        first - used to translate url_paths into actual URLs with hostnames

        Each root path is an instance of the `SiteRootPath` named tuple,
        and have the following attributes:

        - `site_id` - The ID of the Site record
        - `root_path` - The internal URL path of the site's home page (for example '/home/')
        - `root_url` - The scheme/domain name of the site (for example 'https://www.example.com/')
        - `language_code` - The language code of the site (for example 'en')
        """
    @staticmethod
    def clear_site_root_paths_cache() -> None: ...
