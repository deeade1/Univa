"""
Shared GraphQL GIS field converters.

This module provides the canonical Graphene-Django conversion for
GeoDjango GIS fields used throughout Univa.

Architecture
------------
Domain GraphQL modules must not register competing PointField
converters independently.

Instead:

    GeoDjango PointField
            │
            ▼
    graphq.core.types.gis
            │
            ▼
    Graphene GIS scalar

This keeps GIS serialization consistent across accounts, transport,
real estate, and other domain applications.
"""

from django.contrib.gis.db.models import PointField
from graphene_django.converter import convert_django_field
from graphene_gis.converter import gis_converter


@convert_django_field.register(PointField)
def convert_point_field(field, registry=None):
    """
    Convert a GeoDjango PointField into the canonical GraphQL GIS type.

    The actual serialization/parsing behavior is delegated to
    graphene-gis so every GraphQL domain uses the same representation.
    """
    return gis_converter(field, registry)