import asyncio
from typing import TYPE_CHECKING
from unittest.mock import patch

import strawberry as sb
from django.db import connection
from django.http import HttpRequest
from graphql import ExecutionResult

import pytest

from kausal_common.strawberry.context import GraphQLContext
from kausal_common.strawberry.extensions import ExecutionCacheExtension, LoggingTracingExtension

if TYPE_CHECKING:
    from collections.abc import Generator
    from unittest.mock import MagicMock

pytestmark = pytest.mark.django_db


@sb.type
class MetricsQuery:
    @sb.field
    def value(self, fail: bool = False) -> int:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.execute('SELECT 2')
        if fail:
            raise ValueError('resolver failed')
        return 2


@sb.type
class MetricsMutation:
    @sb.mutation
    def update(self) -> int:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return 1


class CachedExecution(ExecutionCacheExtension[GraphQLContext]):
    context_class = GraphQLContext

    def get_cache_key_parts(self) -> list[str]:
        return ['test']

    def get_cache_key(self) -> str:
        return 'metrics-test'

    def get_from_cache(self, key: str) -> ExecutionResult:
        return ExecutionResult(data={'value': 99})


@pytest.fixture
def metric_calls() -> Generator[tuple[MagicMock, MagicMock]]:
    with (
        patch('kausal_common.strawberry.extensions.metrics.distribution') as distribution,
        patch('kausal_common.strawberry.extensions.metrics.count') as count,
    ):
        yield distribution, count


@pytest.mark.parametrize(
    ('operation', 'name', 'kind', 'queries', 'outcome'),
    [
        ('query Test { value }', 'Test', 'query', 2, 'success'),
        ('{ value }', '<unnamed>', 'query', 2, 'success'),
        ('query Broken { value(fail: true) }', 'Broken', 'query', 2, 'error'),
        ('mutation Update { update }', 'Update', 'mutation', 1, 'success'),
    ],
)
def test_execute_metrics(
    metric_calls: tuple[MagicMock, MagicMock],
    operation: str,
    name: str,
    kind: str,
    queries: int,
    outcome: str,
) -> None:
    distribution, count = metric_calls
    schema = sb.Schema(
        query=MetricsQuery,
        mutation=MetricsMutation,
        extensions=[
            lambda: LoggingTracingExtension(context_class=GraphQLContext),
        ],
    )
    context = GraphQLContext(request=HttpRequest(), response=None)
    result = schema.execute_sync(operation, context_value=context)
    assert bool(result.errors) == (outcome == 'error')
    attrs = {'graphql.operation.type': kind, 'graphql.operation.name': name, 'graphql.operation.outcome': outcome}
    count.assert_called_once_with('graphql.execute.sql_queries', queries, attributes=attrs)
    duration, query_count = distribution.call_args_list
    assert duration.args[0] == 'graphql.execute.duration'
    assert duration.args[1] >= 0
    assert duration.kwargs == {'unit': 'millisecond', 'attributes': attrs}
    assert query_count.args == ('graphql.execute.sql_queries_per_operation', queries)


def test_cache_hit_has_no_execution_metrics(metric_calls: tuple[MagicMock, MagicMock]) -> None:
    schema = sb.Schema(
        query=MetricsQuery,
        extensions=[
            lambda: LoggingTracingExtension(context_class=GraphQLContext),
            CachedExecution,
        ],
    )
    result = schema.execute_sync('query Cached { value }', context_value=GraphQLContext(request=HttpRequest(), response=None))
    assert result.data == {'value': 99}
    for mock in metric_calls:
        mock.assert_not_called()


def test_async_execution_omits_thread_local_sql_counts(metric_calls: tuple[MagicMock, MagicMock]) -> None:
    schema = sb.Schema(query=MetricsQuery, extensions=[lambda: LoggingTracingExtension(context_class=GraphQLContext)])
    result = asyncio.run(schema.execute('{ __typename }', context_value=GraphQLContext(request=HttpRequest(), response=None)))
    assert not result.errors
    distribution, count = metric_calls
    distribution.assert_called_once()
    assert distribution.call_args.args[0] == 'graphql.execute.duration'
    count.assert_not_called()


@pytest.mark.parametrize('operation', ['query {', '{ nonexistent }'])
def test_invalid_operation_has_no_execution_metrics(metric_calls: tuple[MagicMock, MagicMock], operation: str) -> None:
    schema = sb.Schema(query=MetricsQuery, extensions=[lambda: LoggingTracingExtension(context_class=GraphQLContext)])
    result = schema.execute_sync(operation, context_value=GraphQLContext(request=HttpRequest(), response=None))
    assert result.errors
    for mock in metric_calls:
        mock.assert_not_called()


def test_product_metric_attributes(metric_calls: tuple[MagicMock, MagicMock]) -> None:
    class ProductContext(GraphQLContext):
        def get_metric_attributes(self) -> dict[str, str]:
            return {'instance.id': 'test-instance', 'instance.uuid': 'test-uuid'}

    schema = sb.Schema(query=MetricsQuery, extensions=[lambda: LoggingTracingExtension(context_class=ProductContext)])
    result = schema.execute_sync('{ value }', context_value=ProductContext(request=HttpRequest(), response=None))
    assert not result.errors
    for mock in metric_calls:
        for call in mock.call_args_list:
            assert call.kwargs['attributes']['instance.id'] == 'test-instance'
            assert call.kwargs['attributes']['instance.uuid'] == 'test-uuid'
