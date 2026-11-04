from __future__ import annotations

from django.contrib.auth.models import Group
from strawberry_django.fields.types import OperationInfo, OperationMessage

import pytest

from kausal_common.strawberry.mutations import MutationExtension

pytestmark = pytest.mark.django_db

Kind = OperationMessage.Kind


@pytest.mark.parametrize(
    ('kind', 'committed'),
    [
        (Kind.INFO, True),
        (Kind.WARNING, True),
        (Kind.ERROR, False),
        (Kind.PERMISSION, False),
        (Kind.VALIDATION, False),
    ],
)
def test_writes_roll_back_when_mutation_returns_an_error(kind: OperationMessage.Kind, committed: bool):
    # strawberry-django's `handle_django_errors` returns errors as `OperationInfo` instead of
    # raising them, so the extension must roll back the writes made before the error itself.
    def resolver(_source, _info, **_kwargs):
        Group.objects.create(name='created-by-mutation')
        return OperationInfo(messages=[OperationMessage(kind=kind, message='Something happened')])

    ret = MutationExtension().resolve(resolver, None, None)  # type: ignore[arg-type]

    assert isinstance(ret, OperationInfo)
    assert Group.objects.filter(name='created-by-mutation').exists() is committed


def test_writes_are_committed_on_success():
    def resolver(_source, _info, **_kwargs):
        return Group.objects.create(name='created-by-mutation')

    ret = MutationExtension().resolve(resolver, None, None)  # type: ignore[arg-type]

    assert isinstance(ret, Group)
    assert Group.objects.filter(name='created-by-mutation').exists()
