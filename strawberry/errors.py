from __future__ import annotations

from graphql import GraphQLError
from graphql.type import GraphQLResolveInfo
from strawberry.types import Info

type AnyInfo = Info | GraphQLResolveInfo


class ExecutionError(GraphQLError):
    message: str = 'An unexpected error occurred'

    def __init__(
        self, info: AnyInfo, message: str | None = None, code: str | None = None, original_error: Exception | None = None
    ):
        extensions = {}
        if code:
            extensions['code'] = code
        if message:
            self.message = message
        if isinstance(info, Info):
            info = info._raw_info
        super().__init__(self.message, nodes=info.field_nodes, original_error=original_error, extensions=extensions)


class PermissionDeniedError(ExecutionError):
    message: str = 'Permission denied'


class AuthenticationRequiredError(ExecutionError):
    message: str = 'Authentication required'


class NotFoundError(ExecutionError):
    message: str = 'Object not found'
