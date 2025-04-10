from __future__ import annotations

import inspect
from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

from django.utils.deprecation import MiddlewareMixin

import nanoid
import sentry_sdk

from kausal_common.const import FORWARDED_FOR_HEADER, FORWARDED_HEADER
from kausal_common.deployment.http import parse_forwarded
from kausal_common.deployment.types import get_cluster_context
from kausal_common.logging.http import start_request

if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator

    from django.http.request import HttpRequest
    from django.http.response import HttpResponseBase

    from kausal_common.deployment.types import LoggedHttpRequest


ID_ALPHABET = '346789ABCDEFGHJKLMNPQRTUVWXYabcdefghijkmnpqrtwxyz'


class RequestStartMiddleware(MiddlewareMixin):
    def __init__(self, get_response) -> None:
        super().__init__(get_response)

    def _generate_correlation_id(self, request: HttpRequest) -> str:
        return nanoid.non_secure_generate(ID_ALPHABET, 8)

    def _get_client_ip(self, request: HttpRequest) -> str | None:
        forwarded = request.headers.get(FORWARDED_HEADER)
        if forwarded:
            fwd_vals = parse_forwarded([forwarded])
            if fwd_vals and fwd_vals[0].for_:
                return fwd_vals[0].for_
        x_fwd = request.headers.get(FORWARDED_FOR_HEADER)
        if x_fwd:
            return x_fwd.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @contextmanager
    def _set_sentry_context(self, request: LoggedHttpRequest) -> Generator[None, None, None]:  # noqa: UP043
        with sentry_sdk.new_scope() as scope:
            request.scope = scope
            if request.client_ip:
                scope.set_user({'ip_address': request.client_ip})
            scope.set_context('request', dict(correlation_id=request.correlation_id))
            cluster_context = get_cluster_context()
            for key, value in cluster_context.items():
                if value:
                    sentry_sdk.set_tag(key, value)
            yield

    def __call__(self, request: HttpRequest) -> Awaitable[HttpResponseBase] | HttpResponseBase:
        request = cast('LoggedHttpRequest', request)
        request.correlation_id = self._generate_correlation_id(request)
        request.client_ip = self._get_client_ip(request)
        with start_request(request), self._set_sentry_context(request):
            return self.get_response(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        response = self.__call__(request)
        if inspect.isawaitable(response):
            return await response
        return response


class RequestContextMiddleware(MiddlewareMixin):
    def __init__(self, get_response) -> None:
        super().__init__(get_response)

    def __call__(self, request: HttpRequest) -> Awaitable[HttpResponseBase] | HttpResponseBase:
        request = cast('LoggedHttpRequest', request)
        user = request.user
        if user and user.is_authenticated:
            request.scope.set_user(dict(
                id=user.pk,
                email=user.email,
            ))
        return self.get_response(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        response = self.__call__(request)
        if inspect.isawaitable(response):
            return await response
        return response
