from __future__ import annotations

import json
from collections.abc import Mapping

from django import http
from django.db import connection

from loguru import logger

QUERIES_TO_IGNORE = ['BEGIN', 'COMMIT', 'ROLLBACK']


class LogQueryCountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _get_graphql_operation_name(self, request) -> str:
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            pass
        except http.RawPostDataException:
            pass
        except Exception as e:
            logger.error(e)
        else:
            if isinstance(body, Mapping) and 'operationName' in body:
               return str(body.get('operationName', '-'))
        return '-'


    def __call__(self, request):
        response = self.get_response(request)
        queries = [q for q in connection.queries if q['sql'] not in QUERIES_TO_IGNORE]

        sqltime = 0.0
        for query in queries:
            sqltime += float(query["time"])
        sqltime = round(1000 * sqltime)

        query_count = len(queries)
        if query_count == 0:
            return response
        if query_count >= 100:
            level = 'ERROR'
        elif query_count >= 50:
            level = 'WARNING'
        elif query_count >= 20:
            level = 'INFO'
        else:
            level = 'DEBUG'

        graphql_operation_name = self._get_graphql_operation_name(request)
        logger.log(level, f"⛁ {query_count} SQL queries took {sqltime} ms {request.path} {graphql_operation_name}")
        return response
