from __future__ import annotations

import re
import typing
from collections import Counter
from uuid import UUID

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, response, serializers, status, viewsets
from rest_framework.exceptions import ValidationError

from kausal_common.model_images import ModelWithImageSerializerMixin, ModelWithImageViewMixin
from kausal_common.models.general import public_fields

from paths import permissions

from nodes.models import InstanceConfig
from orgs.models import Organization
from people.models import Person

if typing.TYPE_CHECKING:
    from paths.types import PathsAdminRequest, PathsAuthenticatedRequest, PathsAPIRequest
    from django.db.models import QuerySet

def camelcase_to_underscore(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def register_view_helper(view_list, klass, name=None, basename=None):
    if not name:
        if klass.serializer_class:
            model = klass.serializer_class.Meta.model
        else:
            model = klass.queryset.model
        name = camelcase_to_underscore(model._meta.object_name)

    entry = {'class': klass, 'name': name}
    if basename is not None:
        entry['basename'] = basename

    view_list.append(entry)

    return klass

all_views = []
all_routers = []

def register_view(klass, *args, **kwargs):
    return register_view_helper(all_views, klass, *args, **kwargs)

class PrevSiblingField(serializers.CharField):
    # Instances must implement method get_prev_sibling(). (Treebeard nodes do that.) Must be used in ModelSerializer so
    # we can get the model for to_internal_value().
    # FIXME: This is ugly.
    def get_attribute(self, instance):
        return instance.get_prev_sibling()

    def to_representation(self, value):
        # value is the left sibling of the original instance
        if value is None:
            return None
        try:
            value._meta.get_field('uuid')
            return str(value.uuid)
        except FieldDoesNotExist:
            return value.id

    def to_internal_value(self, data):
        # FIXME: No validation (e.g., permission checking)
        model = self.parent.Meta.model
        # We use a UUID as the value for this field if the model has a field called uuid. Otherwise we use the
        # related model instance itself.
        try:
            model._meta.get_field('uuid')
            return UUID(data)
        except FieldDoesNotExist:
            return model.objects.get(id=data)

class TreebeardParentField(serializers.CharField):
    # For serializers of Treebeard node models
    def get_attribute(self, instance):
        return instance.get_parent()

    def to_representation(self, value):
        # value is the parent of the original instance
        if value is None:
            return None
        try:
            value._meta.get_field('uuid')
            return str(value.uuid)
        except FieldDoesNotExist:
            return value.id

    def to_internal_value(self, data):
        # FIXME: No validation (e.g., permission checking)
        model = self.parent.Meta.model
        # We use a UUID as the value for this field if the model has a field called uuid. Otherwise we use the
        # related model instance itself.
        try:
            model._meta.get_field('uuid')
            return UUID(data)
        except FieldDoesNotExist:
            return model.objects.get(id=data)


# Regarding the metaclass: https://stackoverflow.com/a/58304791/14595546
class TreebeardModelSerializerMixin(metaclass=serializers.SerializerMetaclass):
    parent = TreebeardParentField(allow_null=True, required=False)
    left_sibling = PrevSiblingField(allow_null=True, required=False)

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields += ['parent', 'left_sibling']
        return fields

    def _get_instance_from_uuid(self, uuid: UUID | str | None):
        if uuid is None:
            return None
        return self.Meta.model.objects.get(uuid=uuid)

    def _get_validated_instance_data(self, uuid: UUID):
        for child_data in getattr(self.parent, '_children_validated_so_far', []):
            assert child_data['uuid'] is None or isinstance(child_data['uuid'], UUID)
            if child_data['uuid'] == uuid:
                return child_data
        raise exceptions.ValidationError("No validated instance with the given UUID found")

    def run_validation(self, *args, **kwargs):
        data = super().run_validation(*args, **kwargs)
        if hasattr(self.parent, '_children_validated_so_far'):
            self.parent._children_validated_so_far.append(data)
        return data

    def validate(self, data):
        assert data['left_sibling'] is None or isinstance(data['left_sibling'], UUID)
        assert data['parent'] is None or isinstance(data['parent'], UUID)
        if data['left_sibling']:
            parents: dict[UUID, UUID | None] = {}
            for d in self.initial_data:
                assert isinstance(d['uuid'], str)
                uuid = UUID(d['uuid'])
                if d['parent'] is None:
                    parent_uuid = None
                else:
                    assert isinstance(d['parent'], str)
                    parent_uuid = UUID(d['parent'])
                parents[uuid] = parent_uuid
            if data['left_sibling'] in parents:
                left_sibling_parent_uuid = parents[data['left_sibling']]
            else:
                try:
                    left_sibling = self._get_instance_from_uuid(data['left_sibling'])
                except self.Meta.model.DoesNotExist:
                    # Maybe the instance is not created yet because it is about to be created in the same request
                    left_sibling = self._get_validated_instance_data(data['left_sibling'])
                    left_sibling_parent_uuid = left_sibling['parent']
                    assert left_sibling_parent_uuid is None or isinstance(left_sibling_parent_uuid, UUID)
                else:
                    assert left_sibling is not None
                    if left_sibling.parent is None:
                        left_sibling_parent_uuid = None
                    else:
                        left_sibling_parent_uuid = left_sibling.parent.uuid
            if left_sibling_parent_uuid != data['parent']:
                raise exceptions.ValidationError("Instance and left sibling have different parents")
        return data

    def create(self, validated_data):
        parent_uuid = validated_data.pop('parent', None)
        parent = self._get_instance_from_uuid(parent_uuid)
        left_sibling_uuid = validated_data.pop('left_sibling', None)
        left_sibling = self._get_instance_from_uuid(left_sibling_uuid)
        instance = Organization(**validated_data)
        # This sucks, but I don't think Treebeard provides an easier way of doing this
        if left_sibling is None:
            if parent is None:
                first_root = Organization.get_first_root_node()
                if first_root is None:
                    Organization.add_root(instance=instance)
                else:
                    first_root.add_sibling('left', instance=instance)
            else:
                right_sibling = parent.get_first_child()
                if right_sibling is None:
                    parent.add_child(instance=instance)
                else:
                    right_sibling.add_sibling('left', instance=instance)
        else:
            left_sibling.add_sibling('right', instance=instance)
        return instance

    def update(self, instance, validated_data):
        # FIXME: Since left_sibling has allow_null=True, we should distinguish whether left_sibling is None because it
        # is not in validated_data or because validated_data['left_sibling'] is None. Similarly for parent. Sending a
        # PUT request and omitting one of these fields might inadvertently move the node.
        parent_uuid = validated_data.pop('parent', None)
        parent = self._get_instance_from_uuid(parent_uuid)
        left_sibling_uuid = validated_data.pop('left_sibling', None)
        left_sibling = self._get_instance_from_uuid(left_sibling_uuid)
        # If this is called from BulkListSerializer, then `instance` might be in some weird state and if we don't
        # re-fetch it we'll get weird integrity errors.
        instance = instance._meta.model.objects.get(pk=instance.pk)
        super().update(instance, validated_data)
        if left_sibling is None:
            if parent is None:
                first_root = Organization.get_first_root_node()
                assert first_root is not None  # if there were no root, there would be no node and thus no `instance`
                instance.move(first_root, 'left')
            else:
                instance.move(parent, 'first-child')
        else:
            instance.move(left_sibling, 'right')
        # Reload because object is stale after move
        instance = instance._meta.model.objects.get(pk=instance.pk)
        return instance

class BulkSerializerValidationInstanceMixin:
    def run_validation(self, data: dict):
        if self.parent and self.instance is not None:
            assert isinstance(self.instance, models.query.QuerySet)
            self._instance = self.parent.objs_by_id.get(data['id'])
        else:
            self._instance = self.instance
        return super().run_validation(data)


class BulkListSerializer(serializers.ListSerializer):
    child: serializers.ModelSerializer
    instance: QuerySet | None
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
            else:
                if qs is not None:
                    errors.append({id_attr: "Attribute missing"})
                    continue
        if any(errors):
            raise ValidationError(errors)

        if qs is not None:
            objs_by_id = {}
            self.obj_ids = []
            qs = qs.filter(**{'%s__in' % id_attr: obj_ids})
            for obj in qs:
                objs_by_id[getattr(obj, id_attr)] = obj
            seen_ids = set()
            for idx, item in enumerate(data):
                obj_id = item[id_attr]
                self.obj_ids.append(obj_id)
                if obj_id not in objs_by_id:
                    errors[idx] = {id_attr: "Unable to find object"}
                    continue
                if obj_id in seen_ids:
                    errors[idx] = {id_attr: "Duplicate value"}
                    continue
                seen_ids.add(obj_id)
            self.objs_by_id = objs_by_id

        if any(errors):
            raise ValidationError(errors)

        return super().to_internal_value(data)

    def _handle_updates(self, update_ops):
        for model, ops in update_ops.items():
            # TODO: build the deferred operations structure
            # like this from the get go

            # If the same instance occurs multiple times (perhaps with some fields different) in `ops`, then this
            # will do nasty stuff. (If we use an instance as a dict key, only the PK matters, so the other values
            # could different but we'd still map to the same value). We merge all ops with the same instance PK by
            # only taking the latest instance having that PK and unifying the fields.
            fields_for_instance = {}
            for instance, fields in ops:
                fields = frozenset(fields)  # merge duplicate fields
                if instance in fields_for_instance:
                    # Actually not necessarily the exact instance occurs, but one with the same PK
                    existing_fields = fields_for_instance.pop(instance)
                    fields_for_instance[instance] = existing_fields | fields
                else:
                    fields_for_instance[instance] = fields
            instances_for_fields = {}
            for instance, fields in fields_for_instance.items():
                instances_for_fields.setdefault(fields, []).append(instance)
            for fields, instances in instances_for_fields.items():
                model.objects.bulk_update(instances, fields)

    def _handle_deletes(self, delete_ops):
        for model in delete_ops.keys():
            pks = [o[0].pk for o in delete_ops[model]]
            model.objects.filter(pk__in=pks).delete()

    def _handle_creates(self, create_ops):
        for model in create_ops.keys():
            instances = [o[0] for o in create_ops[model]]
            model.objects.bulk_create(instances)

    def _handle_set_related(self, set_ops):
        for model in set_ops.keys():
            # TODO: actually batch this up
            for instance, field_name, related_ids in set_ops[model]:
                setattr(instance, field_name, related_ids)

    def _execute_deferred_operations(self, ops):
        grouped_by_operation_and_model = dict()
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
        for obj_id, obj_data in zip(self.obj_ids, all_validated_data):
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

class BulkModelViewSet(viewsets.ModelViewSet):
    request: PathsAPIRequest

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

class OrganizationSerializer(TreebeardModelSerializerMixin, serializers.ModelSerializer):
    uuid = serializers.UUIDField(required=False)

    class Meta:
        model = Organization
        list_serializer_class = BulkListSerializer
        fields = public_fields(Organization)

    def create(self, validated_data):
        from paths.context import realm_context
        instance = super().create(validated_data)
        # # Add instance to active instance's related organizations
        # request: PathsAdminRequest = self.context.get('request')
        # ic = realm_context.get().realm
        # ic.related_organizations.add(instance)
        return instance

class ProtectedError(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Cannot delete instance because other objects reference it.')
    default_code = 'protected_error'


class HandleProtectedErrorMixin:
    """Mixin for viewsets that use DRF's DestroyModelMixin to handle ProtectedError gracefully."""

    def perform_destroy(self, instance):
        try:
            super().perform_destroy(instance)
        except models.ProtectedError as err:
            raise ProtectedError(
                detail={
                    'non_field_errors': _(
                        'Cannot delete "%s" because it is connected to other objects '
                        'such as instances, persons or actions.',
                    ) % getattr(instance, 'name', str(instance)),
                },
            ) from err


@register_view
class OrganizationViewSet(HandleProtectedErrorMixin, BulkModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    filterset_fields = {
        'name': ('exact', 'in'),
    }

    # This view set is not registered with a "bulk router" (see BulkRouter or NestedBulkRouter), so we need to define
    # patch and put ourselves
    def patch(self, request, *args, **kwargs):
        return self.partial_bulk_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.bulk_update(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [permissions.ReadOnly]
        else:
            permission_classes = [permissions.OrganizationPermission]
        return [permission() for permission in permission_classes]

    def get_queryset(self):

        from loguru import logger
        queryset = super().get_queryset()
        instance_identifier = self.request.query_params.get('instance', None)
        if instance_identifier is None:
            return queryset
        try:
            logger.debug(f"Getting organizations for instance {instance_identifier}")
            instance = InstanceConfig.objects.get(identifier=instance_identifier)
        except InstanceConfig.DoesNotExist:
            raise exceptions.NotFound(detail="Instance not found")
        available_organizations = Organization.objects.available_for_instance(instance)
        logger.debug(f"available_organizations: {available_organizations}")
        return available_organizations

class PersonSerializer(
    BulkSerializerValidationInstanceMixin,
    serializers.ModelSerializer,
    ModelWithImageSerializerMixin,
):
    uuid = serializers.UUIDField(required=False)
    avatar_url = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context.get('authorized_for_instance') is None:
            self.fields.pop('email')

    def get_avatar_url(self, obj: Person) -> str | None:
        return obj.get_avatar_url(self.context['request'])

    def validate_email(self, value):
        qs = Person.objects.filter(email__iexact=value)
        if self._instance is not None:
            qs = qs.exclude(pk=self._instance.pk)
        if qs.exists():
            raise serializers.ValidationError(_('Person with this email already exists'))
        return value

    def validate(self, data):
        for d in self.initial_data:
            if 'email' not in d:
                raise exceptions.ValidationError(_("Not all objects have an email address"))
        emails = Counter(data['email'] for data in self.initial_data)
        duplicates = [email for email, n in emails.most_common() if n > 1]
        if duplicates:
            # TODO: This should better be in validate_email to highlight the faulty table cells
            raise exceptions.ValidationError(_("Duplicate email addresses: %s") % ', '.join(duplicates))
        return data

    class Meta:
        model = Person
        list_serializer_class = BulkListSerializer
        fields = public_fields(Person, add_fields=['avatar_url'])


@register_view
class PersonViewSet(ModelWithImageViewMixin, BulkModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # This view set is not registered with a "bulk router" (see BulkRouter or NestedBulkRouter), so we need to define
    # patch and put ourselves
    def patch(self, request, *args, **kwargs):
        return self.partial_bulk_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.bulk_update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # FIXME: Duplicated in people.wagtail_admin.PersonDeleteView.delete_instance()
        acting_admin_user = self.request.user
        instance.delete_and_deactivate_corresponding_user(acting_admin_user)

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [permissions.ReadOnly]
        else:
            permission_classes = [permissions.PersonPermission]
        return [permission() for permission in permission_classes]

    def get_instance(self):
        instance_identifier = self.request.query_params.get('instanceIdentifier', None)

        if instance_identifier is None:
            return None
        try:
            return InstanceConfig.objects.get(identifier=instance_identifier)
        except InstanceConfig.DoesNotExist:
            raise exceptions.NotFound(detail="InstanceConfig not found")

    def user_is_authorized_for_instance(self, instance):
        user = self.request.user

        return (
            user is not None
            and user.is_authenticated
            # and hasattr(user, 'is_general_admin_for_instance')
            and user.user_is_admin_for_instance(instance)
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        instance = self.get_instance()
        if instance is None:
            return context
        if self.user_is_authorized_for_instance(instance):
            context.update({'authorized_for_instance': instance})
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        instance = self.get_instance()
        if instance is None:
            return queryset
        if not self.user_is_authorized_for_instance(instance):
            raise exceptions.PermissionDenied(detail="Not authorized")
        return queryset.available_for_instance(instance)
