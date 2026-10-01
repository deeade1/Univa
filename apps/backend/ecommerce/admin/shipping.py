from adminsortable2.admin import \
    SortableAdminMixin  # optional if you want sorting
from django.contrib import admin
from django.contrib.admin.widgets import (AdminTextareaWidget,
                                          AdminTextInputWidget)
from django.db import models
from django.forms import Textarea, TextInput
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from ecommerce.modelse.shipping import (ShippingMethod, ShippingMethodChannelListing,
                     ShippingMethodPostalCodeRule, ShippingMethodTranslation,
                     ShippingZone)


class ShippingZoneCountriesFilter(admin.SimpleListFilter):
    title = _('has countries')
    parameter_name = 'has_countries'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('With countries')),
            ('no', _('Without countries')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(countries__len__gt=0)
        if self.value() == 'no':
            return queryset.filter(countries__len=0)


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'countries_display',
        'default',
        'channel_count',
        'shipping_method_count',
    )
    list_filter = (
        'default',
        ShippingZoneCountriesFilter,
        ('channels', RelatedDropdownFilter),
    )
    search_fields = ('name', 'countries')
    filter_horizontal = ('channels',)
    readonly_fields = ('shipping_method_count',)
    formfield_overrides = {
        models.CharField: {'widget': AdminTextInputWidget(attrs={'size': '50'})},
        models.TextField: {'widget': AdminTextareaWidget(attrs={'rows': 4, 'cols': 60})},
    }
    actions = ['set_as_default', 'remove_default']
    save_on_top = True
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('channels', 'shipping_methods')

    def countries_display(self, obj):
        if not obj.countries:
            return "-"
        return format_html(", ".join([str(code) for code in obj.countries]))
    countries_display.short_description = _("Countries")

    def channel_count(self, obj):
        return obj.channels.count()
    channel_count.short_description = _("Channels")

    def shipping_method_count(self, obj):
        url = (
            reverse("admin:shipping_shippingmethod_changelist")
            + f"?shipping_zone__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.shipping_methods.count())
    shipping_method_count.short_description = _("Methods")

    @admin.action(description=_("Set selected zones as default"))
    def set_as_default(self, request, queryset):
        updated = queryset.update(default=True)
        self.message_user(request, _("%d shipping zones set as default.") % updated)

    @admin.action(description=_("Remove default status from selected zones"))
    def remove_default(self, request, queryset):
        updated = queryset.update(default=False)
        self.message_user(request, _("%d shipping zones no longer default.") % updated)

    fieldsets = (
        (None, {
            'fields': ('name', 'default', 'description')
        }),
        (_("Countries"), {
            'fields': ('countries',)
        }),
        (_("Channels"), {
            'fields': ('channels',)
        }),
        (_("Statistics"), {
            'fields': ('shipping_method_count',),
            'classes': ('collapse',)
        }),
    )


class ShippingMethodChannelListingInline(admin.TabularInline):
    model = ShippingMethodChannelListing
    extra = 1
    min_num = 1
    formfield_overrides = {
        # Display decimals with small input box
        ShippingMethodChannelListing.price_amount.field: {'widget': TextInput(attrs={'size': '10'})},
        ShippingMethodChannelListing.minimum_order_price_amount.field: {'widget': TextInput(attrs={'size': '10'})},
        ShippingMethodChannelListing.maximum_order_price_amount.field: {'widget': TextInput(attrs={'size': '10'})},
    }
    readonly_fields = ('currency_display',)
    fields = (
        'channel',
        'price_amount',
        'minimum_order_price_amount',
        'maximum_order_price_amount',
        'currency_display',
        'is_active',
    )

    def currency_display(self, obj):
        return obj.currency
    currency_display.short_description = _("Currency")



class ShippingMethodPostalCodeRuleInline(admin.TabularInline):
    model = ShippingMethodPostalCodeRule
    extra = 1
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '20'})},
    }


class ShippingMethodTranslationInline(admin.TabularInline):
    model = ShippingMethodTranslation
    extra = 1
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '50'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 60})},
    }


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'type_display',
        'shipping_zone_link',
        'tax_class_link',
        'channel_listings_count',
        'postal_code_rules_count',
        'is_active',
    )
    list_filter = (
        'type',
        ('shipping_zone', RelatedDropdownFilter),
        ('tax_class', RelatedDropdownFilter),
    )
    search_fields = ('name', 'shipping_zone__name')
    readonly_fields = (
        'channel_listings_count',
        'postal_code_rules_count',
        'excluded_products_count',
    )
    filter_horizontal = ('excluded_products',)
    inlines = (
        ShippingMethodChannelListingInline,
        ShippingMethodPostalCodeRuleInline,
        ShippingMethodTranslationInline,
    )
    actions = ['enable_methods', 'disable_methods']
    save_on_top = True
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'shipping_zone', 'tax_class'
        ).prefetch_related(
            'channel_listings', 'postal_code_rules', 'excluded_products'
        )

    def type_display(self, obj):
        return obj.get_type_display()
    type_display.short_description = _("Type")
    type_display.admin_order_field = "type"

    def shipping_zone_link(self, obj):
        url = reverse("admin:shipping_shippingzone_change", args=[obj.shipping_zone.id])
        return format_html('<a href="{}">{}</a>', url, obj.shipping_zone)
    shipping_zone_link.short_description = _("Shipping Zone")
    shipping_zone_link.admin_order_field = "shipping_zone__name"

    def tax_class_link(self, obj):
        if not obj.tax_class:
            return "-"
        url = reverse("admin:tax_taxclass_change", args=[obj.tax_class.id])
        return format_html('<a href="{}">{}</a>', url, obj.tax_class)
    tax_class_link.short_description = _("Tax Class")
    tax_class_link.admin_order_field = "tax_class__name"

    def channel_listings_count(self, obj):
        return obj.channel_listings.count()
    channel_listings_count.short_description = _("Channel Listings")

    def postal_code_rules_count(self, obj):
        return obj.postal_code_rules.count()
    postal_code_rules_count.short_description = _("Postal Code Rules")

    def excluded_products_count(self, obj):
        return obj.excluded_products.count()
    excluded_products_count.short_description = _("Excluded Products")

    def is_active(self, obj):
        return any(cl.is_active for cl in obj.channel_listings.all())
    is_active.boolean = True
    is_active.short_description = _("Active")

    @admin.action(description=_("Enable selected shipping methods"))
    def enable_methods(self, request, queryset):
        from django.db import transaction
        with transaction.atomic():
            for method in queryset:
                method.channel_listings.update(is_active=True)
        self.message_user(request, _("Selected shipping methods enabled."))

    @admin.action(description=_("Disable selected shipping methods"))
    def disable_methods(self, request, queryset):
        from django.db import transaction
        with transaction.atomic():
            for method in queryset:
                method.channel_listings.update(is_active=False)
        self.message_user(request, _("Selected shipping methods disabled."))

    fieldsets = (
        (None, {
            'fields': ('name', 'type', 'shipping_zone', 'tax_class')
        }),
        (_("Weight Restrictions"), {
            'fields': ('minimum_order_weight', 'maximum_order_weight'),
            'classes': ('collapse',)
        }),
        (_("Product Exclusions"), {
            'fields': ('excluded_products', 'excluded_products_count'),
            'classes': ('collapse',)
        }),
        (_("Statistics"), {
            'fields': ('channel_listings_count', 'postal_code_rules_count'),
            'classes': ('collapse',)
        }),
    )



@admin.register(ShippingMethodChannelListing)
class ShippingMethodChannelListingAdmin(admin.ModelAdmin):
    list_display = (
        'shipping_method_link',
        'channel_link',
        'price_display',
        'min_order_price_display',
        'max_order_price_display',
        'is_active',
    )
    list_filter = (
        'is_active',
        ('channel', admin.RelatedOnlyFieldListFilter),
        ('shipping_method__shipping_zone', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        'shipping_method__name',
        'channel__name',
    )
    list_select_related = ('shipping_method', 'channel')

    # Display links
    def shipping_method_link(self, obj):
        url = reverse("admin:shipping_shippingmethod_change", args=[obj.shipping_method.id])
        return format_html('<a href="{}">{}</a>', url, obj.shipping_method)
    shipping_method_link.short_description = _("Shipping Method")
    shipping_method_link.admin_order_field = "shipping_method__name"

    def channel_link(self, obj):
        url = reverse("admin:channel_channel_change", args=[obj.channel.id])
        return format_html('<a href="{}">{}</a>', url, obj.channel)
    channel_link.short_description = _("Channel")
    channel_link.admin_order_field = "channel__name"

    # Display money fields
    def price_display(self, obj):
        return obj.price
    price_display.short_description = _("Price")

    def min_order_price_display(self, obj):
        return obj.minimum_order_price if obj.minimum_order_price_amount is not None else "-"
    min_order_price_display.short_description = _("Min Order Price")

    def max_order_price_display(self, obj):
        return obj.maximum_order_price if obj.maximum_order_price_amount is not None else "-"
    max_order_price_display.short_description = _("Max Order Price")

    # Fieldsets for editing
    fieldsets = (
        (None, {
            'fields': ('shipping_method', 'channel', 'is_active')
        }),
        (_("Pricing"), {
            'fields': (
                'price_amount',
                'minimum_order_price_amount',
                'maximum_order_price_amount',
                'currency',
            )
        }),
    )


@admin.register(ShippingMethodPostalCodeRule)
class ShippingMethodPostalCodeRuleAdmin(admin.ModelAdmin):
    list_display = (
        'shipping_method_link',
        'inclusion_type_display',
        'range_display',
    )
    list_filter = (
        'inclusion_type',
        ('shipping_method__shipping_zone', RelatedDropdownFilter),
    )
    search_fields = (
        'start',
        'end',
        'shipping_method__name',
    )
    list_select_related = ('shipping_method',)

    def shipping_method_link(self, obj):
        url = reverse("admin:shipping_shippingmethod_change", args=[obj.shipping_method.id])
        return format_html('<a href="{}">{}</a>', url, obj.shipping_method)
    shipping_method_link.short_description = _("Shipping Method")
    shipping_method_link.admin_order_field = "shipping_method__name"

    def inclusion_type_display(self, obj):
        return obj.get_inclusion_type_display()
    inclusion_type_display.short_description = _("Inclusion Type")
    inclusion_type_display.admin_order_field = "inclusion_type"

    def range_display(self, obj):
        return f"{obj.start} - {obj.end}" if obj.end else obj.start
    range_display.short_description = _("Postal Code Range")

    fieldsets = (
        (None, {
            'fields': ('shipping_method', 'inclusion_type')
        }),
        (_("Postal Code Range"), {
            'fields': ('start', 'end')
        }),
    )


@admin.register(ShippingMethodTranslation)
class ShippingMethodTranslationAdmin(admin.ModelAdmin):
    list_display = (
        'shipping_method_link',
        'language_code',
        'name',
    )
    list_filter = (
        'language_code',
        ('shipping_method__shipping_zone', RelatedDropdownFilter),
    )
    search_fields = (
        'name',
        'shipping_method__name',
    )
    list_select_related = ('shipping_method',)

    def shipping_method_link(self, obj):
        url = reverse("admin:shipping_shippingmethod_change", args=[obj.shipping_method.id])
        return format_html('<a href="{}">{}</a>', url, obj.shipping_method)
    shipping_method_link.short_description = _("Shipping Method")
    shipping_method_link.admin_order_field = "shipping_method__name"

    fieldsets = (
        (None, {
            'fields': ('shipping_method', 'language_code')
        }),
        (_("Content"), {
            'fields': ('name', 'description')
        }),
    )