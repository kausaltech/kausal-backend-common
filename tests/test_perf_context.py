from dataclasses import dataclass

import pytest

from kausal_common.perf.perf_context import PerfContext, PerfKind

pytestmark = pytest.mark.django_db


@dataclass
class DummyNode:
    id: str


class SlowNode(DummyNode):
    pass


class FastNode(DummyNode):
    pass


def test_perf_span_attaches_to_current_parent():
    perf = PerfContext[DummyNode](supports_cache=False)
    perf.enabled = True
    node = DummyNode(id='node-a')

    with (
        perf as run,
        perf.exec_node(node),
        perf.exec_named(
            kind=PerfKind.DATASET,
            id='ds-1',
            op='cache_get',
            attrs={
                'dataset.id': 'ds-1',
                'cache.hit': True,
            },
        ) as span,
    ):
        assert span is not None
        span.set_attr('dataset.rows', 12)

    assert len(run.roots) == 1
    root = run.roots[0]
    assert len(root.children) == 1
    child = root.children[0]
    assert child.subject.kind == PerfKind.DATASET
    assert child.subject.id == 'ds-1'
    assert child.subject.op == 'cache_get'
    assert child.attrs == {
        'dataset.id': 'ds-1',
        'cache.hit': True,
        'dataset.rows': 12,
    }


def test_perf_span_without_parent_is_recorded_at_run_level():
    perf = PerfContext[DummyNode](supports_cache=False)
    perf.enabled = True

    with perf as run, perf.exec_named(kind=PerfKind.DATASET_REPO, id='dvc', op='load_all', attrs={'dataset.count': 3}):
        pass

    assert len(run.roots) == 1
    root = run.roots[0]
    assert root.subject.kind == PerfKind.DATASET_REPO
    assert root.subject.id == 'dvc'
    assert root.subject.op == 'load_all'
    assert root.attrs['dataset.count'] == 3


def test_span_summary_aggregates_by_kind_and_op_using_exclusive_time():
    perf = PerfContext[DummyNode](supports_cache=False)
    perf.enabled = True

    with perf as run:
        with perf.exec_named(kind=PerfKind.DATASET, id='ds-1', op='get'):
            pass
        with perf.exec_named(kind=PerfKind.DATASET, id='ds-2', op='get'):
            pass
        with perf.exec_named(kind=PerfKind.DATASET, id='ds-3', op='filter'):
            pass

    run.roots[0].started_at = 0
    run.roots[0].finished_at = 30
    run.roots[1].started_at = 40
    run.roots[1].finished_at = 60
    run.roots[2].started_at = 70
    run.roots[2].finished_at = 75

    summaries = {(summary.kind, summary.op): summary for summary in run.summarize_non_compute_spans()}

    assert set(summaries) == {
        (PerfKind.DATASET, 'get'),
        (PerfKind.DATASET, 'filter'),
    }
    get_summary = summaries[(PerfKind.DATASET, 'get')]
    assert get_summary.count == 2
    assert get_summary.total_exclusive_duration_ns == 50
    assert get_summary.avg_exclusive_duration_ns == 25
    assert get_summary.max_exclusive_duration_ns == 30


def test_node_class_summary_uses_local_attributable_time():
    perf = PerfContext[DummyNode](supports_cache=False)
    perf.enabled = True

    with perf as run:
        with perf.exec_node(SlowNode(id='slow-a')) as slow_a, perf.exec_named(kind=PerfKind.DATASET, id='ds-1', op='get'):
            pass
        with perf.exec_node(SlowNode(id='slow-b')):
            pass
        with perf.exec_node(FastNode(id='fast-a')):
            pass

    assert slow_a is not None
    slow_a.started_at = 0
    slow_a.finished_at = 100
    slow_a.children[0].started_at = 20
    slow_a.children[0].finished_at = 50
    run.roots[1].started_at = 110
    run.roots[1].finished_at = 150
    run.roots[2].started_at = 160
    run.roots[2].finished_at = 170

    summaries = run.summarize_node_classes()

    assert [summary.class_name for summary in summaries] == ['SlowNode', 'FastNode']
    assert summaries[0].count == 2
    assert summaries[0].total_local_duration_ns == 140
    assert summaries[0].avg_local_duration_ns == 70
    assert summaries[0].max_local_duration_ns == 100


def test_node_class_operation_mix_uses_local_subtree_without_child_node_compute():
    perf = PerfContext[DummyNode](supports_cache=False)
    perf.enabled = True

    with perf as run, perf.exec_node(SlowNode(id='slow-a')) as slow_a:
        with perf.exec_named(kind=PerfKind.DATASET, id='ds-1', op='get') as dataset_get:
            pass
        with perf.exec_named(kind=PerfKind.NODE, id='slow-a', op='generic.multiply') as multiply:
            pass
        with perf.exec_node(FastNode(id='child-fast')) as child_fast:
            pass

    assert slow_a is not None
    assert dataset_get is not None
    assert multiply is not None
    assert child_fast is not None

    slow_a.started_at = 0
    slow_a.finished_at = 100
    dataset_get.started_at = 20
    dataset_get.finished_at = 50
    multiply.started_at = 60
    multiply.finished_at = 70
    child_fast.started_at = 80
    child_fast.finished_at = 95

    summaries = {(summary.class_name, summary.kind, summary.op): summary for summary in run.summarize_node_class_operation_mix()}

    slow_compute = summaries[('SlowNode', PerfKind.NODE, 'compute')]
    assert slow_compute.total_duration_ns == 45
    slow_dataset = summaries[('SlowNode', PerfKind.DATASET, 'get')]
    assert slow_dataset.total_duration_ns == 30
    slow_multiply = summaries[('SlowNode', PerfKind.NODE, 'generic.multiply')]
    assert slow_multiply.total_duration_ns == 10
    assert ('SlowNode', PerfKind.NODE, 'compute') in summaries
    assert ('FastNode', PerfKind.NODE, 'compute') in summaries
