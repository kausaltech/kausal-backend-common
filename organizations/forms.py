from __future__ import annotations

from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField
from django.utils.translation import gettext_lazy as _

from treebeard.mp_tree import MP_NodeQuerySet
from wagtailgeowidget.helpers import geosgeometry_str_to_struct
from wagtailgeowidget.widgets import GoogleMapsField

from kausal_common.const import IS_PATHS, IS_WATCH

from .models import Node

if IS_PATHS:
    from admin_site.forms import PathsAdminModelForm as ModelForm
elif IS_WATCH:
    from admin_site.forms import WatchAdminModelForm as ModelForm
else:
    raise RuntimeError('No admin form found')


class NodeChoiceField[M: Node[MP_NodeQuerySet[Any]]](ModelChoiceField[M]):
    def label_from_instance(self, obj):
        depth_line = '-' * (obj.get_depth() - 1)
        label = obj.tree_label
        return f'{depth_line} {label}'


class OrganizationLocationField(forms.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault('label', _('location'))
        kwargs.setdefault('required', False)
        kwargs.setdefault('widget', GoogleMapsField(srid=4326, id_prefix='id_'))
        super().__init__(**kwargs)

    def clean(self, value) -> tuple[float, float] | None:
        value = super().clean(value)
        if not value:
            return None

        coordinates = geosgeometry_str_to_struct(value)
        if coordinates is None or int(coordinates['srid']) != 4326:
            raise ValidationError(_('Enter a valid location.'), code='invalid')

        longitude = float(coordinates['x'])
        latitude = float(coordinates['y'])
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValidationError(_('Enter a valid location.'), code='invalid')
        return longitude, latitude

    def prepare_value(self, value):
        if isinstance(value, tuple):
            longitude, latitude = value
            return f'SRID=4326;POINT({longitude} {latitude})'
        return super().prepare_value(value)


class OrganizationLocationFormMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance is not None and instance.latitude is not None and instance.longitude is not None:
            self.initial['coordinate_location'] = self.fields['coordinate_location'].prepare_value((
                instance.longitude,
                instance.latitude,
            ))

    def clean(self):
        cleaned_data = super().clean() or {}
        if 'coordinate_location' not in cleaned_data:
            return cleaned_data

        coordinates = cleaned_data['coordinate_location']
        if coordinates is None:
            self.instance.longitude = None
            self.instance.latitude = None
        else:
            self.instance.longitude, self.instance.latitude = coordinates
        return cleaned_data


class NodeForm[M: Node[Any]](ModelForm[M]):
    parent: NodeChoiceField[M] = NodeChoiceField[M](required=False, queryset=None)

    def __init__(self, *args, **kwargs):
        parent_required = kwargs.pop('parent_required', False)
        parent_choices = kwargs.pop('parent_choices', self._meta.model.objects.all())
        super().__init__(*args, **kwargs)
        self.fields['parent'] = NodeChoiceField(required=parent_required, queryset=parent_choices)

        instance = kwargs.get('instance')

        if instance:
            parent = instance.get_parent()
            if parent:
                self.fields['parent'].initial = parent

    def clean_parent(self):
        parent = self.cleaned_data['parent']
        if (parent is not None and parent == self.instance) or parent in self.instance.get_descendants():
            raise ValidationError(_('A node cannot be moved under itself in the hierarchy.'), code='invalid_parent')
        return parent

    def save(self, commit: bool = True) -> M:
        instance: M = super().save(commit=False)

        parent = self.cleaned_data['parent']

        if not commit:
            return instance

        if instance.pk is None:  # creating a new node
            if parent is None:
                instance = self._meta.model.add_root(instance=instance)
            else:
                instance = parent.add_child(instance=instance)
        else:
            instance.save()
            if instance.get_parent() != parent:
                if parent is None:
                    # Make instance another root
                    previous_root = instance.get_root()
                    instance.move(previous_root, pos='last-sibling')
                else:
                    instance.move(parent, pos='last-child')
                # Need to reload instance after move.
                # Note that instance.refresh_from_db() won't cut it because get_parent() will then still return the old
                # parent if we don't call it with `update=True`.
                # From treebeard docs:
                # django-treebeard uses Django raw SQL queries for some write operations, and raw queries don't update
                # the objects in the ORM since it's being bypassed. Because of this, if you have a node in memory and
                # plan to use it after a tree modification (adding/removing/moving nodes), you need to reload it.
                mgr = instance._meta.default_manager
                assert mgr is not None
                instance = mgr.get(pk=instance.pk)
                # The following would also seem to work, but is more likely to break.
                # instance.refresh_from_db()
                # instance.get_parent(update=True)
        return instance
