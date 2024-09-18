# ruff: noqa: E402
from __future__ import annotations

import dataclasses
import json
import typing
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import Any, ClassVar, Generic, NamedTuple, Self, TypeVar, cast, overload
from uuid import UUID

from django.contrib.admin.utils import NestedObjects
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import FieldDoesNotExist
from django.db import router, transaction
from django.db.models import ForeignObjectRel, Model
from django.db.models.deletion import Collector
from django.db.models.fields import NOT_PROVIDED, Field
from django.db.models.fields.related import RelatedField
from django.utils.functional import Promise
from pydantic import BaseModel, ConfigDict, IPvAnyAddress, Json, PrivateAttr
from pydantic.fields import FieldInfo
from pydantic.v1.fields import Required

from pydantic_core import PydanticUndefined

BaseModel.model_config['protected_namespaces'] = ()

from diffsync import Adapter, DiffSyncModel
from diffsync.diff import Diff, DiffElement
from diffsync.enum import DiffSyncActions, DiffSyncFlags, DiffSyncModelFlags
from diffsync.exceptions import ObjectNotCreated, ObjectNotFound
from diffsync.helpers import DiffSyncDiffer
from diffsync.store import BaseStore
from diffsync.store.local import LocalStore
from loguru import logger as log
from rich.console import Console
from rich.padding import Padding
from rich.pretty import Pretty
from rich.prompt import Confirm
from rich.tree import Tree
from treebeard.mp_tree import MP_Node

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from diffsync.store import BaseStore
    from structlog import BoundLogger


INT_TYPES = [
    "AutoField",
    "BigAutoField",
    "IntegerField",
    "SmallIntegerField",
    "BigIntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
]

STR_TYPES = [
    "CharField",
    "EmailField",
    "URLField",
    "SlugField",
    "TextField",
    "FilePathField",
    "FileField",
]


FIELD_TYPES: dict[str, type | UnionType] = {
    "GenericIPAddressField": IPvAnyAddress,
    "BooleanField": bool,
    "BinaryField": bytes,
    "DateField": date,
    "DateTimeField": datetime,
    "DurationField": timedelta,
    "TimeField": time,
    "DecimalField": Decimal,
    "FloatField": float,
    "UUIDField": UUID,
    "JSONField": Json | dict | list,  # TODO: Configure this using default
    "ArrayField": list,
    # "IntegerRangeField",
    # "BigIntegerRangeField",
    # "CICharField",
    # "CIEmailField",
    # "CIText",
    # "CITextField",
    # "DateRangeField",
    # "DateTimeRangeField",
    # "DecimalRangeField",
    # "FloatRangeField",
    # "HStoreField",
    # "RangeBoundary",
    # "RangeField",
    # "RangeOperators",
}


def get_internal_type(field: Field) -> type | UnionType | None:
    internal_type = field.get_internal_type()
    if internal_type in STR_TYPES:
        return str
    if internal_type in INT_TYPES:
        return int
    if internal_type in FIELD_TYPES:
        return FIELD_TYPES[internal_type]

    for field_class in type(field).__mro__:
        get_internal_type = getattr(field_class, "get_internal_type", None)
        if not get_internal_type:
            continue
        _internal_type = get_internal_type(field_class())
        if _internal_type in FIELD_TYPES:
            return FIELD_TYPES[_internal_type]

    return None


type PythonType = type | UnionType
type DBFieldType = Field | ForeignObjectRel | GenericForeignKey

def _get_choice_type(field: Field, schema_name: str) -> tuple[Enum, Any]:
    assert field.choices is not None
    enum_choices = {}
    for k, v in field.choices:
        if Promise in type(v).__mro__:
            val = str(v)
        else:
            assert isinstance(v, str)
            val = v
        enum_choices[val] = k
    if field.blank:
        enum_choices["_blank"] = ""

    enum_prefix = (
        f"{schema_name.replace('_', '')}{field.name.title().replace('_', '')}"
    )
    enum_name = f"{enum_prefix}Enum"
    python_type = Enum(  # type: ignore
        enum_name,
        enum_choices,
        module=__name__,
    )
    if field.has_default() and isinstance(field.default, Enum):
        default = field.default.value
    else:
        default = None
    return python_type, default  # type: ignore

def _convert_field(field: Field, schema_name: str) -> tuple[PythonType, FieldInfo]:  # noqa: C901, PLR0912, PLR0915
    deconstructed = field.deconstruct()
    field_options = deconstructed[3] or {}
    blank = field_options.pop("blank", False)
    null = field_options.pop("null", False)
    description = field.help_text
    title = field.verbose_name.title()
    default = Required
    default_factory = None
    related_field_name = None

    python_type: PythonType

    if isinstance(field, RelatedField):
        if not field.related_model:
            internal_type = field.model._meta.pk.get_internal_type()
        else:
            assert field.related_model != 'self'
            internal_type = field.related_model._meta.pk.get_internal_type()
            if not field.concrete and field.auto_created or field.null:
                default = None

        pk_type = FIELD_TYPES.get(internal_type, int)
        if field.one_to_many or field.many_to_many:
            python_type = list[dict[str, pk_type]]  # type: ignore
        else:
            python_type = pk_type

        if blank or null:
            python_type = python_type | None
        related_field_name = field.target_field.name
    else:
        if field.choices:
            python_type, default = _get_choice_type(field, schema_name)  # type: ignore[assignment]
        elif isinstance(field, ArrayField):
            mapped_type = get_internal_type(field.base_field)
            python_type = list[mapped_type]  # type: ignore[valid-type]
        else:
            mapped_type = get_internal_type(field)
            if mapped_type is None:
                log.warning(
                    "%s is currently unhandled, defaulting to str.", field.__class__,
                )
                python_type = str
            else:
                python_type = mapped_type

        if default is Required and field.has_default():
            if callable(field.default):
                default_factory = field.default
                default = PydanticUndefined
            else:
                default = field.default
        elif field.primary_key or blank or null:
            default = None
            python_type = python_type | None

        if default not in (None, NOT_PROVIDED) and field.null:
            python_type = python_type | None

    if field.get_internal_type() in STR_TYPES and not field.choices:
        max_length = field.max_length
    else:
        max_length = None

    field_is_optional = all([
        getattr(field, "null", None),
        field.is_relation,
        # A list that is null, is the empty list. So there is no need
        # to make it nullable.
        typing.get_origin(python_type) is not list,
    ])
    if field_is_optional:
        python_type = python_type | None

    field_info = FieldInfo(
        annotation=python_type,  # type: ignore
        default=default,
        default_factory=default_factory,
        title=title,
        description=str(description) or related_field_name or field.name,
        max_length=max_length,
    )

    return python_type, field_info

def _convert_foreign_object_rel(field: ForeignObjectRel) -> tuple[PythonType, FieldInfo]:
    raise NotImplementedError

@dataclass(frozen=True)
class DjangoModelFields:
    plain_fields: dict[str, Field] = dataclasses.field(default_factory=dict)
    enum_fields: dict[str, Field] = dataclasses.field(default_factory=dict)
    related_fields: dict[str, ForeignObjectRel] = dataclasses.field(default_factory=dict)
    extra_attrs: set[str] = dataclasses.field(default_factory=set)

    @property
    def field_names(self) -> set[str]:
        return set(self.plain_fields.keys()) | set(self.enum_fields.keys())

def convert_django_field(
    field: DBFieldType, schema_name: str, django_fields: DjangoModelFields,
) -> tuple[PythonType, FieldInfo] | None:
    if isinstance(field, Field):
        python_type, field_info = _convert_field(field, schema_name)
        if isinstance(python_type, type) and issubclass(python_type, Enum):
            django_fields.enum_fields[field.name] = field
        else:
            django_fields.plain_fields[field.name] = field
    elif isinstance(field, ForeignObjectRel):
        #python_type, field_info = _convert_foreign_object_rel(field)
        django_fields.related_fields[field.name] = field
        return None
    else:
        raise NotImplementedError(str(type(field)))

    return (
        python_type,
        field_info,
    )

_BaseT_co = TypeVar('_BaseT_co', bound=BaseModel, covariant=True)

def pydantic_from_django_model(
    cls: type[_BaseT_co], model: type[Model], include_fields: Sequence[str],
):
    django_fields = DjangoModelFields()
    new_pydantic_fields: dict[str, tuple[PythonType, FieldInfo]] = {}

    for field_name in include_fields:
        try:
            db_field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            if field_name not in cls.model_fields:
                raise
            django_fields.extra_attrs.add(field_name)
            continue

        field_def = convert_django_field(db_field, cls.__name__, django_fields)
        if field_name in cls.model_fields:
            # field already has an annotation
            continue

        if field_def is None:
            raise Exception("Unable to convert field: %s.%s" % (model._meta.label, field_name))

        new_pydantic_fields[field_name] = field_def
        python_type, field_info = field_def

    cls.__doc__ = getattr(cls, '__doc__', model.__doc__)
    for field_name, (python_type, field_info) in new_pydantic_fields.items():
        cls.model_fields[field_name] = field_info
        cls.__annotations__[field_name] = python_type
    cls.model_rebuild(force=True)
    return django_fields


_ModelT = TypeVar('_ModelT', bound=Model)

class SiblingIds(NamedTuple):
    prev: str | None
    next: str | None

SIBLING_ORDER_ATTRIBUTE = 'sibling_order'

class DjangoDiffModel(DiffSyncModel, Generic[_ModelT]):
    _model: ClassVar[type[_ModelT]]  # type: ignore[misc]
    _django_fields: ClassVar[DjangoModelFields]
    _allow_related_model_deletion: ClassVar[bool] = False
    _is_orderable: ClassVar[bool] = False
    _parent_key: ClassVar[str | None] = None
    _parent_type: ClassVar[str | None] = None
    model_flags: DiffSyncModelFlags = DiffSyncModelFlags.NATURAL_DELETION_ORDER

    sibling_order: int | None = None
    """Order of the instance under the same parent."""

    _instance: _ModelT | None = None
    _instance_pk: int | None = None
    _parent_id: str | None = None
    _parent_model: type[DjangoDiffModel] | None = None
    _children_changed: set[str] = PrivateAttr(default_factory=set)

    model_config = ConfigDict(extra='allow', protected_namespaces=())

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs) -> None:  # noqa: C901
        if not hasattr(cls, '_model'):
            return
        include_fields = list(set(cls._identifiers) | set(cls._attributes))
        django_fields = pydantic_from_django_model(cls, cls._model, include_fields=include_fields)
        cls._django_fields = django_fields

        internal_attrs = []
        mp_model = cls._mpnode_or_none()
        if mp_model:
            if not cls._parent_key:
                msg = f"{cls._model!r} is an MP_Node, but _parent_key is not set"
                raise AttributeError(msg)
            if cls._parent_key not in cls._attributes:
                msg = f"{cls._model!r} is an MP_Node, but '{cls._parent_key}' is not in _attributes"
                raise AttributeError(msg)
            if not mp_model.node_order_by:
                cls._is_orderable = True
            if cls._parent_type is None:
                cls._parent_type = cls._modelname
            else:
                assert cls._parent_type == cls._modelname
        elif cls._parent_key and not cls._parent_type:
            raise AttributeError("'_parent_type' is not set")

        if hasattr(cls._model, 'sort_order_field'):
            cls._is_orderable = True

        if cls._is_orderable and SIBLING_ORDER_ATTRIBUTE not in cls._attributes:
            internal_attrs.append(SIBLING_ORDER_ATTRIBUTE)

        if internal_attrs:
            cls._attributes = (*cls._attributes, *internal_attrs)

        super().__pydantic_init_subclass__(**kwargs)

    @classmethod
    def _convert_django_instance(cls, obj: _ModelT) -> dict[str, Any]:
        field_names = cls._django_fields.field_names
        data = {field_name: getattr(obj, field_name) for field_name in field_names}
        return data

    @classmethod
    def _mpnode_or_none(cls) -> type[MP_Node] | None:
        if issubclass(cls._model, MP_Node):
            return cls._model
        return None

    def get_django_instance(self) -> _ModelT:
        if self._instance:
            return self._instance
        assert self._instance_pk
        instance = self._model._default_manager.get(pk=self._instance_pk)
        self._instance = instance
        return instance

    @classmethod
    def from_django(cls, data: _ModelT | dict, context: Any = None) -> Self:  # noqa: ANN401
        if isinstance(data, cls._model):
            obj = data
            obj_data = cls._convert_django_instance(obj)
            obj_pk = obj.pk
        else:
            assert isinstance(data, dict)
            obj_data = data.copy()
            obj_pk = obj_data.pop('_instance_pk')
            obj = None

        self = cls.model_validate(obj_data, context=context)
        self._instance = obj
        self._instance_pk = obj_pk
        return self

    @classmethod
    def create_related(cls, adapter: DjangoAdapter, ids: dict, attrs: dict, instance: _ModelT, /) -> None:
        """
        Create related objects if there are any.

        This will be implemented in a subclass.
        """
        pass

    @classmethod
    def _convert_enums(cls, kwargs: dict) -> None:
        for field_name in cls._django_fields.enum_fields.keys():
            if field_name not in kwargs:
                continue
            kwargs[field_name] = kwargs[field_name].value

    @classmethod
    def _remove_related(cls, kwargs: dict) -> None:
        for field_name in cls._django_fields.related_fields.keys():
            if field_name not in kwargs:
                continue
            del kwargs[field_name]

    @classmethod
    def get_create_kwargs(cls, _adapter: DjangoAdapter, ids: dict, attrs: dict) -> dict:
        """Get the kwargs for the Django object create methods."""
        kwargs = {**ids, **attrs}
        cls._remove_related(kwargs)
        cls._convert_enums(kwargs)
        return kwargs

    @classmethod
    def get_mpnode_root_instance(cls, instance: _ModelT) -> _ModelT | None:  # noqa: ARG003
        return None

    @classmethod
    def _create_mpnode(
        cls, adapter: DjangoAdapter, instance: _ModelT, parent_id: str | None, sibling_order: int | None,
    ) -> _ModelT:
        parent = adapter.get(cls, str(parent_id)) if parent_id else None
        root_obj = cls.get_mpnode_root_instance(instance)
        parent_obj = parent.get_django_instance() if parent else cls.get_mpnode_root_instance(instance)
        assert isinstance(instance, MP_Node)
        assert parent_obj is None or isinstance(parent_obj, MP_Node)

        if not cls._is_orderable:
            assert sibling_order is None
            if parent_obj is None:
                child_obj = instance.add_root(instance=instance)
            else:
                assert isinstance(parent_obj, type(instance))
                child_obj = parent_obj.add_child(instance=instance)
                parent_obj.save()
            return cast(_ModelT, child_obj)

        # Orderable mptree
        if parent is not None:
            assert sibling_order is not None
            assert parent_obj is not None
            siblings = parent.get_children(cls, ordered=True)
            if len(siblings) == 0:
                child_obj = parent_obj.add_child(instance=instance)
            else:
                left_sibling = siblings[sibling_order - 1]
                sibling_obj = left_sibling.get_django_instance()
                assert isinstance(sibling_obj, MP_Node)
                child_obj = sibling_obj.add_sibling(pos='right', instance=instance)
        elif root_obj is None:
            child_obj = instance.add_root(instance=instance)
        else:
            assert isinstance(root_obj, MP_Node)
            child_obj = root_obj.add_child(instance=instance)

        return cast(_ModelT, child_obj)

    @classmethod
    def create_django_instance(cls, adapter: DjangoAdapter, create_kwargs: dict) -> _ModelT:
        model = cls._model
        mp_model = cls._mpnode_or_none()
        parent_id = None
        sibling_order: int | None = None

        if cls._is_orderable:
            sibling_order = create_kwargs.pop(SIBLING_ORDER_ATTRIBUTE)
            if not mp_model:
                sort_field = getattr(model, 'sort_order_field')  # noqa: B009
                create_kwargs[sort_field] = sibling_order

        if mp_model:
            parent_key = cls._parent_key
            parent_id = create_kwargs.pop(parent_key)

        instance = model(**create_kwargs)

        if mp_model:
            return cls._create_mpnode(adapter, instance, parent_id, sibling_order)

        instance.save()
        return instance

    @classmethod
    def create(cls, adapter: Adapter, ids: dict, attrs: dict) -> Self | None:
        self = super().create(adapter, ids, attrs)
        assert self is not None

        if cls._parent_key:
            assert cls._parent_key in attrs
            # parent_id = attrs[cls._parent_key]
            # self._parent_id = str(parent_id) if parent_id is not None else None
            # assert cls._parent_type is not None
            # if self._parent_id:
            #     parent = adapter.get(cls._parent_type, self._parent_id)
            #     parent.add_child(self)

        if not isinstance(adapter, DjangoAdapter):
            return self

        create_kwargs = cls.get_create_kwargs(adapter, ids, attrs)
        try:
            obj = cls.create_django_instance(adapter, create_kwargs)
            obj_pk = obj.pk
            cls.create_related(adapter, ids, attrs, obj)
        except Exception as e:
            msg = f"Unable to create a new {cls._model._meta.label} instance with ids {ids}"
            raise ObjectNotCreated(msg) from e

        self._instance = obj
        self._instance_pk = obj_pk
        return self

    def update_related(self, attrs: dict) -> None:
        """
        Update related objects if there are any.

        This will be implemented in a subclass.
        """
        raise NotImplementedError

    def get_update_kwargs(self, attrs: dict) -> dict:
        """Get the field values for updating a Django instance."""
        kwargs = {**attrs}
        self._remove_related(kwargs)
        self._convert_enums(kwargs)
        return kwargs

    def change_parent(self, old_parent: DjangoDiffModel, new_parent: DjangoDiffModel):
        assert self.get_type() in old_parent._children
        assert self.get_type() in new_parent._children
        old_parent.remove_child(self)
        old_parent._children_changed.add(self.get_type())
        new_parent.add_child(self)
        new_parent._children_changed.add(self.get_type())
        if not self._mpnode_or_none() or not new_parent._mpnode_or_none():
            return

        child_obj = self._instance
        assert isinstance(child_obj, MP_Node)
        parent_obj = new_parent.get_django_instance()
        assert type(parent_obj) is type(child_obj)
        assert isinstance(parent_obj, MP_Node)
        #siblings = new_parent.get_children(type(self), ordered=True)
        child_obj.move(parent_obj, 'last-child')

    def update(self, attrs: dict) -> Self | None:
        if not isinstance(self.adapter, DjangoAdapter):
            return super().update(attrs)

        update_kwargs = self.get_update_kwargs(attrs)
        obj = self.get_django_instance()

        #_sibling_ids = update_kwargs.pop(SIBLINGS_ATTRIBUTE, None)
        # if PARENT_ID_ATTRIBUTE in update_kwargs:
        #     parent_id = update_kwargs.pop(PARENT_ID_ATTRIBUTE)
        #     parent_changed = True
        # else:
        #     parent_changed = False

        new_parent: DjangoDiffModel | None
        old_parent: DjangoDiffModel | None

        if self._parent_key and self._parent_key in update_kwargs:
            new_parent_id = update_kwargs[self._parent_key]
            if new_parent_id is None:
                raise NotImplementedError()
            else:  # noqa: RET506
                new_parent_id = str(new_parent_id)
            if self._mpnode_or_none():
                # For MP_Nodes, the parent key is not a real DB column
                update_kwargs.pop(self._parent_key)
            assert self._parent_model is not None
            assert self._parent_id is not None
            new_parent = self.adapter.get(self._parent_model, new_parent_id)
            old_parent = self.adapter.get(self._parent_model, self._parent_id)
        else:
            new_parent = old_parent = None

        if self._is_orderable:
            sibling_order = update_kwargs.pop(SIBLING_ORDER_ATTRIBUTE, None)
            if sibling_order is not None:
                assert self._parent_model is not None
                assert self._parent_id is not None
                parent = self.adapter.get(self._parent_model, self._parent_id)
                parent._children_changed.add(self.get_type())
                log.debug("Sort order changed for %s:%s (parent %s:%s)" % (
                    self.get_type(), self.get_unique_id(), parent.get_type(), parent.get_unique_id(),
                ))
                # FIXME: Should we reorder the "children" attribute?

        if update_kwargs:
            for field_name, val in update_kwargs.items():
                setattr(obj, field_name, val)

            obj.save(update_fields=update_kwargs.keys(), force_update=True)

        ret = super().update(attrs)
        if new_parent and old_parent:
            self.change_parent(old_parent, new_parent)
        return ret

    def get_delete_collector[CollT: Collector](self, instance: _ModelT, collector: type[CollT]) -> CollT:
        coll = collector(using=router.db_for_write(type(instance), instance=instance))
        coll.collect([instance])  # pyright: ignore
        return coll

    def is_object_deletion_allowed(self, instance: _ModelT) -> bool:
        if not isinstance(self.adapter, DjangoAdapter):
            return True
        collector = self.get_delete_collector(instance, NestedObjects)
        if not collector.edges.get(instance):
            return True
        if self._allow_related_model_deletion:
            return True
        if self.adapter.allow_related_deletion is not None:
            return self.adapter.allow_related_deletion
        return self.adapter.is_object_deletion_allowed(instance)

    def delete(self) -> Self | None:
        if not isinstance(self.adapter, DjangoAdapter):
            return super().delete()
        instance = self._model._default_manager.get(pk=self._instance_pk)
        if not self.is_object_deletion_allowed(instance):
            return None
        obj_count, related = instance.delete()
        if related:
            related_objs_str = '; '.join('%s: %d' % (key, val) for key, val in related.items())
            related_str = 'with related objects: %s' % related_objs_str
        else:
            related_str = 'with no related objects'
        log.info("Deleted %s:%s %s" % (self.get_type(), self.get_unique_id(), related_str))
        return super().delete()

    def get_children[ChildT: DjangoDiffModel](self, child_type: type[ChildT], ordered: bool = False) -> list[ChildT]:
        type_str = child_type.get_type()
        children_ids = getattr(self, self._children[type_str])
        assert self.adapter is not None
        children: list[ChildT] = []
        for child in self.adapter.get_by_uids(children_ids, child_type):
            assert isinstance(child, child_type)
            children.append(child)
        if child_type._is_orderable and ordered:
            children = sorted(children, key=lambda x: getattr(x, SIBLING_ORDER_ATTRIBUTE))
        return children

    def add_child(self, child: DiffSyncModel, initial: bool = False) -> None:
        super().add_child(child)
        if not isinstance(child, DjangoDiffModel):
            return

        child._parent_id = self.get_unique_id()
        child._parent_model = type(self)
        if initial:
            if child._is_orderable and child.sibling_order is None:
                type_str = child.get_type()
                children_ids = getattr(self, self._children[type_str])
                child.sibling_order = len(children_ids) - 1
            return

        self._children_changed.add(child.get_type())

    def remove_child(self, child: DiffSyncModel) -> None:
        super().remove_child(child)
        assert isinstance(child, DjangoDiffModel)
        self._children_changed.add(child.get_type())


class TypedAdapter(Adapter):
    @overload  # type: ignore[override]
    def get[M: DiffSyncModel](self, obj: type[M], identifier: str | dict) -> M: ...

    @overload
    def get[M: DiffSyncModel](self, obj: M, identifier: str | dict) -> M: ...

    @overload
    def get(self, obj: str, identifier: str | dict) -> DiffSyncModel: ...

    def get(self, obj: str | DiffSyncModel | type[DiffSyncModel], identifier: str | dict) -> DiffSyncModel:
        return super().get(obj, identifier)

    @overload  # type: ignore[override]
    def get_all[M: DiffSyncModel](self, obj: type[M]) -> list[M]: ...

    @overload
    def get_all[M: DiffSyncModel](self, obj: M) -> list[M]: ...

    @overload
    def get_all(self, obj: str) -> list[DiffSyncModel]: ...

    def get_all(self, obj: str | DiffSyncModel | type[DiffSyncModel]) -> Sequence[DiffSyncModel]:  # pyright: ignore
        return super().get_all(obj)

class MergingSyncDiffer(DiffSyncDiffer):
    parent_changes: set[tuple[str, str]]

    def __init__(
            self,
            src_diffsync: Adapter,
            dst_diffsync: Adapter,
            flags: DiffSyncFlags,
            diff_class: type[Diff] = Diff,
            callback: Callable[[str, int, int], None] | None = None,
        ):
        self.parent_changes = set()
        super().__init__(src_diffsync, dst_diffsync, flags, diff_class, callback)

    def diff_object_pair(self, src_obj: DiffSyncModel | None, dst_obj: DiffSyncModel | None) -> DiffElement | None:
        parent_changed = False
        if src_obj is not None and dst_obj is None:
            # Try to detect parent moves
            unique_id = src_obj.get_unique_id()
            try:
                dst_obj = self.dst_diffsync.get(src_obj.get_type(), unique_id)
                if isinstance(dst_obj, DjangoDiffModel):
                    assert dst_obj._parent_key is not None
                self.parent_changes.add((dst_obj.get_type(), dst_obj.get_unique_id()))
                parent_changed = True
            except ObjectNotFound:
                dst_obj = None
        elif src_obj is None and dst_obj is not None:
            type_id = (dst_obj.get_type(), dst_obj.get_unique_id())
            if type_id in self.parent_changes:
                return None

        el = super().diff_object_pair(src_obj, dst_obj)
        if parent_changed:
            assert el is not None
            attr_diffs = el.get_attrs_diffs().get('+', {})
            if isinstance(dst_obj, DjangoDiffModel):
                assert dst_obj._parent_key in attr_diffs
        return el

type ParentChildGroup = tuple[type[DjangoDiffModel], str, str]

class DjangoAdapter(TypedAdapter):
    transaction_started: bool = False
    allow_related_deletion: bool | None = None
    interactive: bool

    def __init__(
        self, interactive: bool = False, allow_related_deletion: bool | None = None, **kwargs,
    ) -> None:
        self.allow_related_deletion = allow_related_deletion
        self.interactive = interactive
        super().__init__(**kwargs)

    def is_object_deletion_allowed(self, instance: Model):
        collector = NestedObjects(using=router.db_for_write(type(instance), instance=instance))
        collector.collect([instance])  # pyright: ignore
        if len(collector.edges.keys()) == 1:
            return True
        if self.allow_related_deletion is not None:
            return self.allow_related_deletion
        if not self.interactive:
            return False
        return self.confirm_delete(instance, collector)

    def confirm_delete(self, obj: Model, collector: NestedObjects) -> bool:
        root_related = collector.edges.get(obj)
        if not root_related:
            return True

        console = Console()
        # Create a tree of related objects
        tree = Tree(Pretty(obj))
        edges = collector.edges
        def add_related(parent: Tree, related: Sequence[Model]) -> None:
            for child in related:
                branch = parent.add(Pretty(child, max_depth=2))
                child_related = edges.get(child)
                if child_related:
                    add_related(branch, child_related)

        add_related(tree, root_related)  # pyright: ignore
        # Print the tree
        console.print(Padding(tree, (1, 4)))
        console.print(":warning: The above objects would be deleted", style="logging.level.warning")
        return Confirm.ask("Do you want to proceed with deletion?", default=True)

    @contextmanager
    def start(self):
        assert not self.transaction_started
        with transaction.atomic():
            self.transaction_started = True
            try:
                yield
            finally:
                self.transaction_started = False

    def rollback(self):
        assert self.transaction_started
        transaction.set_rollback(rollback=True)

    def diff_from(
        self,
        source: Adapter,
        diff_class: type[Diff] = Diff,
        flags: DiffSyncFlags = DiffSyncFlags.NONE,
        callback: Callable[[str, int, int], None] | None = None,
    ) -> Diff:
        """
        Generate a Diff describing the difference from the other DiffSync to this one.

        Args:
        ----
            source: Object to diff against.
            diff_class: Diff or subclass thereof to use for diff calculation and storage.
            flags: Flags influencing the behavior of this diff operation.
            callback: Function with parameters (stage, current, total), to be called at intervals as the
                calculation of the diff proceeds.

        """
        differ = MergingSyncDiffer(
            src_diffsync=source,
            dst_diffsync=self,
            flags=flags,
            diff_class=diff_class,
            callback=callback,
        )
        return differ.calculate_diffs()

    def sync_from(
        self,
        source: Adapter,
        diff_class: type[Diff] = Diff,
        flags: DiffSyncFlags = DiffSyncFlags.NONE,
        callback: Callable[[str, int, int], None] | None = None,
        diff: Diff | None = None,
    ) -> Diff:
        assert self.transaction_started
        with transaction.atomic():
            return super().sync_from(source, diff_class, flags, callback, diff)

    def get_model_class(self, type_str: str) -> type[DjangoDiffModel]:
        cls = getattr(self, type_str)
        assert issubclass(cls, DjangoDiffModel)
        return cls

    def _process_diff_element(
        self, el: DiffElement, parent: DjangoDiffModel | None, group: str, parents: set[ParentChildGroup], indent: int,
    ) -> None:
        model = getattr(self, el.type)
        assert issubclass(model, DjangoDiffModel)

        if el.action == DiffSyncActions.DELETE:
            if model._is_orderable and parent is not None:
                parents.add((type(parent), parent.get_unique_id(), group))
            return

        obj = self.get(model, el.keys)
        if obj._children and obj._children_changed:
            for key in obj._children_changed:
                parents.add((model, obj.get_unique_id(), key))

        if not el.has_diffs(include_children=True):
            return

        self._process_diff(el.child_diff, obj, parents, indent + 1)

    def _process_diff(self, diff: Diff, parent: DjangoDiffModel | None, parents: set[ParentChildGroup], indent: int) -> None:
        for group in diff.groups():
            for child in diff.children[group].values():
                self._process_diff_element(child, parent, group, parents, indent)

    def _reorder_mptree(
        self,
        parent: MP_Node | None,
        child_model: type[MP_Node],
        child_type: type[DjangoDiffModel[MP_Node]],
        children: list[DjangoDiffModel[MP_Node]],
    ) -> None:
        if parent:
            siblings = parent.get_children()
        else:
            # Not re-arranging root nodes
            return
        db_pks: list[int] = list(siblings.values_list('pk', flat=True))
        new_db_pks: list[int] = [cast(int, child._instance_pk) for child in children]

        mgr = child_model._default_manager
        nr_changes = 0
        for order, new_pk in enumerate(new_db_pks):
            if new_pk not in db_pks:
                old_pk = None
            else:
                old_pk = db_pks[order]
            if new_pk == old_pk:
                continue

            nr_changes += 1
            db_child = mgr.get(pk=new_pk)
            if old_pk is not None:
                db_pks.remove(new_pk)
            if order == 0:
                db_child.move(parent, 'first-child')
            else:
                db_child.move(mgr.get(pk=new_db_pks[order - 1]), 'right')
            db_pks.insert(order, new_pk)

        if nr_changes:
            log.debug("%d children reordered" % nr_changes)
        else:
            log.debug("No re-ordering needed")

    def _reorder_sorted(self, model: type[Model], ordered_pks: list[int]) -> None:
        obj_by_pk: dict[int, Model] = {obj.pk: obj for obj in model._default_manager.filter(pk__in=ordered_pks)}
        assert len(obj_by_pk) == len(ordered_pks)
        order_field: str = getattr(model, 'sort_order_field')  # noqa: B009
        for order, pk in enumerate(ordered_pks):
            obj = obj_by_pk[pk]
            if getattr(obj, order_field) == order:
                continue
            setattr(obj, order_field, order)
            obj.save(update_fields=[order_field])

    def reorder_children(self, parent: DjangoDiffModel, group: str):
        child_type = getattr(self, group)
        assert issubclass(child_type, DjangoDiffModel)
        child_model = child_type._model  # pyright: ignore
        children = parent.get_children(child_type, ordered=True)
        if child_type._mpnode_or_none():
            if type(parent) is not child_type:
                parent_obj = parent.get_mpnode_root_instance(parent.get_django_instance())
            else:
                parent_obj = parent.get_django_instance()
            self._reorder_mptree(parent_obj, child_model, child_type, children)
        else:
            self._reorder_sorted(child_model, [cast(int, child._instance_pk) for child in children])

    def sync_complete(
        self, source: Adapter, diff: Diff, flags: DiffSyncFlags = DiffSyncFlags.NONE, logger: BoundLogger | None = None,
    ) -> None:
        parents: set[ParentChildGroup] = set()
        self._process_diff(diff, None, parents, 0)
        trees_to_check: set[type[MP_Node]] = set()
        for parent_type, parent_id, group in parents:
            parent = self.get(parent_type, parent_id)
            child_type = getattr(self, group)
            if not child_type._is_orderable:
                continue

            log.debug("Re-ordering children under %s:%s (group %s)" % (parent_type._modelname, parent_id, group))
            self.reorder_children(parent, group)
            assert issubclass(child_type, DjangoDiffModel)
            mp_model = child_type._mpnode_or_none()
            if mp_model:
                trees_to_check.add(mp_model)
        for mp_model in trees_to_check:
            probs = mp_model.find_problems()
            if any(probs):
                raise Exception("Problems found in %s: %s" % (mp_model, probs))
        return super().sync_complete(source, diff, flags, logger)


class JSONAdapter(TypedAdapter):
    data: Any

    def __init__(
        self,
        json_path: Path,
        name: str | None = None,
        internal_storage_engine: type[BaseStore] | BaseStore = LocalStore,
    ):
        self.json_path = json_path
        super().__init__(name=name, internal_storage_engine=internal_storage_engine)

    def load_json(self):
        with self.json_path.open('r') as f:
            self.data = json.load(f)
