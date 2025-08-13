from __future__ import annotations

from typing import Sequence

from wagtail.admin.views.generic.base import BaseObjectMixin


def _monkeypatch_one_class(kls: type) -> None:
    kls.__class_getitem__ = classmethod(lambda cls, *args, **kwargs: cls)  # type: ignore


def _monkeypath_init() -> None:
    import django_stubs_ext
    from django.db.models import ManyToManyField
    from django.db.models.fields.json import JSONField
    from graphene import ObjectType
    from modelcluster.fields import ParentalKey, ParentalManyToManyField
    from wagtail.admin.panels import Panel
    from wagtail.admin.viewsets.model import ModelViewSet
    from wagtail.blocks.base import Block
    from wagtail.permission_policies.base import BasePermissionPolicy

    from treebeard.models import Node

    extra_classes: list[type] = [
        ModelViewSet, ParentalKey, ParentalManyToManyField,
        JSONField, ManyToManyField, Node,
        Panel, Panel.BoundPanel, BaseObjectMixin,
        BasePermissionPolicy, ObjectType,
        Block
    ]

    try:
        from generic_chooser.views import ChooserCreateTabMixin, ChooserListingTabMixin, ChooserMixin, ChooserViewSet
        extra_classes.append(ChooserMixin)
        extra_classes.append(ChooserViewSet)
        extra_classes.append(ChooserCreateTabMixin)
        extra_classes.append(ChooserListingTabMixin)
    except ImportError:
        pass

    django_stubs_ext.monkeypatch(extra_classes=extra_classes, include_builtins=True)


def monkeypatch_generic_support(kls: type | Sequence[type] | None = None):
    if kls is None:
        _monkeypath_init()
        return
    if isinstance(kls, type):
        kls = [kls]
    for k in kls:
        _monkeypatch_one_class(k)
