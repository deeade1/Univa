import json

from django.conf import settings
from django.contrib import admin
from django.db.models import Count, Q, Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from prices import Money

from django_prices.templatetags import prices_i18n

from ecommerce.models.discount import (CheckoutDiscount, CheckoutLineDiscount, OrderDiscount,
                     Promotion, PromotionEvent, PromotionRule,
                     PromotionRule_Variants, PromotionRuleTranslation,
                     PromotionTranslation, Voucher, VoucherChannelListing,
                     VoucherCode, VoucherCustomer, VoucherTranslation)


class VoucherCodeInline(admin.TabularInline):
    model = VoucherCode
    extra = 0
    readonly_fields = ('used', 'is_active_display')
    
    def used(self, obj):
        return obj.used
    used.short_description = _("Times Used")
    
    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.boolean = True
    is_active_display.short_description = _("Active")


class VoucherChannelListingInline(admin.TabularInline):
    model = VoucherChannelListing
    extra = 0
    raw_id_fields = ('channel',)
    readonly_fields = ('discount_value_display',)
    
    def discount_value_display(self, obj):
        return prices_i18n.amount(obj.discount)
    discount_value_display.short_description = _("Discount Value")

class VoucherCustomerInline(admin.TabularInline):
    model = VoucherCustomer
    extra = 0
    raw_id_fields = ('voucher_code',)
    readonly_fields = ('customer_email', 'get_voucher_link')
    verbose_name = _("Customer")
    verbose_name_plural = _("Customers")

    def get_voucher_link(self, obj):
        if obj.voucher_code.voucher:
            url = reverse("admin:discount_voucher_change", args=(obj.voucher_code.voucher.id,))
            return format_html('<a href="{}">{}</a>', url, obj.voucher_code.voucher.name)
        return "-"
    get_voucher_link.short_description = _("Voucher")

    def has_add_permission(self, request, obj=None):
        # Only allow adding if we're editing an existing voucher
        return obj is not None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.resolver_match.kwargs.get('object_id'):
            return qs.none()
        return qs.filter(voucher_code__voucher_id=request.resolver_match.kwargs['object_id'])



@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'get_code_list', 'discount_value_type', 'usage_limit', 'get_used_count',
        'start_date', 'end_date', 'get_active_status', 'get_countries_display'
    )
    list_filter = (
        'discount_value_type', 'type', 'start_date', 'end_date', 'countries'
    )
    search_fields = ('name', 'codes__code')
    readonly_fields = (
        'get_used_count',
        'get_usage_stats',
        'get_discount_value_display',
        'get_active_status',
    )

    fieldsets = (
        (None, {
            'fields': (
                'name', 'type', 'discount_value_type', 'get_discount_value_display',
                'usage_limit', 'get_used_count'
            )
        }),
        ('Availability', {
            'fields': (
                'start_date', 'end_date', 'countries', 'get_active_status'
            )
        }),
        ('Usage', {
            'fields': ('get_usage_stats',),
            'classes': ('collapse',)
        }),
    )

    # ------------------------------------------------------------------
    # ✅ Helper methods BELOW must be defined inside the class (indented)
    # ------------------------------------------------------------------

    def get_code_list(self, obj):
        codes = obj.promo_codes or []
        return ", ".join(codes[:3]) + ("..." if len(codes) > 3 else "")
    get_code_list.short_description = _("Codes")

    def get_used_count(self, obj):
        return obj.codes.aggregate(total_used=Sum('used'))['total_used'] or 0
    get_used_count.short_description = _("Times used")

    def get_usage_stats(self, obj):
        used = self.get_used_count(obj)
        if obj.usage_limit:
            return f"{used} / {obj.usage_limit}"
        return f"{used} / ∞"
    get_usage_stats.short_description = _("Usage stats")

    def get_active_status(self, obj):
        now = timezone.now()
        if obj.start_date > now:
            return format_html('<span style="color: orange;">{}</span>', _("Scheduled"))
        elif obj.end_date and obj.end_date < now:
            return format_html('<span style="color: red;">{}</span>', _("Expired"))
        else:
            return format_html('<span style="color: green;">{}</span>', _("Active"))
    get_active_status.short_description = _("Status")
    get_active_status.admin_order_field = 'start_date'

    def get_countries_display(self, obj):
        if not obj.countries:
            return "-"
        return ", ".join(str(code) for code in obj.countries)
    get_countries_display.short_description = _("Countries")

    def get_discount_value_display(self, obj):
        if not obj.channel_listings.exists():
            return "-"
        first_listing = obj.channel_listings.first()
        if obj.discount_value_type == DiscountValueType.FIXED:
            return prices_i18n.amount(first_listing.discount)
        return f"{first_listing.discount_value}%"
    get_discount_value_display.short_description = _("Discount value")


@admin.register(VoucherCustomer)
class VoucherCustomerAdmin(admin.ModelAdmin):
    list_display = ('voucher_code_link', 'customer_email', 'voucher_link', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('customer_email', 'voucher_code__code', 'voucher_code__voucher__name')
    raw_id_fields = ('voucher_code',)
    readonly_fields = ('created_at', 'voucher_link')
    
    def voucher_code_link(self, obj):
        url = reverse("admin:discount_vouchercode_change", args=(obj.voucher_code.id,))
        return format_html('<a href="{}">{}</a>', url, obj.voucher_code.code)
    voucher_code_link.short_description = _("Voucher Code")
    
    def voucher_link(self, obj):
        if obj.voucher_code.voucher:
            url = reverse("admin:discount_voucher_change", args=(obj.voucher_code.voucher.id,))
            return format_html('<a href="{}">{}</a>', url, obj.voucher_code.voucher.name)
        return "-"
    voucher_link.short_description = _("Voucher")
    
    def customer_email(self, obj):
        return obj.customer_email
    customer_email.short_description = _("Customer Email")
    
@admin.register(VoucherCode)
class VoucherCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'voucher_link', 'used', 'is_active', 'created_at'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('code', 'voucher__name')
    raw_id_fields = ('voucher',)
    readonly_fields = ('created_at',)
    
    def voucher_link(self, obj):
        url = reverse("admin:discount_voucher_change", args=(obj.voucher.id,))
        return format_html('<a href="{}">{}</a>', url, obj.voucher.name)
    voucher_link.short_description = _("Voucher")


@admin.register(PromotionRule_Variants)
class PromotionRuleVariantsAdmin(admin.ModelAdmin):
    list_display = ('promotionrule', 'productvariant')
    raw_id_fields = ('promotionrule', 'productvariant')


class PromotionRuleVariantsInline(admin.TabularInline):
    model = PromotionRule_Variants
    extra = 0
    raw_id_fields = ('productvariant',)
    verbose_name = _("Variant")
    verbose_name_plural = _("Applicable Variants")


class PromotionRuleTranslationInline(admin.TabularInline):
    model = PromotionRuleTranslation
    extra = 0
    verbose_name = _("Translation")
    verbose_name_plural = _("Translations")


@admin.register(PromotionRule)
class PromotionRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'promotion_link', 'reward_type', 'reward_value', 'catalogue_predicate'
    )
    list_filter = ('reward_type',)
    search_fields = ('name', 'promotion__name')
    raw_id_fields = ('promotion',)
    inlines = [PromotionRuleVariantsInline, PromotionRuleTranslationInline]
    readonly_fields = ('predicate_display',)
    
    def promotion_link(self, obj):
        url = reverse("admin:discount_promotion_change", args=(obj.promotion.id,))
        return format_html('<a href="{}">{}</a>', url, obj.promotion.name)
    promotion_link.short_description = _("Promotion")
    
    def predicate_display(self, obj):
        if not obj.catalogue_predicate:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.catalogue_predicate, indent=2))
    predicate_display.short_description = _("Predicate Details")


class PromotionTranslationInline(admin.TabularInline):
    model = PromotionTranslation
    extra = 0
    verbose_name = _("Translation")
    verbose_name_plural = _("Translations")


class PromotionRuleInline(admin.TabularInline):
    model = PromotionRule
    extra = 0
    fields = ('name', 'reward_type', 'reward_value', 'description')
    show_change_link = True


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'start_date', 'end_date', 'active_status', 'rules_count'
    )
    list_filter = ('start_date', 'end_date')
    search_fields = ('name', 'description')
    inlines = [PromotionRuleInline, PromotionTranslationInline]
    readonly_fields = (
        'created_at', 'updated_at', 'active_status', 'rules_count'
    )
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'active_status')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'rules_count'),
            'classes': ('collapse',)
        }),
    )
    
    def active_status(self, obj):
        now = timezone.now()
        if obj.start_date > now:
            return format_html('<span style="color: orange;">{}</span>', _("Scheduled"))
        elif obj.end_date and obj.end_date < now:
            return format_html('<span style="color: red;">{}</span>', _("Expired"))
        else:
            return format_html('<span style="color: green;">{}</span>', _("Active"))
    active_status.short_description = _("Status")
    active_status.admin_order_field = 'start_date'
    
    def rules_count(self, obj):
        return obj.rules.count()
    rules_count.short_description = _("Rules Count")
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            rules_count=Count('rules')
        )


@admin.register(OrderDiscount)
class OrderDiscountAdmin(admin.ModelAdmin):
    list_display = ('order_link', 'type', 'value_display', 'amount_display', 'reason')
    list_filter = ('type', 'value_type')
    search_fields = ('order__number', 'reason', 'voucher_code')
    raw_id_fields = ('order', 'promotion_rule')
    readonly_fields = ('created_at', 'value_display', 'amount_display')

    def order_link(self, obj):
        url = reverse("admin:order_order_change", args=(obj.order.id,))
        return format_html('<a href="{}">#{}</a>', url, obj.order.number)
    order_link.short_description = _("Order")
    
    def value_display(self, obj):
        if obj.value_type == 'fixed':
            return prices_i18n.amount(Money(obj.value, obj.currency))
        return f"{obj.value}%"
    value_display.short_description = _("Value")
    
    def amount_display(self, obj):
        return prices_i18n.amount(obj.amount)
    amount_display.short_description = _("Amount")


@admin.register(CheckoutDiscount)
class CheckoutDiscountAdmin(admin.ModelAdmin):
    list_display = ('checkout_link', 'type', 'value_display', 'amount_display')
    list_filter = ('type',)
    search_fields = ('checkout__token', 'voucher_code')
    raw_id_fields = ('checkout', 'voucher')
    readonly_fields = ('created_at', 'value_display', 'amount_display')
    
    def checkout_link(self, obj):
        url = reverse("admin:checkout_checkout_change", args=(obj.checkout.token,))
        return format_html('<a href="{}">{}</a>', url, obj.checkout.token)
    checkout_link.short_description = _("Checkout")
    
    def value_display(self, obj):
        if obj.value_type == 'fixed':
            return prices_i18n.amount(Money(obj.value, obj.currency))
        return f"{obj.value}%"
    value_display.short_description = _("Value")
    
    def amount_display(self, obj):
        return prices_i18n.amount(obj.amount)
    amount_display.short_description = _("Amount")


@admin.register(CheckoutLineDiscount)
class CheckoutLineDiscountAdmin(admin.ModelAdmin):
    list_display = ('checkout_line_link', 'type', 'value_display', 'amount_display')
    list_filter = ('type',)
    search_fields = ('line__checkout__token',)
    raw_id_fields = ('line',)
    readonly_fields = ('created_at', 'value_display', 'amount_display')
    
    def checkout_line_link(self, obj):
        url = reverse("admin:checkout_checkoutline_change", args=(obj.line.id,))
        return format_html('<a href="{}">Line #{}</a>', url, obj.line.id)
    checkout_line_link.short_description = _("Checkout Line")
    
    def value_display(self, obj):
        if obj.value_type == 'fixed':
            return prices_i18n.amount(Money(obj.value, obj.currency))
        return f"{obj.value}%"
    value_display.short_description = _("Value")
    
    def amount_display(self, obj):
        return prices_i18n.amount(obj.amount)
    amount_display.short_description = _("Amount")


@admin.register(PromotionEvent)
class PromotionEventAdmin(admin.ModelAdmin):
    list_display = ('date', 'type', 'promotion_link', 'parameters_display')
    list_filter = ('type', 'date')
    search_fields = ('promotion__name',)
    raw_id_fields = ('promotion', 'user')
    readonly_fields = ('date', 'parameters_display')
    
    def promotion_link(self, obj):
        if not obj.promotion:
            return "-"
        url = reverse("admin:discount_promotion_change", args=(obj.promotion.id,))
        return format_html('<a href="{}">{}</a>', url, obj.promotion.name)
    promotion_link.short_description = _("Promotion")
    
    def parameters_display(self, obj):
        if not obj.parameters:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.parameters, indent=2))
    parameters_display.short_description = _("Parameters")


# Register remaining models with basic configuration
admin.site.register(VoucherTranslation)
admin.site.register(VoucherChannelListing)
admin.site.register(PromotionTranslation)
admin.site.register(PromotionRuleTranslation)