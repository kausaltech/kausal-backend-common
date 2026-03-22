from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from typing_extensions import TypedDict

from django.http import HttpRequest
from django.utils.text import slugify
from graphql import GraphQLError

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Iterable

    from strawberry.http import GraphQLHTTPResponse, GraphQLRequestData

    from kausal_common.strawberry.context import GraphQLContext


def format_error(error: Exception):
    if isinstance(error, GraphQLError):
        return error.formatted
    return {'message': str(error)}


DEFAULT_STORE_DIR = Path('query-store')


def capture_query(
    context: GraphQLContext,
    headers: list[str],
    data: GraphQLRequestData,
    response: GraphQLHTTPResponse,
    exec_time: float | None = None,
    instance_id: str | None = None,
    store_dir: Path = DEFAULT_STORE_DIR,
):
    if not data.operation_name:
        return
    request_headers = context.get_request_headers()
    if isinstance(context.request, HttpRequest):
        session = context.request.session
    else:
        session = context.get_scope().get('session')
    has_session = False
    if session and session.session_key:
        has_session = True

    out = dict(
        headers={hdr: request_headers.get(hdr) for hdr in headers},
        operation_name=data.operation_name,
        query=data.query,
        variables=data.variables,
        response=response,
        execution_time=exec_time,
        has_session=has_session,
    )
    store_dir.mkdir(exist_ok=True)
    instance_id_part = ''
    if instance_id:
        instance_id_part = f'-{instance_id}'
    op_name = slugify(data.operation_name) or 'unnamed'
    used_indices = {int(p.name[:4]) for p in store_dir.glob('????-*.json') if p.name[:4].isdigit()}
    index = 1
    while index in used_indices:
        index += 1
    path = store_dir / f'{index:04d}{instance_id_part}-{op_name}.json'
    logger.info('Capturing GraphQL query and response to %s' % path)
    with path.open('w') as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=False))


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
        assert not messages, 'No error messages in operation data'
    keys.discard('messages')
    assert not keys, f'Unexpected keys in operation data: {keys}'

    incoming_message_set = set((msg['kind'], msg['message']) for msg in op_data['messages'])

    def msg_to_tuple(msg: OperationMessage | OperationMessageDict) -> tuple[str, str]:
        if isinstance(msg, OperationMessage):
            return msg.kind, msg.message
        return msg['kind'], msg['message']

    required_message_set = set(msg_to_tuple(msg) for msg in messages)
    assert incoming_message_set == required_message_set
