from __future__ import annotations

import time
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, cast

from django.contrib.auth.models import AnonymousUser
from django.http.request import HttpRequest
from strawberry.channels import ChannelsRequest, GraphQLWSConsumer

from kausal_common.perf.perf_context import PerfContext

if TYPE_CHECKING:
    from django.http.response import HttpResponse
    from strawberry.http.temporal_response import TemporalResponse

    from kausal_common.asgi.types import ASGICommonScope
    from kausal_common.auth.tokens import TokenAuthResult
    from kausal_common.deployment.types import LoggedHttpRequest
    from kausal_common.users import UserOrAnon

    from .schema import GraphQLPerfNode


@dataclass
class GraphQLContext:
    request: HttpRequest | GraphQLWSConsumer | ChannelsRequest
    response: HttpResponse | GraphQLWSConsumer | TemporalResponse
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
        if isinstance(self.request, GraphQLWSConsumer):
            return self.request.scope
        if isinstance(self.request, ChannelsRequest):
            return self.request.consumer.scope
        raise ValueError('Unknown request type')

    def get_token_auth(self) -> TokenAuthResult | None:
        if isinstance(self.request, HttpRequest):
            req = cast('LoggedHttpRequest', self.request)
            return req.token_auth
        scope = self.get_scope()
        return scope.get('token_auth')

    def get_user(self) -> UserOrAnon:
        req = self.request
        if isinstance(req, HttpRequest):
            return cast('UserOrAnon', req.user)
        if isinstance(req, GraphQLWSConsumer):
            user = req.scope.get('user')
        elif isinstance(req, ChannelsRequest):
            user = req.consumer.scope.get('user')
        else:
            user = None
        if user is None:
            return AnonymousUser()
        return cast('UserOrAnon', user)

    def build_absolute_uri(self, path: str) -> str:
        if isinstance(self.request, HttpRequest):
            return self.request.build_absolute_uri(path)
        scope = self.get_scope()
        for header, value in scope['headers']:
            if header == b'host':
                host = value.decode('utf-8')
                break
        else:
            raise ValueError('Host header not found')
        scheme = scope['scheme']
        return f'{scheme}://{host}{path}'

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
