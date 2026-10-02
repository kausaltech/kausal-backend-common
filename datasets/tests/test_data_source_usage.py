from __future__ import annotations

import pytest

from kausal_common.datasets.models import DatasetSourceReference, DataSource
from kausal_common.datasets.tests.factories import DataPointFactory, DatasetFactory
from kausal_common.datasets.wagtail_hooks import DataSourceUsage

pytestmark = pytest.mark.django_db


def test_usage_groups_references_by_citing_dataset():
    cited_by_points = DatasetFactory.create()
    cited_by_both = DatasetFactory.create()
    DatasetFactory.create()  # cites nothing
    source = DataSource.objects.create(
        scope_content_type=cited_by_points.scope_content_type, scope_id=cited_by_points.scope_id, name='Census'
    )
    for _ in range(3):
        DatasetSourceReference.objects.create(data_point=DataPointFactory.create(dataset=cited_by_points), data_source=source)
    DatasetSourceReference.objects.create(dataset=cited_by_both, data_source=source)
    DatasetSourceReference.objects.create(data_point=DataPointFactory.create(dataset=cited_by_both), data_source=source)

    usage = DataSourceUsage(source)

    citations = {citation.dataset.pk: (citation.data_points, citation.dataset_level) for citation in usage.citations}
    assert citations == {cited_by_points.pk: (3, False), cited_by_both.pk: (1, True)}
    assert usage.count() == 2
    assert usage.is_protected


def test_an_uncited_source_is_unprotected():
    dataset = DatasetFactory.create()
    source = DataSource.objects.create(scope_content_type=dataset.scope_content_type, scope_id=dataset.scope_id, name='Unused')

    usage = DataSourceUsage(source)

    assert usage.count() == 0
    assert not usage.is_protected
