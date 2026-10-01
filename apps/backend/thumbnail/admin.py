from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from .models import THUMBNAIL_SIZES, Thumbnail, ThumbnailFormat


class ThumbnailSizeFilter(admin.SimpleListFilter):
    title = _('thumbnail size')
    parameter_name = 'size'

    def lookups(self, request, model_admin):
        return [(size, f"{size}px") for size in sorted(THUMBNAIL_SIZES)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(size=self.value())


class ThumbnailFormatFilter(admin.SimpleListFilter):
    title = _('format')
    parameter_name = 'format'

    def lookups(self, request, model_admin):
        return ThumbnailFormat.CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(format=self.value())


@admin.register(Thumbnail)
class ThumbnailAdmin(admin.ModelAdmin):
    list_display = (
        'thumbnail_preview',
        'size_display',
        'format_display',
        'content_object_link',
        'user_link',
        'created_at',
    )
    list_filter = (
        ThumbnailSizeFilter,
        ThumbnailFormatFilter,
        ('category', RelatedDropdownFilter),
        ('collection', RelatedDropdownFilter),
        ('product_media', RelatedDropdownFilter),
        ('user', RelatedDropdownFilter),
    )
    search_fields = (
        'category__name',
        'collection__name',
        'product_media__alt',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
        'thumbnail_preview_large',
        'content_object_link',
        'user_link',
    )
    list_select_related = (
        'category',
        'collection',
        'product_media',
        'product_media__product',
        'user',
    )
    actions = ['regenerate_thumbnails']
    date_hierarchy = 'created_at'
    save_on_top = True
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category',
            'collection',
            'product_media',
            'product_media__product',
            'user',
        )

    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image.url
            )
        return "-"
    thumbnail_preview.short_description = _("Preview")

    def thumbnail_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 100%;" />',
                obj.image.url
            )
        return "-"
    thumbnail_preview_large.short_description = _("Large Preview")

    def size_display(self, obj):
        return f"{obj.size}px"
    size_display.short_description = _("Size")
    size_display.admin_order_field = "size"

    def format_display(self, obj):
        return obj.get_format_display() if obj.format else "-"
    format_display.short_description = _("Format")
    format_display.admin_order_field = "format"

    def content_object_link(self, obj):
        if obj.category:
            url = reverse("admin:product_category_change", args=[obj.category.id])
            return format_html('<a href="{}">Category: {}</a>', url, obj.category.name)
        elif obj.collection:
            url = reverse("admin:product_collection_change", args=[obj.collection.id])
            return format_html('<a href="{}">Collection: {}</a>', url, obj.collection.name)
        elif obj.product_media:
            url = reverse("admin:product_productmedia_change", args=[obj.product_media.id])
            product_name = obj.product_media.product.name if obj.product_media.product else "Unknown"
            return format_html(
                '<a href="{}">Product Media: {} ({})</a>',
                url,
                obj.product_media.alt or "No alt text",
                product_name
            )
        return "-"
    content_object_link.short_description = _("Content Object")

    def user_link(self, obj):
        if obj.user:
            url = reverse("admin:accounts_userprofile_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.id)
        return "-"
    user_link.short_description = _("User")
    user_link.admin_order_field = "user_id"

    @admin.action(description=_("Regenerate selected thumbnails"))
    def regenerate_thumbnails(self, request, queryset):
        from .tasks import generate_thumbnails
        thumbnail_ids = list(queryset.values_list('id', flat=True))
        generate_thumbnails.delay(thumbnail_ids)
        self.message_user(
            request,
            _("Started regeneration of {} thumbnails in background.").format(len(thumbnail_ids))
        )

    fieldsets = (
        (None, {
            'fields': ('image', 'size', 'format')
        }),
        (_("Relations"), {
            'fields': ('category', 'collection', 'product_media', 'user', 'content_object_link', 'user_link'),
            'classes': ('collapse',)
        }),
        (_("Preview"), {
            'fields': ('thumbnail_preview_large',)
        }),
        (_("Metadata"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ['category', 'collection', 'product_media', 'user']:
            if db_field.name in ['category', 'collection']:
                kwargs['queryset'] = db_field.remote_field.model._default_manager.order_by('name')
            elif db_field.name == 'product_media':
                kwargs['queryset'] = db_field.remote_field.model._default_manager.order_by('alt')
            else:  # user
                kwargs['queryset'] = db_field.remote_field.model._default_manager.order_by('id')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
