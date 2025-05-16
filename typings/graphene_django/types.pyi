from django.db.models import Model
from django.db.models.query import QuerySet
from graphene.relay import Connection
from graphene.types.objecttype import ObjectType, ObjectTypeOptions

from .registry import Registry

ALL_FIELDS = ...
def construct_fields(model, registry, only_fields, exclude_fields, convert_choices_to_enum=...): # -> OrderedDict[Any, Any]:
    ...

def validate_fields(type_, model, fields, only_fields, exclude_fields): # -> None:
    ...

class DjangoObjectTypeOptions[M: Model](ObjectTypeOptions):
    model: type[M] = ...
    registry: Registry = ...
    connection: type[Connection] = ...
    filter_fields = ...
    filterset_class = ...


type _FieldList = list[str] | tuple[str, ...]

class DjangoObjectType[M: Model](ObjectType):
    _meta: DjangoObjectTypeOptions[M]

    @classmethod
    def __init_subclass_with_meta__(  # type: ignore[override]
        cls,
        model: type[M] = ...,
        registry: Registry | None = ...,
        skip_registry: bool = ...,
        only_fields: _FieldList = ...,
        fields: _FieldList = ...,
        exclude_fields: _FieldList = ...,
        exclude: _FieldList = ...,
        filter_fields: _FieldList = ...,
        filterset_class: type | None = ...,
        connection=...,
        connection_class=...,
        use_connection=...,
        interfaces=...,
        convert_choices_to_enum=...,
        _meta=...,
        **options,
    ) -> None: ...

    @staticmethod
    def resolve_id(root, info) -> str:
        ...

    @classmethod
    def is_type_of(cls, root, info) -> bool:
        ...

    @classmethod
    def get_queryset[QS: QuerySet](cls, queryset: QS, info) -> QS:
        ...

    @classmethod
    def get_node(cls, info, id) -> M | None:
        ...



class ErrorType(ObjectType):
    field = ...
    messages = ...
    @classmethod
    def from_errors(cls, errors): # -> list[Self]:
        ...
