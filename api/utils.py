from __future__ import annotations

import inspect
import re
from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from rest_framework.viewsets import ViewSetMixin


def camelcase_to_underscore(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

RegisteredAPIView = TypedDict('RegisteredAPIView', {
    'class': 'type[ViewSetMixin]',
    'name': str,
    'basename': NotRequired[str]
})


def register_view_helper(view_list: list[RegisteredAPIView], klass, name=None, basename=None):
    if not name:
        if klass.serializer_class:
            model = klass.serializer_class.Meta.model
        else:
            model = klass.queryset.model
        name = camelcase_to_underscore(model._meta.object_name)

    entry: RegisteredAPIView = {'class': klass, 'name': name}
    if basename is not None:
        entry['basename'] = basename

    view_list.append(entry)

    return klass


def register_view(klass, *args, **kwargs):
    frame = inspect.currentframe()
    if frame is None:
        raise ValueError("Failed to get the current frame")
    calling_module = inspect.getmodule(frame.f_back)

    all_views = getattr(calling_module, 'all_views', None)
    if all_views is None:
        assert calling_module is not None
        raise AttributeError(f"Module {calling_module.__name__} must define 'all_views' list")
    return register_view_helper(all_views, klass, *args, **kwargs)
