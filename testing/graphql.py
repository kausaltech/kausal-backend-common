import json
from django.http import HttpRequest
from django.utils.text import slugify
from graphene_django.views import GraphQLView
from graphql import GraphQLError


counter = 0

def format_error(error: Exception):
    if isinstance(error, GraphQLError):
        return error.formatted
    return {"message": str(error)}


def capture_query(request: HttpRequest, headers: list[str], data: dict, response: str, status_code: int, exec_time: float):
    global counter

    query, variables, operation_name, id = GraphQLView.get_graphql_params(request, data)
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
    with open('query-store/%04d-%s.json'% (counter, slugify(operation_name)), 'w') as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=False))
    counter += 1
