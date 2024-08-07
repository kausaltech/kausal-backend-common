import os
from contextlib import contextmanager
from typing import cast

import nanoid
import sentry_sdk
from django.http import HttpRequest
from loguru import logger

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
    node_name = os.getenv("NODE_NAME", None)
    if node_name:
        sentry_sdk.set_tag("cluster_node", node_name)
    pod_name = os.getenv("POD_NAME", None)
    if pod_name:
        sentry_sdk.set_tag("cluster_pod", pod_name)
    with logger.contextualize(correlation_id=request.correlation_id):
        yield
