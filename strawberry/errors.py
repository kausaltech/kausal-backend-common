from __future__ import annotations

from typing import TYPE_CHECKING

from graphql import GraphQLError
from strawberry.types import Info

if TYPE_CHECKING:
    from kausal_common.strawberry.helpers import InfoType


class ExecutionError(GraphQLError):
    message: str = 'An unexpected error occurred'

    def __init__(
        self,
        info: InfoType,
        message: str | None = None,
        code: str | None = None,
        original_error: Exception | None = None,
    ):
        extensions = {}
        if code:
            extensions['code'] = code
        if message:
            self.message = message
        if isinstance(info, Info):
            resolve_info = info._raw_info
        else:
            resolve_info = info
        super().__init__(self.message, nodes=resolve_info.field_nodes, original_error=original_error, extensions=extensions)


class GraphQLValidationError(ExecutionError):
    message: str = 'Validation error'


class PermissionDeniedError(ExecutionError):
    message: str = 'Permission denied'


class AuthenticationRequiredError(ExecutionError):
    message: str = 'Authentication required'


class NotFoundError(ExecutionError):
    message: str = 'Object not found'
