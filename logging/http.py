from contextlib import contextmanager
import os
from typing import cast

from django.http import HttpRequest
from loguru import logger
import nanoid
import sentry_sdk


ID_ALPHABET = '346789ABCDEFGHJKLMNPQRTUVWXYabcdefghijkmnpqrtwxyz'


class CorrelatedRequest(HttpRequest):
    correlation_id: str


@contextmanager
def start_request(request: HttpRequest):
    request = cast(CorrelatedRequest, request)
    request.correlation_id = nanoid.non_secure_generate(ID_ALPHABET, 8)
    cluster_name = os.getenv('CLUSTER_NAME', None)
    if cluster_name:
        sentry_sdk.set_tag('cluster', cluster_name)
    with logger.contextualize(**{"correlation_id": request.correlation_id}):
        yield
