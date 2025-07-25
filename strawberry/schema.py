from __future__ import annotations

import dataclasses
import hashlib
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Annotated, Any

import strawberry
from django.conf import settings
from django.core.cache import cache
from django.http.request import HttpRequest
from graphql import DirectiveLocation, ExecutionResult, GraphQLError
from strawberry.channels import ChannelsRequest, GraphQLWSConsumer
from strawberry.exceptions import StrawberryGraphQLError
from strawberry.extensions import SchemaExtension as StrawberrySchemaExtension
from strawberry.types.graphql import OperationType

import orjson
import sentry_sdk
from loguru import logger
from rich.console import Console
from rich.syntax import Syntax
from sentry_sdk.tracing import TransactionSource

from kausal_common.deployment import env_bool, get_deployment_build_id
from kausal_common.graphene.merged_schema import GrapheneStrawberrySchema
from kausal_common.models.types import copy_signature
from kausal_common.strawberry.context import GraphQLContext
from kausal_common.users import user_or_none

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping

    from django.contrib.sessions.backends.base import SessionBase
    from strawberry.types import ExecutionContext

    from sentry_sdk.tracing import Transaction

    from kausal_common.asgi.types import ASGICommonScope

    from users.models import User


logger = logger.bind(name='graphql', markup=True)

@dataclasses.dataclass
class GraphQLPerfNode:
    id: str


class SchemaExtension[Ctx: GraphQLContext](StrawberrySchemaExtension):
    context_class: type[Ctx]

    def __init__(self, *, context_class: type[Ctx] | None = None, **kwargs):
        super().__init__(**kwargs)
        if getattr(self, 'context_class', None) is None:
            if context_class is None:
                raise ValueError('context_class must be set')
            self.context_class = context_class

    def get_ws_consumer(self) -> GraphQLWSConsumer:
        ctx = self.get_context()
        assert isinstance(ctx.request, GraphQLWSConsumer)
        return ctx.request

    def get_http_request(self) -> HttpRequest:
        ctx = self.get_context()
        assert isinstance(ctx.request, HttpRequest)
        return ctx.request

    def get_user(self) -> User | None:
        ctx = self.get_context()
        request = ctx.request
        if isinstance(request, HttpRequest):
            return user_or_none(request.user)
        scope: ASGICommonScope
        if isinstance(request, ChannelsRequest):
            scope = request.consumer.scope
        elif isinstance(request, GraphQLWSConsumer):
            scope = request.scope
        else:
            raise TypeError(f'Unknown request type: {type(request)}')
        return user_or_none(scope.get('user'))

    def get_session(self) -> SessionBase | None:
        ctx = self.get_context()
        request = ctx.request
        if isinstance(request, HttpRequest):
            return request.session

        scope: ASGICommonScope
        if isinstance(request, ChannelsRequest):
            scope = request.consumer.scope
        elif isinstance(request, GraphQLWSConsumer):
            scope = request.scope
        else:
            raise TypeError(f'Unknown request type: {type(request)}')
        return scope.get('session')

    def get_request_headers(self) -> Mapping[str, str]:
        ctx = self.get_context()
        if isinstance(ctx.request, (HttpRequest, ChannelsRequest)):
            return ctx.request.headers
        request = ctx.get_ws_consumer()
        headers_list = request.scope.get('headers', [])
        headers = {key.decode('utf8'): value.decode('utf8') for key, value in headers_list}
        return headers

    def get_context(self) -> Ctx:
        ctx = self.execution_context.context
        assert isinstance(ctx, self.context_class)
        return ctx

    def get_schema(self) -> Schema:
        assert isinstance(self.execution_context.schema, Schema)
        return self.execution_context.schema


class LoggingTracingExtension(SchemaExtension[GraphQLContext]):
    def get_log_context(self) -> dict[str, Any]:
        exec_ctx = self.execution_context
        log_ctx: dict[str, Any] = {}
        log_ctx['graphql.operation.name'] = exec_ctx.operation_name or '<unnamed>'
        log_ctx['graphql.operation.type'] = exec_ctx.operation_type.value
        return log_ctx

    def get_op_type(self, lower_case: bool = False) -> str:
        exec_ctx = self.execution_context
        op_type: str
        match exec_ctx.operation_type:
            case OperationType.QUERY:
                op_type = 'Query'
            case OperationType.MUTATION:
                op_type = 'Mutation'
            case OperationType.SUBSCRIPTION:
                op_type = 'Subscription'
            case _:
                op_type = 'Unknown'
        return op_type.lower() if lower_case else op_type

    def configure_root_transaction(self) -> None:
        scope = sentry_sdk.get_current_scope()
        transaction: Transaction | None = scope.transaction
        if not transaction:
            return
        exec_ctx = self.execution_context

        name = exec_ctx.operation_name or '<unnamed>'
        op_type = self.get_op_type(lower_case=True)
        name = f'{name}'

        transaction.op = f'http.graphql.{op_type}'
        transaction.name = name
        transaction.source = TransactionSource.CUSTOM
        transaction.set_data('method', self.get_op_type(lower_case=False))

        if sentry_sdk.get_client().spotlight:
            transaction.set_data('graphql.document', exec_ctx.query)
            transaction.set_data('graphql.variables', orjson.dumps(exec_ctx.variables or {}).decode('utf8'))

        ctx = self.get_context()
        if ctx.referer:
            transaction.set_tag('referer', ctx.referer)
        if ctx.user is not None:
            token_auth = ctx.get_token_auth()
            if token_auth is not None:
                transaction.set_tag('auth.method', token_auth.token_type)
            else:
                transaction.set_tag('auth.method', 'session')

    def on_validate(self) -> Generator[None]:
        """
        Configure the Sentry root transaction for the GraphQL operation.

        It's done at on_validate(), because by now the query has been parsed.
        """
        self.configure_root_transaction()
        yield None

    def on_execute(self) -> Generator[None]:
        exec_ctx = self.execution_context
        op_type = self.get_op_type()
        if exec_ctx.operation_name:
            span_name = f'{exec_ctx.operation_name}'
        else:
            span_name = f'{op_type} <unnamed>'

        start_span = sentry_sdk.start_span
        if (current_span := sentry_sdk.get_current_span()) and (transaction := current_span.containing_transaction):
            start_span = transaction.start_child

        with start_span(op='graphql.execute', name=span_name), logger.contextualize(**self.get_log_context()):
            _rich_traceback_omit = True
            yield None


class ExecutionCacheExtension[Ctx: GraphQLContext](SchemaExtension[Ctx], ABC):
    def log(self, level: str, msg, *args, depth: int = 0, **kwargs):
        exec_ctx = self.execution_context
        op_name = exec_ctx.operation_name or '<unnamed>'
        op_type = exec_ctx.operation_type.value
        log = logger.opt(depth=1 + depth)
        log.log(level, 'GQL [blue]%s[/] [bright_magenta]%s[/]: %s' % (op_type, op_name, msg), *args, **kwargs)

    def set_reason(self, reason: str) -> None:
        ctx = self.get_context()
        ctx.graphql_no_cache_reason = reason

    @abstractmethod
    def get_cache_key_parts(self) -> list[str] | None: ...

    def get_cache_key(self):
        exec_ctx = self.execution_context
        if not exec_ctx.query:
            return None

        if env_bool('DISABLE_GRAPHQL_CACHE', default=False):
            self.set_reason('cache disabled by env variable')
            return None
        if exec_ctx.operation_type != OperationType.QUERY:
            self.set_reason('not a query')
            return None
        if self.get_user() is not None:
            self.set_reason('user authenticated')
            return None

        other_parts = self.get_cache_key_parts()
        if other_parts is None:
            return None

        m = hashlib.md5(usedforsecurity=False)
        # Include build ID in the cache key to invalidate the cache when a new version is deployed.
        if build_id := get_deployment_build_id():
            m.update(build_id.encode('utf8'))

        if exec_ctx.operation_name:
            m.update(exec_ctx.operation_name.encode('utf8'))
        if exec_ctx.variables:
            m.update(json.dumps(exec_ctx.variables, sort_keys=True, ensure_ascii=True).encode('ascii'))
        m.update(exec_ctx.query.encode('utf8'))
        key = m.hexdigest()
        parts = [key]

        m = hashlib.md5(usedforsecurity=False)
        for part in other_parts:
            m.update(part.encode('utf8'))
        parts.append(m.hexdigest())
        return ':'.join(parts)

    def get_from_cache(self, key):
        return cache.get(key)

    def store_to_cache(self, key, result):
        return cache.set(key, result, timeout=30 * 60)

    def on_execute(self) -> Generator[None]:
        exec_ctx = self.execution_context
        ctx = self.get_context()

        def enter(id: str):  # noqa: ANN202
            return ctx.graphql_perf.exec_node(GraphQLPerfNode(id))

        span = sentry_sdk.get_current_span()

        with enter('get query cache key'):
            cache_key = self.get_cache_key()

        result: ExecutionResult | None = None
        if cache_key is not None:
            result = self.get_from_cache(cache_key)

        cache_reason = ''
        if cache_key is None:
            cache_res = 'disabled'
            color = 'bright_magenta'
            if ctx.graphql_no_cache_reason:
                cache_reason = f' ({ctx.graphql_no_cache_reason})'
        elif result is None:
            cache_res = 'miss'
            color = 'yellow'
        else:
            cache_res = 'hit'
            color = 'green'

        if span is not None:
            span.set_tag('cache', cache_res)

        self.log('INFO', 'cache [%s]%s[/]%s' % (color, cache_res, cache_reason))
        if result is not None:
            exec_ctx.result = result
        else:
            ctx.graphql_cache_key = cache_key

        yield None

    def get_results(self) -> dict[str, Any]:
        # Since there is no hook for extensions to process final results,
        # we need to do the cache store here.
        result = self.execution_context.result
        exec_ctx = self.get_context()
        if result is None or result.errors or exec_ctx.graphql_cache_key is None:
            return {}
        self.store_to_cache(exec_ctx.graphql_cache_key, result)
        return {}


class AuthenticationExtension[Ctx: GraphQLContext](SchemaExtension[Ctx], ABC):
    def on_operation(self) -> Generator[None]:
        ctx = self.get_context()
        token_auth = ctx.get_token_auth()
        if token_auth is not None and token_auth.error:
            raise StrawberryGraphQLError(str(token_auth.error))
        yield


@strawberry.directive(
    locations=[DirectiveLocation.QUERY, DirectiveLocation.MUTATION],
    name='locale',
    description='Select locale in which to return data',
)
def locale_directive(info, lang: Annotated[str, strawberry.argument(description='Selected language')]):
    pass


class Schema(ABC, GrapheneStrawberrySchema):
    @copy_signature(GrapheneStrawberrySchema.__init__)
    def __init__(self, *args, **kwargs: Any):
        directives = [
            *kwargs.pop('directives', []),
            locale_directive,
        ]
        kwargs['directives'] = directives
        kwargs['enable_federation_2'] = True
        super().__init__(*args, **kwargs)

    def get_extensions(self, sync: bool = False) -> list[StrawberrySchemaExtension]:
        from strawberry.extensions.parser_cache import ParserCache
        from strawberry.extensions.validation_cache import ValidationCache

        extensions = super().get_extensions(sync=sync)
        extensions.extend([
            ParserCache(maxsize=100),
            ValidationCache(maxsize=100),
        ])
        return extensions

    def process_errors(self, errors: list[GraphQLError], execution_context: ExecutionContext | None = None) -> None:
        for error in errors:
            path_str = '.'.join(str(part) for part in error.path) if error.path else 'unknown'
            logger.opt(exception=error.original_error).bind(graphql_path=path_str).error(error)
        if errors and execution_context and execution_context.query and settings.DEBUG:
            console = Console()
            syntax = Syntax(execution_context.query, 'graphql')
            console.print(syntax)
            if execution_context.variables:
                console.print('Variables:', execution_context.variables)
