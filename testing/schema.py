from __future__ import annotations

from pathlib import Path

import strawberry
from django.conf import settings

from kausal_common.deployment import test_mode_enabled
from kausal_common.strawberry.registry import register_strawberry_type


class TestModeNotEnabledError(Exception):
    def __init__(self, message: str | None = None):
        if not message:
            message = 'Test mode is not enabled'
        super().__init__(message)


class CoverageNotEnabledError(Exception):
    def __init__(self, message: str | None = None):
        if not message:
            message = 'Coverage is not enabled'
        super().__init__(message)


COVERAGE_DATA_PATH = Path('/tmp') / 'coverage'  # noqa: S108
COVERAGE_XML_PATH = COVERAGE_DATA_PATH / 'coverage.xml'


@register_strawberry_type
@strawberry.type
class CoverageOutput:
    @strawberry.field
    def xml(self) -> str | None:
        if not COVERAGE_XML_PATH.exists():
            return None
        return COVERAGE_XML_PATH.read_text(encoding='utf-8')


@register_strawberry_type
@strawberry.type
class TestModeMutation:
    @strawberry.mutation
    def start_coverage_tracking(self) -> bool:
        from coverage import Coverage

        cov = Coverage(
            data_file=str(COVERAGE_DATA_PATH / 'coverage'),
            data_suffix='sqlite',
            branch=True,
            concurrency='thread',
            messages=True,
        )
        cov.start()

        return True

    @strawberry.mutation
    def stop_coverage_tracking(self) -> CoverageOutput:
        from coverage import Coverage

        cov = Coverage.current()
        if cov is None:
            raise CoverageNotEnabledError()
        cov.stop()
        cov.xml_report(outfile=str(COVERAGE_XML_PATH))
        return CoverageOutput()

    @strawberry.mutation
    def switch_coverage_context(self, context: str) -> bool:
        from coverage import Coverage

        cov = Coverage.current()
        if cov is None:
            raise CoverageNotEnabledError()
        cov.switch_context(context)
        return True


@strawberry.type
class TestModeMutations:
    @strawberry.field
    def test_mode(self) -> TestModeMutation:
        if not test_mode_enabled():
            raise TestModeNotEnabledError()
        return TestModeMutation()
