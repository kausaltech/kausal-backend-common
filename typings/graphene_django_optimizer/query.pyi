from typing import Any

from django.db.models.query import Prefetch, QuerySet
from graphql import GraphQLObjectType, GraphQLResolveInfo, GraphQLSchema, InlineFragmentNode

def query[QS: QuerySet[Any]](queryset: QS, info: GraphQLResolveInfo, **options) -> QS:
    """
    Automatically optimize queries.

    Arguments:
        - queryset (Django QuerySet object) - The queryset to be optimized
        - info (GraphQL GraphQLResolveInfo object) - This is passed by the graphene-django resolve methods
        - **options - optimization options/settings
            - disable_abort_only (boolean) - in case the objecttype contains any extra fields,
                                             then this will keep the "only" optimization enabled.
    """

class QueryOptimizer:
    """
    Automatically optimize queries.
    """

    root_info: GraphQLResolveInfo
    disable_abort_only: bool
    def __init__(self, info: GraphQLResolveInfo, **options) -> None: ...
    def optimize[QS: QuerySet[Any]](self, queryset: QS) -> QS: ...
    def handle_inline_fragment(
        self,
        selection: InlineFragmentNode,
        schema: GraphQLSchema,
        possible_types: list[GraphQLObjectType],
        store: QueryOptimizerStore,
    ) -> None: ...
    def handle_fragment_spread(self, store: QueryOptimizerStore, name: str, field_type: GraphQLObjectType) -> None: ...

class QueryOptimizerStore:
    select_list: list[str]
    prefetch_list: list[str | Prefetch]
    only_list: list[str]
    disable_abort_only: bool
    def __init__(self, disable_abort_only: bool = False) -> None: ...
    def select_related(self, name: str, store: QueryOptimizerStore) -> None: ...
    def prefetch_related(self, name: str, store: QueryOptimizerStore, queryset: QuerySet[Any]) -> None: ...
    def only(self, field: str) -> None: ...
    def abort_only_optimization(self) -> None: ...
    def optimize_queryset(self, queryset: QuerySet[Any]) -> QuerySet[Any]: ...
    def append(self, store) -> None: ...
