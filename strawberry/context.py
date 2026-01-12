from __future__ import annotations

import time
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, cast
from urllib.parse import urljoin, urlsplit

from django.contrib.auth.models import AnonymousUser
from django.http.request import HttpRequest
from django.utils.encoding import iri_to_uri
from strawberry.channels import ChannelsRequest, GraphQLWSConsumer

from starlette.requests import Request as StarletteRequest

from kausal_common.perf.perf_context import PerfContext

if TYPE_CHECKING:
    from kausal_common.asgi.types import ASGICommonScope
    from kausal_common.auth.tokens import TokenAuthResult
    from kausal_common.deployment.types import LoggedHttpRequest
    from kausal_common.strawberry.views import RequestType, ResponseType
    from kausal_common.users import UserOrAnon

    from .extensions import GraphQLPerfNode


@dataclass
class GraphQLContext:
    request: RequestType
    response: ResponseType
    operation_name: str | None = None
    referer: str | None = None
    wildcard_domains: list[str] = field(default_factory=list)
    graphql_perf: PerfContext[GraphQLPerfNode] = field(init=False)
    graphql_query_language: str | None = field(init=False)
    graphql_cache_key: str | None = field(init=False, default=None)
    graphql_no_cache_reason: str | None = field(init=False, default=None)
    op_started_at: float = field(default_factory=time.perf_counter_ns)

    def get_ws_consumer(self) -> GraphQLWSConsumer:
        assert isinstance(self.request, GraphQLWSConsumer)
        return self.request

    def get_http_request(self) -> HttpRequest:
        assert isinstance(self.request, HttpRequest)
        return self.request

    def get_scope(self) -> ASGICommonScope:
        if isinstance(self.request, (GraphQLWSConsumer, StarletteRequest)):
            return cast('ASGICommonScope', self.request.scope)  # pyright: ignore[reportInvalidCast]
        if isinstance(self.request, ChannelsRequest):
            return cast('ASGICommonScope', self.request.consumer.scope)  # pyright: ignore[reportInvalidCast]
        raise ValueError('Unknown request type')

    def get_token_auth(self) -> TokenAuthResult | None:
        if isinstance(self.request, HttpRequest):
            req = cast('LoggedHttpRequest', self.request)
            return req.token_auth
        scope = self.get_scope()
        return scope.get('token_auth')

    def get_host(self) -> str:
        scope = self.get_scope()
        for header, value in scope['headers']:
            if header == b'host':
                return value.decode('utf-8')
        raise ValueError('Host header not found')

    def get_scheme_host(self) -> str:
        scope = self.get_scope()
        return scope['scheme'] + '://' + self.get_host()

    def get_user(self) -> UserOrAnon:
        req = self.request
        if isinstance(req, HttpRequest):
            return cast('UserOrAnon', req.user)
        if isinstance(req, (GraphQLWSConsumer, StarletteRequest)):
            user = req.scope.get('user')
        elif isinstance(req, ChannelsRequest):
            user = req.consumer.scope.get('user')
        else:
            user = None
        if user is None:
            return AnonymousUser()
        return cast('UserOrAnon', user)

    def build_absolute_uri(self, location: str | None) -> str:
        if isinstance(self.request, HttpRequest):
            return self.request.build_absolute_uri(location)
        scope = self.get_scope()
        if location is None:
            location = '//%s' % scope['path']
        bits = urlsplit(location)
        if bits.scheme and bits.netloc:
            return iri_to_uri(location)
        # Handle the simple, most common case. If the location is absolute
        # and a scheme or host (netloc) isn't provided, skip an expensive
        # urljoin() as long as no path segments are '.' or '..'.
        if (
            bits.path.startswith("/")
            and not bits.scheme
            and not bits.netloc
            and "/./" not in bits.path
            and "/../" not in bits.path
        ):
            # If location starts with '//' but has no netloc, reuse the
            # schema and netloc from the current request. Strip the double
            # slashes and continue as if it wasn't specified.
            location = self.get_scheme_host() + location.removeprefix("//")
        else:
            # Join the constructed URL with the provided location, which
            # allows the provided location to apply query strings to the
            # base path.
            location = urljoin(self.get_scheme_host() + scope['path'], location)
        return iri_to_uri(location)

    @cached_property
    def user(self) -> UserOrAnon:
        return self.get_user()

    def __post_init__(self):
        from django.conf import settings

        perf: PerfContext = PerfContext(
            supports_cache=False,
            min_ms=10,
            description=self.operation_name,
        )
        perf.enabled = getattr(settings, 'ENABLE_PERF_TRACING', False)
        self.graphql_perf = perf
        self.graphql_query_language = None
