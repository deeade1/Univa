from django.db import models
from django.contrib.gis.db.models import PointField
import django_filters

try:
    from pgvector.django import VectorField
except ImportError:
    VectorField = None


FILTER_OVERRIDES = {
    models.ImageField: {
        "filter_class": django_filters.CharFilter,
    },
    models.BinaryField: {
        "filter_class": django_filters.CharFilter,
    },
    PointField: {
        "filter_class": django_filters.CharFilter,
    },
}

if VectorField:
    FILTER_OVERRIDES[VectorField] = {
        "filter_class": django_filters.CharFilter,
    }