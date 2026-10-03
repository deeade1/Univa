# core/admin/region.py
# ---------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------

from django.contrib import admin as _admin  # noqa: F401
from mptt.admin import DraggableMPTTAdmin

from core.models.region import Region, RegionTranslation


@_admin.register(Region)
class RegionAdmin(DraggableMPTTAdmin):
    list_display = (
        "tree_actions",
        "indented_title",
        "level",
        "code",
        "currency",
        "timezone",
        "is_active",
    )
    list_filter = ("level", "is_active", "currency")
    search_fields = ("name", "slug", "code")
    mptt_level_indent = 20


@_admin.register(RegionTranslation)
class RegionTranslationAdmin(_admin.ModelAdmin):
    list_display = ("region", "language_code", "name")
    list_filter = ("language_code",)
    search_fields = ("name", "slug")