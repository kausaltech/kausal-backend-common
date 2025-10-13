from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Annotated, Any

import strawberry
from django.conf import settings
from graphql import DirectiveLocation, GraphQLError

import sentry_sdk
from loguru import logger
from rich.console import Console
from rich.syntax import Syntax

from kausal_common.graphene.merged_schema import GrapheneStrawberrySchema
from kausal_common.models.types import copy_signature

if TYPE_CHECKING:
    from strawberry.extensions import SchemaExtension as StrawberrySchemaExtension
    from strawberry.types import ExecutionContext


logger = logger.bind(name='graphql', markup=True)


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
        errors_sent = 0
        for error in errors:
            path_str = '.'.join(str(part) for part in error.path) if error.path else 'unknown'
            logger.opt(exception=error.original_error).bind(graphql_path=path_str).error(error)
            if error.original_error and errors_sent < 5:
                sentry_sdk.capture_exception(error.original_error)
                errors_sent += 1

        if errors and execution_context and execution_context.query and settings.DEBUG:
            console = Console()
            syntax = Syntax(execution_context.query, 'graphql')
            console.print(syntax)
            if execution_context.variables:
                console.print('Variables:', execution_context.variables)
