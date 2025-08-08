from uuid import UUID

from django.core.exceptions import FieldDoesNotExist
from rest_framework import exceptions, serializers

from orgs.models import Organization


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
