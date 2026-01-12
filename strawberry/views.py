from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypedDict

from django.http.request import HttpRequest
from strawberry import UNSET
from strawberry.channels import (
    ChannelsRequest,
    GraphQLWSConsumer as StrawberryGraphQLWSConsumer,
    SyncGraphQLHTTPConsumer as StrawberrySyncGraphQLHTTPConsumer,
)
from strawberry.channels.handlers.http_handler import ChannelsResponse, MultipartChannelsResponse
from strawberry.django.views import GraphQLView as StrawberryGraphQLView
from strawberry.http.temporal_response import TemporalResponse

import orjson
from starlette.requests import Request as StarletteRequest

from kausal_common.const import WILDCARD_DOMAINS_HEADER
from kausal_common.strawberry.context import GraphQLContext
from kausal_common.strawberry.helpers import graphql_log

if TYPE_CHECKING:
    from django.http.response import HttpResponse


class BaseContext(TypedDict):
    request: RequestType
    response: ResponseType
    referer: str | None
    wildcard_domains: list[str]


type RequestType = HttpRequest | StrawberryGraphQLWSConsumer[Any] | ChannelsRequest | StarletteRequest
type ResponseType = HttpResponse | StrawberryGraphQLWSConsumer[Any] | TemporalResponse | None

def get_base_context(
    request: RequestType,
    response: ResponseType,
) -> BaseContext:
    if isinstance(request, (HttpRequest, ChannelsRequest)):
        wildcard_domains_str = request.headers.get(WILDCARD_DOMAINS_HEADER)
        referer = request.headers.get('referer')
    else:
        assert isinstance(request, (StrawberryGraphQLWSConsumer, StarletteRequest))
        headers_list = request.scope.get('headers', [])
        headers = {key.decode('utf8'): value.decode('utf8') for key, value in headers_list}
        wildcard_domains_str = headers.get(WILDCARD_DOMAINS_HEADER)
        referer = headers.get('referer')
    wildcard_domains = [d.lower() for d in wildcard_domains_str.split(',')] if wildcard_domains_str else []

    return {
        'request': request,
        'response': response,
        'referer': referer,
        'wildcard_domains': wildcard_domains,
    }


class GraphQLView[Context: GraphQLContext = GraphQLContext](StrawberryGraphQLView[Context, None], ABC):
    context_class: type[Context]

    def get_base_context(self, request: HttpRequest, response: HttpResponse) -> BaseContext:
        return get_base_context(request, response)
    def decode_json(self, data: str | bytes) -> object:
        return orjson.loads(data)

    def encode_json(self, data: object) -> str:
        errors = []

        def serialize_unknown(obj) -> str:
            err = TypeError('Unable to serialize value %s with type %s' % (obj, type(obj)))
            errors.append(err)
            return ' '.join(['__INVALID__' * 10])

        opts = None
        ret = orjson.dumps(data, option=opts, default=serialize_unknown)
        if errors:
            from rich import print_json

            print_json(ret.decode('utf8'))
            raise errors[0]

        op_name = getattr(self.request, 'graphql_operation_name', None)
        graphql_log(
            'DEBUG',
            op_name,
            'Response was {} bytes',
            len(ret),
        )
        return ret.decode('utf8')

    @abstractmethod
    def get_context(self, request: HttpRequest, response: HttpResponse) -> Context: ...


class GraphQLWSConsumer[Context: GraphQLContext = GraphQLContext](StrawberryGraphQLWSConsumer[Context, None], ABC):
    context_class: type[Context]

    async def get_base_context(self, request: GraphQLWSConsumer, response: GraphQLWSConsumer) -> BaseContext:
        base_ctx = get_base_context(request, response)
        return base_ctx


class SyncGraphQLHTTPConsumer[Context: GraphQLContext = GraphQLContext](StrawberrySyncGraphQLHTTPConsumer[Context, None], ABC):
    context_class: type[Context]

    async def run(  # type: ignore[override]
        self,
        request: ChannelsRequest,
        context: Context | None = UNSET,
        root_value: Any | None = UNSET,
    ) -> ChannelsResponse | MultipartChannelsResponse:
        if request.method and request.method.lower() == "options":
            return ChannelsResponse(
                content=b'',
                status=200,
            )
        return await super().run(request, context=context, root_value=root_value)

    def get_base_context(self, request: ChannelsRequest, response: TemporalResponse) -> BaseContext:
        base_ctx = get_base_context(request, response)
        return base_ctx
