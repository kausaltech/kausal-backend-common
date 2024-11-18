from __future__ import annotations

import dataclasses
import typing
from types import NoneType, UnionType
from typing import get_type_hints

import graphene


def create_from_dataclass(kls):
    field_types = get_type_hints(kls)
    fields = dataclasses.fields(kls)
    gfields = {}
    for field in fields:
        gf: type[graphene.Scalar]
        field_type = field_types[field.name]
        required = True
        if isinstance(field_type, UnionType):
            args = list(typing.get_args(field_type))
            if NoneType not in args:
                raise TypeError("Only NoneType supported in unions")
            args.remove(NoneType)
            if len(args) != 1:
                raise TypeError("Too many types in the union")
            field_type = args[0]
            required = False

        if field_type is bool or field_type == 'bool':
            gf = graphene.Boolean
        elif field_type is int:
            gf = graphene.Int
        else:
            raise Exception("Unsupported type: %s" % field.type)
        gfields[field.name] = gf(required=required)
    out = type(kls.__name__ + 'Type', (graphene.ObjectType,), gfields)
    return out