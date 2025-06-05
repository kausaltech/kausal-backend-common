from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, cast

from django.utils.deprecation import MiddlewareMixin

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
        request = cast('LoggedHttpRequest', request)
        common_meta = RequestCommonMeta.from_request(request)
        request.token_auth = None
        with common_meta.start_request(request=request) as sentry_scope:
            request.sentry_scope = sentry_scope
            return self.get_response(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        response = self.__call__(request)
        if inspect.isawaitable(response):
            return await response
        return response
