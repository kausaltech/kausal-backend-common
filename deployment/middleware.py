from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.utils.deprecation import MiddlewareMixin

from asgiref.sync import sync_to_async

from kausal_common.logging.request import RequestCommonMeta

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from django.http.request import HttpRequest
    from django.http.response import HttpResponseBase

    from kausal_common.deployment.types import LoggedHttpRequest


class RequestStartMiddleware(MiddlewareMixin):
    def __init__(self, get_response) -> None:
        super().__init__(get_response)

    def __call__(self, request: HttpRequest) -> Awaitable[HttpResponseBase] | HttpResponseBase:
        if self.async_mode:
            return self.__acall__(request)

        request = cast('LoggedHttpRequest', request)
        common_meta = RequestCommonMeta.from_request(request)
        request.token_auth = None
        with common_meta.start_request(request=request) as sentry_scope:
            request.sentry_scope = sentry_scope
            return self.get_response(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        request = cast('LoggedHttpRequest', request)
        common_meta = await sync_to_async(RequestCommonMeta.from_request, thread_sensitive=True)(request)
        request.token_auth = None
        with common_meta.start_request(request=request) as sentry_scope:
            request.sentry_scope = sentry_scope
            response = cast('Awaitable[HttpResponseBase]', self.get_response(request))
            return await response
