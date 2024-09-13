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
from pydantic import BaseModel, ConfigDict, IPvAnyAddress, Json
from pydantic.fields import FieldInfo
from pydantic.v1.fields import Required

from pydantic_core import PydanticUndefined

BaseModel.model_config['protected_namespaces'] = ()

from diffsync import Adapter, DiffSyncModel
from diffsync.diff import Diff, DiffElement
from diffsync.enum import DiffSyncActions, DiffSyncFlags, DiffSyncModelFlags
from diffsync.exceptions import ObjectNotCreated
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
                logger.warning(
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
TREE_PARENT_ATTRIBUTE = 'parent'

class DjangoDiffModel(DiffSyncModel, Generic[_ModelT]):
    _model: ClassVar[type[_ModelT]]  # type: ignore[misc]
    _django_fields: ClassVar[DjangoModelFields]
    _allow_related_model_deletion: ClassVar[bool] = False
    _is_orderable: ClassVar[bool] = False
    model_flags: DiffSyncModelFlags = DiffSyncModelFlags.NATURAL_DELETION_ORDER

    sibling_order: int | None = None
    """Order of the instance under the same parent."""

    _instance: _ModelT | None = None
    _instance_pk: int | None = None
    _parent_id: str | None = None
    _parent_type: type[DjangoDiffModel] | None = None

    model_config = ConfigDict(extra='allow', protected_namespaces=())

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs) -> None:
        if not hasattr(cls, '_model'):
            return
        include_fields = list(set(cls._identifiers) | set(cls._attributes))
        django_fields = pydantic_from_django_model(cls, cls._model, include_fields=include_fields)
        cls._django_fields = django_fields

        internal_attrs = []
        mp_model = cls._mpnode_or_none()
        if mp_model:
            if TREE_PARENT_ATTRIBUTE not in cls._attributes:
                msg = f"{cls._model!r} is an MP_Node, but '{TREE_PARENT_ATTRIBUTE}' is not in _attributes"
                raise AttributeError(msg)
            if not mp_model.node_order_by:
                cls._is_orderable = True

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
    def create_related(cls, _adapter: DjangoAdapter, _ids: dict, _attrs: dict, _instance: _ModelT, /) -> None:
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
    def create(cls, adapter: Adapter, ids: dict, attrs: dict) -> Self | None:
        if not isinstance(adapter, DjangoAdapter):
            return super().create(adapter, ids, attrs)

        create_kwargs = cls.get_create_kwargs(adapter, ids, attrs)
        try:
            obj = adapter.create_instance(cls, create_kwargs)
            obj_pk = obj.pk
            cls.create_related(adapter, ids, attrs, obj)
        except Exception as e:
            msg = f"Unable to create a new {cls._model._meta.label} instance with ids {ids}"
            raise ObjectNotCreated(msg) from e

        self = super().create(adapter, ids, attrs)
        if self is None:
            return None
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

    """
    def _get_sibling_order(self) -> int:
        sort_order = 0
        ss = self.sibling_ids
        assert isinstance(self.adapter, TypedAdapter)
        while ss.prev is not None:
            sibling = self.adapter.get(type(self), ss.prev)
            ss = sibling.sibling_ids
            sort_order += 1
        return sort_order
    """

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

        if self._mpnode_or_none() and TREE_PARENT_ATTRIBUTE in update_kwargs:
            new_parent_id = update_kwargs.pop(TREE_PARENT_ATTRIBUTE, None)
            assert self._parent_type is not None
            assert self._parent_id is not None
            raise Exception("Not supported")  # FIXME
            new_parent, old_parent = self.adapter.get_by_uids([new_parent_id, self._parent_id], self._parent_type)

        if self._is_orderable:
            sibling_order = update_kwargs.pop(SIBLING_ORDER_ATTRIBUTE, None)
            if sibling_order is not None:
                assert self._parent_type is not None
                assert self._parent_id is not None
                _parent = self.adapter.get(self._parent_type, self._parent_id)
                # FIXME: Should we reorder the "children" attribute?

        if update_kwargs:
            for field_name, val in update_kwargs.items():
                setattr(obj, field_name, val)

            obj.save(update_fields=update_kwargs.keys(), force_update=True)

        return super().update(attrs)

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
        assert self._instance_pk is not None
        instance = self._model._default_manager.get(pk=self._instance_pk)
        if not self.is_object_deletion_allowed(instance):
            return None
        obj_count, related = instance.delete()
        # if related and not self._allow_related_model_deletion:
        #     msg = f"Deletion of {self.get_type()}: {self.get_unique_id()} resulted in deletion of other objects: {related}"
        #     raise ObjectNotDeleted(msg)
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

    def add_child(self, child: DiffSyncModel) -> None:
        super().add_child(child)
        if not isinstance(child, DjangoDiffModel) or not child._is_orderable:
            return

        if child.sibling_order is None:
            type_str = child.get_type()
            children_ids = getattr(self, self._children[type_str])
            child.sibling_order = len(children_ids) - 1
        child._parent_id = self.get_unique_id()
        child._parent_type = type(self)

    def remove_child(self, child: DiffSyncModel) -> None:
        super().remove_child(child)
        assert isinstance(child, DjangoDiffModel)
        if not child._is_orderable:
            return

        # Re-order the siblings
        for order, sibling in enumerate(self.get_children(type(child), ordered=True)):
            sibling.sibling_order = order


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

    def _create_mpnode[M: Model](
        self, cls: type[DjangoDiffModel[M]], instance: M, parent_id: str | None, sibling_order: int | None,
    ) -> M:
        parent = self.get(cls, parent_id) if parent_id else None
        assert isinstance(instance, MP_Node)
        if not cls._is_orderable:
            assert sibling_order is None
            if parent is None:
                instance.add_root(instance=instance)
            else:
                parent_obj = parent.get_django_instance()
                assert isinstance(parent_obj, MP_Node)
                instance = cast(M, parent_obj.add_child(instance=instance))
                parent_obj.save()
            return instance

        # Orderable mptree
        if parent is not None:
            assert sibling_order is not None
            left_sibling = parent.get_children(cls, ordered=True)[sibling_order - 1]
            sibling_obj = left_sibling.get_django_instance()
            assert isinstance(sibling_obj, MP_Node)
            instance = cast(M, sibling_obj.add_sibling(pos='right', instance=instance))
        else:
            instance = cast(M, instance.add_root(instance=instance))
        return instance

    def create_instance[M: Model](self, cls: type[DjangoDiffModel[M]], create_kwargs: dict) -> M:
        model = cast(type[M], cls._model)  # pyright: ignore
        mp_model = cls._mpnode_or_none()
        parent_id = None
        sibling_order: int | None = None

        if cls._is_orderable:
            sibling_order = create_kwargs.pop(SIBLING_ORDER_ATTRIBUTE)
            if not mp_model:
                sort_field = getattr(model, 'sort_order_field')  # noqa: B009
                create_kwargs[sort_field] = sibling_order

        if mp_model:
            parent_id = create_kwargs.pop(TREE_PARENT_ATTRIBUTE)

        instance = model(**create_kwargs)

        if mp_model:
            return self._create_mpnode(cls, instance, parent_id, sibling_order)

        instance.save()
        return instance

    def get_model_class(self, type_str: str) -> type[DjangoDiffModel]:
        cls = getattr(self, type_str)
        assert issubclass(cls, DjangoDiffModel)
        return cls

    def _process_diff_element(
        self, el: DiffElement, parent: DjangoDiffModel | None, group: str, parents: set[ParentChildGroup], indent: int,
    ) -> None:
        model = cast(DjangoDiffModel, getattr(self, el.type))
        if el.action == DiffSyncActions.DELETE:
            if model._is_orderable and parent is not None:
                parents.add((type(parent), parent.get_unique_id(), group))
            return

        if not el.has_diffs(include_children=True):
            return

        obj = self.get(el.type, el.keys)
        # print(' ' * indent, el.has_diffs(), '%s: %s' % (obj.get_type(), obj.get_unique_id()), el.get_attrs_diffs().get('+'))
        attrs = el.get_attrs_diffs().get('+', {})

        check_tree = False
        if model._mpnode_or_none() and TREE_PARENT_ATTRIBUTE in attrs:
            check_tree = True
        if model._is_orderable and SIBLING_ORDER_ATTRIBUTE in attrs:
            check_tree = True
        if parent is not None and check_tree:
            parents.add((type(parent), parent.get_unique_id(), group))

        assert isinstance(obj, DjangoDiffModel)
        self._process_diff(el.child_diff, obj, parents, indent + 1)

    def _process_diff(self, diff: Diff, parent: DjangoDiffModel | None, parents: set[ParentChildGroup], indent: int) -> None:
        for group in diff.groups():
            for child in diff.children[group].values():
                self._process_diff_element(child, parent, group, parents, indent)

    def _reorder_mptree(self, parent: MP_Node, children: list[DjangoDiffModel[MP_Node]]) -> None:
        db_pks: list[int] = list(parent.get_children().values_list('pk', flat=True))
        new_db_pks: list[int] = [cast(int, child._instance_pk) for child in children]
        assert len(db_pks) == len(new_db_pks)
        assert set(db_pks) == set(new_db_pks)
        #for order, db_child in enumerate(db_children):
        #    db_by_pk[db_child.pk] = db_child
        #    setattr(db_child, '_old_order', order)

        mgr = parent.__class__.objects
        nr_changes = 0
        for order, new_pk in enumerate(new_db_pks):
            if new_pk == db_pks[order]:
                continue

            nr_changes += 1
            db_child = mgr.get(pk=new_pk)
            db_pks.remove(new_pk)
            if order == 0:
                db_child.move(parent, 'first-child')
            else:
                db_child.move(mgr.get(pk=db_pks[order - 1]), 'right')
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

    def order_children(self, parent: DjangoDiffModel, group: str):
        child_type = getattr(self, group)
        assert issubclass(child_type, DjangoDiffModel)
        child_model = child_type._model  # pyright: ignore
        children = parent.get_children(child_type, ordered=True)

        if parent._mpnode_or_none() and child_type._mpnode_or_none():
            parent_obj = parent.get_django_instance()
            self._reorder_mptree(parent_obj, children)
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
            log.debug("Re-ordering children under %s:%s (group %s)" % (parent_type, parent_id, group))
            self.order_children(parent, group)
            child_type = getattr(self, group)
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
