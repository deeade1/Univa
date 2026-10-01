import json

from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from django_prices.templatetags import prices_i18n

from ecommerce.models.product import (Category, CategoryTranslation, Collection,
                     CollectionChannelListing, CollectionProduct,
                     CollectionTranslation, DigitalContent, DigitalContentUrl,
                     Product, ProductChannelListing, ProductMedia,
                     ProductTranslation, ProductType, ProductVariant,
                     ProductVariantChannelListing, ProductVariantTranslation,
                     VariantMedia)


class CategoryTranslationInline(admin.TabularInline):
    model = CategoryTranslation
    extra = 0
    fields = ('language_code', 'name', 'description', 'seo_title', 'seo_description')
    show_change_link = True

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent_link', 'background_image_display', 'product_count')
    list_filter = ('parent',)
    search_fields = ('name', 'slug', 'description_plaintext')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CategoryTranslationInline]
    readonly_fields = ('product_count', 'background_image_display', 'parent_link')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent_link', 'background_image', 'background_image_alt')
        }),
        ('Description', {
            'fields': ('description', 'description_plaintext'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('seo_title', 'seo_description'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('product_count',),
            'classes': ('collapse',)
        }),
    )

    def parent_link(self, obj):
        if not obj.parent:
            return "-"
        url = reverse("admin:product_category_change", args=(obj.parent.id,))
        return format_html('<a href="{}">{}</a>', url, obj.parent.name)
    parent_link.short_description = _("Parent Category")

    def background_image_display(self, obj):
        if obj.background_image:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.background_image.url)
        return "-"
    background_image_display.short_description = _("Background Image")

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = _("Product Count")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent').prefetch_related('products')

@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'kind', 'has_variants', 'is_shipping_required', 'is_digital', 'tax_class_link')
    list_filter = ('kind', 'has_variants', 'is_shipping_required', 'is_digital')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('tax_class_link',)
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'kind', 'tax_class_link')
        }),
        ('Attributes', {
            'fields': ('has_variants', 'is_shipping_required', 'is_digital'),
            'classes': ('collapse',)
        }),
        ('Default Weight', {
            'fields': ('weight',),
            'classes': ('collapse',)
        }),
    )

    def tax_class_link(self, obj):
        if not obj.tax_class:
            return "-"
        url = reverse("admin:tax_taxclass_change", args=(obj.tax_class.id,))
        return format_html('<a href="{}">{}</a>', url, obj.tax_class.name)
    tax_class_link.short_description = _("Tax Class")

class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 0
    readonly_fields = ('image_display', 'type_display')
    fields = ('image_display', 'type_display', 'alt', 'sort_order')
    
    def image_display(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.image.url)
        elif obj.external_url:
            return format_html('<a href="{}" target="_blank">External Media</a>', obj.external_url)
        return "-"
    image_display.short_description = _("Preview")
    
    def type_display(self, obj):
        return obj.get_type_display()
    type_display.short_description = _("Type")

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    readonly_fields = ('sku', 'price_display', 'inventory_display')
    fields = ('sku', 'name', 'price_display', 'inventory_display', 'track_inventory')
    
    def price_display(self, obj):
        # This would need to be customized based on your actual pricing logic
        return "-"
    price_display.short_description = _("Price")
    
    def inventory_display(self, obj):
        # This would need to be customized based on your actual inventory logic
        return "-"
    inventory_display.short_description = _("Inventory")

class ProductChannelListingInline(admin.TabularInline):
    model = ProductChannelListing
    extra = 0
    readonly_fields = ('channel_link', 'price_display', 'visible_in_listings')
    fields = ('channel_link', 'price_display', 'visible_in_listings', 'published_at')
    
    def channel_link(self, obj):
        url = reverse("admin:channel_channel_change", args=(obj.channel.id,))
        return format_html('<a href="{}">{}</a>', url, obj.channel.name)
    channel_link.short_description = _("Channel")
    
    def price_display(self, obj):
        return prices_i18n.amount(obj.price) if obj.price else "-"
    price_display.short_description = _("Price")

class ProductTranslationInline(admin.TabularInline):
    model = ProductTranslation
    extra = 0
    fields = ('language_code', 'name', 'description', 'seo_title', 'seo_description')
    show_change_link = True


class ProductVariantChannelListingInline(admin.TabularInline):
    model = ProductVariantChannelListing
    extra = 0
    readonly_fields = ('channel_link', 'price_display', 'cost_price_display')
    fields = ('channel_link', 'price_display', 'cost_price_display', 'preorder_quantity_threshold')
    
    def channel_link(self, obj):
        url = reverse("admin:channel_channel_change", args=(obj.channel.id,))
        return format_html('<a href="{}">{}</a>', url, obj.channel.name)
    channel_link.short_description = _("Channel")
    
    def price_display(self, obj):
        return prices_i18n.amount(obj.price) if obj.price else "-"
    price_display.short_description = _("Price")
    
    def cost_price_display(self, obj):
        return prices_i18n.amount(obj.cost_price) if obj.cost_price else "-"
    cost_price_display.short_description = _("Cost Price")

class VariantMediaInline(admin.TabularInline):
    model = VariantMedia
    extra = 0
    readonly_fields = ('media_preview',)
    fields = ('media_preview', 'media')
    
    def media_preview(self, obj):
        if obj.media.image:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.media.image.url)
        return "-"
    media_preview.short_description = _("Preview")

class DigitalContentInline(admin.TabularInline):
    model = DigitalContent
    extra = 0
    fields = ('content_file', 'max_downloads', 'url_valid_days', 'automatic_fulfillment')

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'product_link', 'is_preorder', 'track_inventory', 'updated_at')
    list_filter = ('is_preorder', 'track_inventory', 'product__product_type')
    search_fields = ('sku', 'name', 'product__name')
    inlines = [ProductVariantChannelListingInline, VariantMediaInline, DigitalContentInline]
    readonly_fields = ('product_link', 'weight_display')
    fieldsets = (
        (None, {
            'fields': ('product_link', 'sku', 'name')
        }),
        ('Inventory', {
            'fields': ('track_inventory', 'weight_display', 'quantity_limit_per_customer')
        }),
        ('Preorder', {
            'fields': ('is_preorder', 'preorder_end_date', 'preorder_global_threshold'),
            'classes': ('collapse',)
        }),
    )

    def product_link(self, obj):
        url = reverse("admin:product_product_change", args=(obj.product.id,))
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    product_link.short_description = _("Product")

    def weight_display(self, obj):
        if obj.weight:
            return f"{obj.weight.value} {obj.weight.unit}"
        return "-"
    weight_display.short_description = _("Weight")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')

class DigitalContentUrlInline(admin.TabularInline):
    model = DigitalContentUrl
    extra = 0
    readonly_fields = ('token', 'created_at', 'download_num', 'line_link')
    fields = ('token', 'created_at', 'download_num', 'line_link')
    
    def line_link(self, obj):
        if not obj.line:
            return "-"
        url = reverse("admin:order_orderline_change", args=(obj.line.id,))
        return format_html('<a href="{}">Line #{}</a>', url, obj.line.id)
    line_link.short_description = _("Order Line")

@admin.register(DigitalContent)
class DigitalContentAdmin(admin.ModelAdmin):
    list_display = ('product_variant_link', 'content_type', 'automatic_fulfillment', 'max_downloads')
    inlines = [DigitalContentUrlInline]
    readonly_fields = ('product_variant_link',)
    fieldsets = (
        (None, {
            'fields': ('product_variant_link', 'use_default_settings', 'automatic_fulfillment')
        }),
        ('Content', {
            'fields': ('content_type', 'content_file'),
            'classes': ('collapse',)
        }),
        ('Access', {
            'fields': ('max_downloads', 'url_valid_days'),
            'classes': ('collapse',)
        }),
    )

    def product_variant_link(self, obj):
        url = reverse("admin:product_productvariant_change", args=(obj.product_variant.id,))
        return format_html('<a href="{}">{}</a>', url, obj.product_variant.sku or obj.product_variant.name)
    product_variant_link.short_description = _("Product Variant")


class CollectionProductInline(SortableAdminMixin, admin.TabularInline):
    model = CollectionProduct
    extra = 0
    fields = ('product_link',)
    readonly_fields = ('product_link',)

    def product_link(self, obj):
        url = reverse("admin:product_product_change", args=(obj.product.id,))
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    product_link.short_description = _("Product")


class CollectionChannelListingInline(admin.TabularInline):
    model = CollectionChannelListing
    extra = 0
    readonly_fields = ('channel_link', 'is_published')
    fields = ('channel_link', 'is_published', 'published_at')
    
    def channel_link(self, obj):
        url = reverse("admin:channel_channel_change", args=(obj.channel.id,))
        return format_html('<a href="{}">{}</a>', url, obj.channel.name)
    channel_link.short_description = _("Channel")
    
    def is_published(self, obj):
        return obj.is_published()
    is_published.boolean = True
    is_published.short_description = _("Published")

class CollectionTranslationInline(admin.TabularInline):
    model = CollectionTranslation
    extra = 0
    fields = ('language_code', 'name', 'description', 'seo_title', 'seo_description')
    show_change_link = True

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'background_image_display', 'product_count', 'is_published')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CollectionTranslationInline, CollectionProductInline, CollectionChannelListingInline]
    readonly_fields = ('background_image_display', 'product_count')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'background_image', 'background_image_alt')
        }),
        ('Description', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('seo_title', 'seo_description'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('product_count',),
            'classes': ('collapse',)
        }),
    )

    def background_image_display(self, obj):
        if obj.background_image:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.background_image.url)
        return "-"
    background_image_display.short_description = _("Background Image")

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = _("Product Count")

    def is_published(self, obj):
        return any(cl.is_published() for cl in obj.channel_listings.all())
    is_published.boolean = True
    is_published.short_description = _("Published")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('products', 'channel_listings')




# ------------------------------------
# ✅ SORTABLE INLINE FOR PRODUCT MEDIA
# ------------------------------------
class ProductMediaInline(SortableAdminMixin, admin.TabularInline):
    """Inline admin for product media with drag-and-drop sorting support."""
    model = ProductMedia
    extra = 0
    fields = ('image_preview', 'alt')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 80px; border-radius: 6px;" />', obj.image.url)
        return "-"
    image_preview.short_description = _("Preview")


# ------------------------------------
# ✅ MAIN PRODUCT ADMIN
# ------------------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type_link', 'category_link', 'updated_at', 'is_published')
    list_filter = ('product_type', 'category', 'updated_at')
    search_fields = ('name', 'description_plaintext', 'variants__sku')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [
        ProductTranslationInline,
        ProductMediaInline,
        ProductVariantInline,
        ProductChannelListingInline,
    ]
    readonly_fields = ('product_type_link', 'category_link', 'default_variant_link')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'product_type_link', 'category_link', 'default_variant_link')
        }),
        ('Description', {
            'fields': ('description', 'description_plaintext'),
            'classes': ('collapse',)
        }),
        ('Attributes', {
            'fields': ('weight', 'rating', 'tax_class'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('seo_title', 'seo_description'),
            'classes': ('collapse',)
        }),
    )

    # ---- Custom Links ----
    def product_type_link(self, obj):
        url = reverse("admin:product_producttype_change", args=(obj.product_type.id,))
        return format_html('<a href="{}">{}</a>', url, obj.product_type.name)
    product_type_link.short_description = _("Product Type")

    def category_link(self, obj):
        if not obj.category:
            return "-"
        url = reverse("admin:product_category_change", args=(obj.category.id,))
        return format_html('<a href="{}">{}</a>', url, obj.category.name)
    category_link.short_description = _("Category")

    def default_variant_link(self, obj):
        if not obj.default_variant:
            return "-"
        url = reverse("admin:product_productvariant_change", args=(obj.default_variant.id,))
        return format_html('<a href="{}">{}</a>', url, obj.default_variant.sku or obj.default_variant.name)
    default_variant_link.short_description = _("Default Variant")

    # ---- Boolean and queryset helpers ----
    def is_published(self, obj):
        return any(cl.is_published() for cl in obj.channel_listings.all())
    is_published.boolean = True
    is_published.short_description = _("Published")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product_type', 'category', 'default_variant'
        ).prefetch_related('channel_listings')
