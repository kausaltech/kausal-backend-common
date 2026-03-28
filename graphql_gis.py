from __future__ import annotations

import json
from typing import Any, ClassVar

from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import GEOSGeometry
from graphene.types import Scalar
from graphene_django.converter import convert_django_field
from graphql.language import ast

# GIS-related types copied from https://github.com/EverWinter23/graphene-gis


class GISScalar(Scalar):
    geom_typeid: ClassVar[int]

    @staticmethod
    def serialize(geometry) -> dict[str, Any]:
        return json.loads(geometry.geojson)

    @classmethod
    def parse_literal(cls, node) -> dict[str, Any]:
        assert isinstance(node, ast.StringValueNode)
        geometry = GEOSGeometry(node.value)
        return json.loads(geometry.geojson)

    @classmethod
    def parse_value(cls, node) -> dict[str, Any]:
        geometry = GEOSGeometry(node.value)
        return json.loads(geometry.geojson)


class PointScalar(GISScalar):
    geom_typeid = 0

    class Meta:
        description = 'A GIS Point geojson'


class LineStringScalar(GISScalar):
    geom_typeid = 1

    class Meta:
        description = 'A GIS LineString geojson'


class PolygonScalar(GISScalar):
    geom_typeid = 3

    class Meta:
        description = 'A GIS Polygon geojson'


GIS_FIELD_SCALAR = {
    'PointField': PointScalar,
    'LineStringField': LineStringScalar,
    'PolygonField': PolygonScalar,
    'GeometryField': GISScalar,
}


@convert_django_field.register(gis_models.GeometryField)
@convert_django_field.register(gis_models.LineStringField)
@convert_django_field.register(gis_models.PointField)
@convert_django_field.register(gis_models.PolygonField)
def gis_converter(field, registry=None):  # pyright: ignore[reportUnusedParameter]
    class_name = field.__class__.__name__
    return GIS_FIELD_SCALAR[class_name](
        required=not field.null,
        description=field.help_text,
    )
