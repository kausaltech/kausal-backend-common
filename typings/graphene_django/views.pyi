# ruff: noqa: ANN401, PLR0913
from collections.abc import Callable, Collection, Generator, Sequence
from typing import Any

from django.http import HttpRequest as DjangoHttpRequest, HttpResponse
from django.views.generic import View
from graphene import Schema
from graphene_django.constants import MUTATION_ERRORS_FLAG as MUTATION_ERRORS_FLAG
from graphene_django.utils.utils import set_rollback as set_rollback
from graphql import ASTValidationRule, ExecutionContext, ExecutionResult, GraphQLError, GraphQLFormattedError, MiddlewareManager

from _typeshed import Incomplete

from .settings import graphene_settings as graphene_settings

class HttpError(Exception):
    response: HttpResponse
    message: str
    def __init__(self, response: HttpResponse, message: str | None = None, *args, **kwargs) -> None: ...

def get_accepted_content_types(request: HttpRequest) -> list[str]: ...
def instantiate_middleware(middlewares) -> Generator[Any, None, None]: ...

type MiddlewareType = MiddlewareManager | Sequence[type | Callable]
type ValidationRulesType = Collection[type[ASTValidationRule]]
type HttpRequest = DjangoHttpRequest

type GraphQLRequestParams = tuple[str, dict, str | None, str | None]

class GraphQLView(View):
    graphiql_template: str
    whatwg_fetch_version: str
    whatwg_fetch_sri: str
    react_version: str
    react_sri: str
    react_dom_sri: str
    graphiql_version: str
    graphiql_sri: str
    graphiql_css_sri: str
    subscriptions_transport_ws_version: str
    subscriptions_transport_ws_sri: str
    graphiql_plugin_explorer_version: str
    graphiql_plugin_explorer_sri: str
    graphiql_plugin_explorer_css_sri: str
    schema: Schema
    graphiql: bool
    middleware: Incomplete
    root_value: Incomplete
    pretty: bool
    batch: bool
    subscription_path: str | None
    execution_context_class: type[ExecutionContext] | None
    validation_rules: ValidationRulesType | None

    def __init__(
        self,
        schema: Schema | None = None,
        middleware: MiddlewareType | None = None,
        root_value: Any | None = None,
        graphiql: bool = False,
        pretty: bool = False,
        batch: bool = False,
        subscription_path: str | None = None,
        execution_context_class: type[ExecutionContext] | None = None,
        validation_rules: ValidationRulesType | None = None,
    ) -> None: ...
    def get_root_value(self, request: HttpRequest) -> Any: ...
    def get_middleware(self, request: HttpRequest) -> MiddlewareType: ...
    def get_context(self, request: HttpRequest) -> Any: ...
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse: ...
    def get_response(self, request: HttpRequest, data, show_graphiql: bool = False) -> tuple[str | None, int]: ...
    def render_graphiql(self, request: HttpRequest, **data) -> HttpResponse: ...
    def json_encode(self, request: HttpRequest, d: dict, pretty: bool = False) -> str | bytes: ...
    def parse_body(self, request: HttpRequest) -> dict[str, str]: ...
    def execute_graphql_request(
        self,
        request: HttpRequest,
        data: dict,
        query: str | None,
        variables: dict | None,
        operation_name: str | None,
        show_graphiql: bool = False,
    ) -> ExecutionResult: ...
    @classmethod
    def can_display_graphiql(cls, request: HttpRequest, data: dict) -> bool: ...
    @classmethod
    def request_wants_html(cls, request: HttpRequest) -> bool: ...
    @staticmethod
    def get_graphql_params(request: HttpRequest, data: dict) -> GraphQLRequestParams: ...
    @staticmethod
    def format_error(error: Exception | GraphQLError) -> GraphQLFormattedError: ...
    @staticmethod
    def get_content_type(request: HttpRequest) -> str: ...
