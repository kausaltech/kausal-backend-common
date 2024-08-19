from __future__ import annotations

from typing import Sequence

from wagtail.admin.views.generic.base import BaseObjectMixin


def _monkeypatch_one_class(kls: type) -> None:
    kls.__class_getitem__ = classmethod(lambda cls, *args, **kwargs: cls)  # type: ignore


def _monkeypath_init() -> None:
    import django_stubs_ext
    from django.db.models import ManyToManyField
    from django.db.models.fields.json import JSONField
    from modelcluster.fields import ParentalKey, ParentalManyToManyField
    from wagtail.admin.panels import Panel
    from wagtail.admin.viewsets.model import ModelViewSet
    from wagtail.permission_policies.base import ModelPermissionPolicy

    from treebeard.models import Node

    django_stubs_ext.monkeypatch([
        ModelViewSet, ModelPermissionPolicy,
        ParentalKey, ParentalManyToManyField,
        JSONField, ManyToManyField, Node,
        Panel, Panel.BoundPanel, BaseObjectMixin,
    ], include_builtins=True)


def monkeypatch_generic_support(kls: type | Sequence[type] | None = None):
    if kls is None:
        _monkeypath_init()
        return
    if isinstance(kls, type):
        kls = [kls]
    for k in kls:
        _monkeypatch_one_class(k)
