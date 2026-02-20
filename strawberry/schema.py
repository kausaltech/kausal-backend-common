from __future__ import annotations

import sys
from abc import ABC
from typing import TYPE_CHECKING, Annotated, Any, override

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
def locale_directive(info: strawberry.Info, lang: Annotated[str, strawberry.argument(description='Selected language')]):  # pyright: ignore[reportUnusedParameter]
    # Query-level directives do not yet execute in Strawberry
    pass


class Schema(ABC, GrapheneStrawberrySchema):
    @copy_signature(GrapheneStrawberrySchema.__init__)
    def __init__(self, *args, **kwargs: Any):
        FEDERATION_VERSIONS: Any
        try:
            from strawberry.federation.versions import FEDERATION_VERSIONS  # type: ignore
        except ImportError:
            FEDERATION_VERSIONS = None

        directives = [
            *kwargs.pop('directives', []),
            locale_directive,
        ]
        kwargs['directives'] = directives
        if FEDERATION_VERSIONS is None:
            kwargs['enable_federation_2'] = True
        else:
            kwargs['federation_version'] = '2.11'
        super().__init__(*args, **kwargs)

    @override
    def get_extensions(self, sync: bool = False) -> list[StrawberrySchemaExtension]:
        from strawberry.extensions.parser_cache import ParserCache
        from strawberry.extensions.validation_cache import ValidationCache

        extensions = super().get_extensions(sync=sync)
        extensions.extend([
            ParserCache(maxsize=100),
            ValidationCache(maxsize=100),
        ])
        return extensions

    @override
    def process_errors(self, errors: list[GraphQLError], execution_context: ExecutionContext | None = None) -> None:
        errors_sent = 0
        errors_printed = 0
        for error in errors:
            path_str = '.'.join(str(part) for part in error.path) if error.path else 'unknown'
            if not isinstance(error.original_error, GraphQLError):
                logger.opt(exception=error.original_error).bind(graphql_path=path_str).error(error)
                errors_printed += 1
            if error.original_error and errors_sent < 5:
                sentry_sdk.capture_exception(error.original_error)
                errors_sent += 1

        print_to_console = settings.DEBUG or ('pytest' in sys.modules)

        if errors and execution_context and execution_context.query and print_to_console and errors_printed:
            console = Console()
            syntax = Syntax(execution_context.query, 'graphql')
            console.print(syntax)
            if execution_context.variables:
                console.print('Variables:', execution_context.variables)
