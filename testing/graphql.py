from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from typing_extensions import TypedDict

from django.utils.text import slugify
from graphql import GraphQLError

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Iterable

    from strawberry.http import GraphQLHTTPResponse, GraphQLRequestData

    from kausal_common.strawberry.context import GraphQLContext

counter = 0

def format_error(error: Exception):
    if isinstance(error, GraphQLError):
        return error.formatted
    return {"message": str(error)}


def capture_query(
    context: GraphQLContext,
    headers: list[str],
    data: GraphQLRequestData,
    response: GraphQLHTTPResponse,
    exec_time: float | None = None,
):
    global counter  # noqa: PLW0603

    if not data.operation_name:
        return
    request_headers = context.get_request_headers()
    out = dict(
        headers={hdr: request_headers.get(hdr) for hdr in headers},
        operation_name=data.operation_name,
        query=data.query,
        variables=data.variables,
        response=response,
        execution_time=exec_time,
    )
    store_dir = Path('query-store')
    store_dir.mkdir(exist_ok=True)
    path = store_dir / Path('%04d-%s.json'% (counter, slugify(data.operation_name)))
    logger.info('Capturing GraphQL query and response to %s' % path)
    with path.open('w') as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=False))
    counter += 1


@dataclass
class OperationMessage:
    kind: Literal['VALIDATION', 'ERROR']
    message: str

class OperationMessageDict(TypedDict):
    kind: Literal['VALIDATION', 'ERROR']
    message: str


def assert_operation_errors(op_data: dict[str, Any], messages: Iterable[OperationMessage | OperationMessageDict]):
    keys = set(op_data.keys())
    keys.discard('__typename')
    if 'messages' not in keys:
        assert not messages, "No error messages in operation data"
    keys.discard('messages')
    assert not keys, f"Unexpected keys in operation data: {keys}"

    incoming_message_set = set((msg['kind'], msg['message']) for msg in op_data['messages'])
    def msg_to_tuple(msg: OperationMessage | OperationMessageDict) -> tuple[str, str]:
        if isinstance(msg, OperationMessage):
            return msg.kind, msg.message
        return msg['kind'], msg['message']
    required_message_set = set(msg_to_tuple(msg) for msg in messages)
    assert incoming_message_set == required_message_set
