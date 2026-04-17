from __future__ import annotations

import pytest

from kausal_common.datasets.schema import DataPointNode
from kausal_common.datasets.tests.factories import DataPointFactory

pytestmark = pytest.mark.django_db


def test_data_point_node_id_resolves_to_uuid() -> None:
    data_point = DataPointFactory.create()

    assert DataPointNode.resolve_id(data_point, info=None) == str(data_point.uuid)
