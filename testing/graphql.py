from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from typing_extensions import TypedDict

from django.utils.text import slugify
from graphene_django.views import GraphQLView
from graphql import GraphQLError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.http import HttpRequest

counter = 0

def format_error(error: Exception):
    if isinstance(error, GraphQLError):
        return error.formatted
    return {"message": str(error)}


def capture_query(request: HttpRequest, headers: list[str], data: dict, response: str, status_code: int, exec_time: float):
    global counter  # noqa: PLW0603

    query, variables, operation_name, _id = GraphQLView.get_graphql_params(request, data)
    if not operation_name:
        return
    out = dict(
        headers={hdr: request.headers.get(hdr) for hdr in headers},
        operation_name=operation_name,
        query=query,
        variables=variables,
        response=json.loads(response),
        response_code=status_code,
        execution_time=exec_time,
    )
    with Path('query-store/%04d-%s.json'% (counter, slugify(operation_name))).open('w') as f:
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
