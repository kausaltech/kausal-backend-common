from __future__ import annotations

import typing
from typing import Any

from django.db import models
from django.db.models.base import Model
from django.db.models.query import QuerySet
from rest_framework import response, serializers, status, viewsets
from rest_framework.exceptions import ValidationError

if typing.TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from kausal_common.const import IS_PATHS, IS_WATCH
    if IS_PATHS:
        from paths.types import PathsAPIRequest as APIRequest
    elif IS_WATCH:
        from aplans.types import WatchAPIRequest as APIRequest


class BulkSerializerValidationInstanceMixin:
    def run_validation(self, data: dict[str, Any]):
        if self.parent and self.instance is not None:
            assert isinstance(self.instance, models.query.QuerySet)
            self._instance = self.parent.objs_by_id.get(data['id'])
        else:
            self._instance = self.instance
        return super().run_validation(data)


class BulkListSerializer[M: Model](serializers.ListSerializer[QuerySet[M]]):
    child: serializers.ModelSerializer[M]
    # instance: models.QuerySet[M] | None
    update_lookup_field = 'id'
    _refresh_cache: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._refresh_cache = False

    def to_internal_value(self, data):
        id_attr = self.update_lookup_field
        errors = []
        qs = self.instance
        obj_ids = set()
        for item in data:
            obj_id = item.get(id_attr)
            if obj_id:
                if qs is None:
                    errors.append({id_attr: "Must not set attribute"})
                    continue
                obj_ids.add(obj_id)
            elif qs is not None:
                errors.append({id_attr: "Attribute missing"})
                continue
        if any(errors):
            raise ValidationError(errors)

        if qs is not None:
            objs_by_id = {}
            self.obj_ids = []
            qs = qs.filter(**{'%s__in' % id_attr: obj_ids})
            for obj in qs:
                # Get serialized value of `id_attr`. We need the serialized value here and not the plain attribute value
                # obtainable by `getattr(obj, id_attr)` because `objs_by_id` will be used to find objects referenced by
                # their ID. This is a problem if the serialization of the ID attribute is different from the plain
                # attribute value, which happens, e.g., for UUIDs. Then we need to make sure that we never mix the two
                # representations, otherwise we may be unable to find the right object. Let's use the convention that we
                # always use serialized values to refer to objects.
                id_field = self.child.fields[id_attr]
                attr_value = id_field.get_attribute(obj)
                id = id_field.to_representation(attr_value)
                objs_by_id[id] = obj
            seen_ids = set()
            for item in data:
                obj_id = item[id_attr]
                self.obj_ids.append(obj_id)
                if obj_id not in objs_by_id:
                    errors.append({id_attr: "Unable to find object"})
                    continue
                if obj_id in seen_ids:
                    errors.append({id_attr: "Duplicate value"})
                    continue
                seen_ids.add(obj_id)
                errors.append({})  # no error for this item
            self.objs_by_id = objs_by_id

        if any(errors):
            raise ValidationError(errors)

        return super().to_internal_value(data)

    def _handle_updates(self, update_ops: Mapping[type[M], Sequence[tuple[M, Sequence[str]]]]) -> None:
        for model, ops in update_ops.items():
            # TODO: build the deferred operations structure
            # like this from the get go

            # If the same instance occurs multiple times (perhaps with some fields different) in `ops`, then this
            # will do nasty stuff. (If we use an instance as a dict key, only the PK matters, so the other values
            # could different but we'd still map to the same value). We merge all ops with the same instance PK by
            # only taking the latest instance having that PK and unifying the fields.
            fields_for_instance: dict[M, frozenset[str]] = {}
            for instance, fields in ops:
                frozen_fields = frozenset(fields)  # merge duplicate fields
                if instance in fields_for_instance.keys():
                    # Actually not necessarily the exact instance occurs, but one with the same PK
                    existing_fields = fields_for_instance.pop(instance)
                    fields_for_instance[instance] = existing_fields | frozen_fields
                else:
                    fields_for_instance[instance] = frozen_fields
            instances_for_fields: dict[frozenset[str], list[M]] = {}
            for instance, fr_fields in fields_for_instance.items():
                instances_for_fields.setdefault(fr_fields, []).append(instance)
            for fr_fields, instances in instances_for_fields.items():
                model._default_manager.bulk_update(instances, fr_fields)

    def _handle_deletes(self, delete_ops) -> None:
        for model in delete_ops.keys():
            pks = [o[0].pk for o in delete_ops[model]]
            model.objects.filter(pk__in=pks).delete()

    def _handle_creates(self, create_ops) -> None:
        for model in create_ops.keys():
            instances = [o[0] for o in create_ops[model]]
            model.objects.bulk_create(instances)

    def _handle_set_related(self, set_ops) -> None:
        for model in set_ops.keys():
            # TODO: actually batch this up
            for instance, field_name, related_ids in set_ops[model]:
                setattr(instance, field_name, related_ids)

    def _execute_deferred_operations(self, ops) -> None:
        grouped_by_operation_and_model: dict[str, dict[type[M], list[tuple[M, list[str]]]]] = {}
        for operation, obj, *rest in ops:
            grouped_by_operation_and_model.setdefault(
                operation, {},
            ).setdefault(
                type(obj), [],
            ).append(
                tuple([obj] + rest),
            )
        self._handle_updates(grouped_by_operation_and_model.get('update', {}))
        self._handle_deletes(grouped_by_operation_and_model.get('delete', {}))
        self._handle_creates(grouped_by_operation_and_model.get('create', {}))
        self._handle_creates(grouped_by_operation_and_model.get('create_and_set_related', {}))
        self._handle_set_related(grouped_by_operation_and_model.get('create_and_set_related', {}))
        self._handle_set_related(grouped_by_operation_and_model.get('set_related', {}))

    def update(self, queryset, all_validated_data):
        updated_data = []
        try:
            self.child.enable_deferred_operations()
            deferred = True
        except AttributeError:
            deferred = False
        for obj_id, obj_data in zip(self.obj_ids, all_validated_data, strict=True):
            obj = self.objs_by_id[obj_id]
            updated_data.append(self.child.update(obj, obj_data))
        if deferred:
            ops = self.child.get_deferred_operations()
            self._execute_deferred_operations(ops)
        self._refresh_cache = True
        return updated_data

    def create(self, validated_data):
        try:
            self.child.enable_deferred_operations()
            deferred = True
        except AttributeError:
            deferred = False
        result = [self.child.create(attrs) for attrs in validated_data]
        if deferred:
            ops = self.child.get_deferred_operations()
            self._execute_deferred_operations(ops)
        self._refresh_cache = True
        return result

    def to_representation(self, value):
        if self._refresh_cache:
            if hasattr(self.child, 'initialize_cache_context'):
                self.child.initialize_cache_context()
                self._refresh_cache = False
        return super().to_representation(value)

    def run_validation(self, *args, **kwargs):
        # If we POST multiple instances at the same time, then validation will be run for all of them sequentially
        # before creating the first instance in the DB. Some of the new instances might reference instances (e.g., via
        # `parent` or `left_sibling` in the case of `Organization`) that are also still to be created. So we keep track
        # of the instances that we already validated (i.e., that we're about to create). For this, we must make sure to
        # override run_validation() in model serializers so that they add the validated data to
        # `self.parent._validated_so_far`, if `parent` is a BulkListSerializer. This sucks and it would be better to
        # override `to_internal_value()` here, which iterates over the children and calls `run_validation()` on them.
        # However, `ListSerializer.to_internal_value()` has a lot of other code and we might be in trouble if DRF
        # changes some of that.
        self._children_validated_so_far = []
        return super().run_validation(*args, **kwargs)


class BulkModelViewSet[M: Model](viewsets.ModelViewSet[M]):
    def bulk_create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return response.Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers,
        )

    def bulk_update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(
            self.filter_queryset(self.get_queryset()),
            data=request.data,
            many=True,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return response.Response(serializer.data)

    def partial_bulk_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.bulk_update(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            return self.bulk_create(request, *args, **kwargs)
        return super().create(request, *args, **kwargs)
