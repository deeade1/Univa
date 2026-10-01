from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ecommerce.models.channel import Channel
from ecommerce.models.giftcard import GiftCard
from ecommerce.models.shipping import ShippingMethod

from ecommerce.models.checkout import Checkout, CheckoutLine, CheckoutMetadata

User = get_user_model()

class CheckoutLineInline(admin.TabularInline):
    model = CheckoutLine
    extra = 0
    raw_id_fields = ('variant',)
    readonly_fields = ('created_at', 'total_price_display', 'tax_rate_display')
    fields = ('variant', 'quantity', 'price_override', 'is_gift', 'total_price_display', 'tax_rate_display', 'created_at')
    
    def total_price_display(self, obj):
        return prices_i18n.amount(obj.total_price)
    total_price_display.short_description = "Total Price"
    
    def tax_rate_display(self, obj):
        return f"{float(obj.tax_rate) * 100:.2f}%"
    tax_rate_display.short_description = "Tax Rate"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('variant', 'variant__product')

class GiftCardInline(admin.TabularInline):
    model = Checkout.gift_cards.through
    extra = 0
    verbose_name = "Gift Card"
    verbose_name_plural = "Gift Cards"
    raw_id_fields = ('giftcard',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('giftcard')

class CheckoutMetadataInline(admin.StackedInline):
    model = CheckoutMetadata
    extra = 0
    can_delete = False
    readonly_fields = ('metadata_display',)
    
    def metadata_display(self, obj):
        if not obj.metadata:
            return "-"
        return format_html("<br>".join(f"{k}: {v}" for k, v in obj.metadata.items()))
    metadata_display.short_description = "Metadata"



@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = (
        'token',
        'user_display',
        'email',
        'channel_display',
        'created_at',
        'last_change',
        'total_display',
        'quantity_total',
        'charge_status',
        'authorize_status',
    )

    list_filter = (
        'charge_status',
        'authorize_status',
        'created_at',
        'last_change',
        'channel',
        'country',
    )

    search_fields = (
        'token',
        'user__email',
        'user__first_name',
        'user__last_name',
        'email',
    )

    raw_id_fields = ('user',)

    readonly_fields = (
        'token',
        'created_at',
        'last_change',
        'completing_started_at',
        'last_transaction_modified_at',
        'price_expiration',
        'total_display',
        'subtotal_display',
        'shipping_price_display',
        'discount_display',
        'gift_cards_balance_display',
        'payment_status',
    )

    fieldsets = (
        (None, {
            'fields': (
                'user',
                'email',
                'channel',
                'note',
                'language_code',
                'token',
            )
        }),
        ('Pricing', {
            'fields': (
                'currency',
                'total_display',
                'subtotal_display',
                'discount_display',
                'gift_cards_balance_display',
                'voucher_code',
                'tax_exemption',
                'tax_error',
            )
        }),
        ('Status', {
            'fields': (
                'charge_status',
                'authorize_status',
                'payment_status',
                'is_voucher_usage_increased',
                'automatically_refundable',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'last_change',
                'completing_started_at',
                'last_transaction_modified_at',
                'price_expiration',
            ),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': (
                'redirect_url',
                'tracking_code',
            ),
            'classes': ('collapse',)
        }),
    )

    # === Display helpers ===
    def user_display(self, obj):
        if not obj.user:
            return "-"
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_display.short_description = "User"

    def channel_display(self, obj):
        url = reverse("admin:channel_channel_change", args=(obj.channel.id,))
        return format_html('<a href="{}">{}</a>', url, obj.channel.name)
    channel_display.short_description = "Channel"

    def total_display(self, obj):
        return str(obj.total)
    total_display.short_description = "Total"

    def subtotal_display(self, obj):
        return str(obj.subtotal)
    subtotal_display.short_description = "Subtotal"

    def shipping_price_display(self, obj):
        return str(obj.shipping_price)
    shipping_price_display.short_description = "Shipping Price"

    def discount_display(self, obj):
        return str(obj.discount)
    discount_display.short_description = "Discount"

    def gift_cards_balance_display(self, obj):
        balance = obj.get_total_gift_cards_balance()
        return str(balance)
    gift_cards_balance_display.short_description = "Gift Cards Balance"

    def quantity_total(self, obj):
        return obj.lines.aggregate(total=Sum('quantity'))['total'] or 0
    quantity_total.short_description = "Items"

    def payment_status(self, obj):
        payment = obj.get_last_active_payment()
        if not payment:
            return "-"
        url = reverse("admin:payment_payment_change", args=(payment.id,))
        return format_html(
            '<a href="{}">{} ({})</a>',
            url,
            payment.get_charge_status_display(),
            payment.total
        )
    payment_status.short_description = "Last Payment"

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related(
                'user',
                'channel',
            )
            .prefetch_related('lines', 'gift_cards')
        )


class CheckoutLineAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'checkout_link',
        'variant_link',
        'quantity',
        'total_price_display',
        'tax_rate_display',
        'is_gift',
        'created_at',
    )
    list_filter = ('is_gift', 'created_at')
    search_fields = (
        'checkout__token',
        'variant__name',
        'variant__sku',
        'variant__product__name',
    )
    raw_id_fields = ('checkout', 'variant')
    readonly_fields = (
        'created_at',
        'total_price_display',
        'tax_rate_display',
        'price_override_display',
    )
    fieldsets = (
        (None, {
            'fields': (
                'checkout',
                'variant',
                'quantity',
                'is_gift',
            )
        }),
        ('Pricing', {
            'fields': (
                'price_override_display',
                'total_price_display',
                'tax_rate_display',
            )
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def checkout_link(self, obj):
        url = reverse("admin:checkout_checkout_change", args=(obj.checkout.token,))
        return format_html('<a href="{}">{}</a>', url, obj.checkout.token)
    checkout_link.short_description = "Checkout"
    
    def variant_link(self, obj):
        url = reverse("admin:product_productvariant_change", args=(obj.variant.id,))
        return format_html('<a href="{}">{} - {}</a>', url, obj.variant.sku, obj.variant.name)
    variant_link.short_description = "Variant"
    
    def total_price_display(self, obj):
        return prices_i18n.amount(obj.total_price)
    total_price_display.short_description = "Total Price"
    
    def tax_rate_display(self, obj):
        return f"{float(obj.tax_rate) * 100:.2f}%"
    tax_rate_display.short_description = "Tax Rate"
    
    def price_override_display(self, obj):
        if obj.price_override is None:
            return "-"
        return prices_i18n.amount(Money(obj.price_override, obj.currency))
    price_override_display.short_description = "Price Override"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'checkout',
            'variant',
            'variant__product',
        )

class CheckoutMetadataAdmin(admin.ModelAdmin):
    list_display = ('checkout_link', 'metadata_preview')
    search_fields = ('checkout__token',)
    raw_id_fields = ('checkout',)
    readonly_fields = ('metadata_display',)
    
    def checkout_link(self, obj):
        url = reverse("admin:checkout_checkout_change", args=(obj.checkout.token,))
        return format_html('<a href="{}">{}</a>', url, obj.checkout.token)
    checkout_link.short_description = "Checkout"
    
    def metadata_preview(self, obj):
        if not obj.metadata:
            return "-"
        preview = ", ".join(f"{k}: {v}" for k, v in list(obj.metadata.items())[:3])
        if len(obj.metadata) > 3:
            preview += "..."
        return preview
    metadata_preview.short_description = "Metadata Preview"
    
    def metadata_display(self, obj):
        if not obj.metadata:
            return "-"
        return format_html("<br>".join(f"{k}: {v}" for k, v in obj.metadata.items()))
    metadata_display.short_description = "Metadata"


admin.site.register(CheckoutLine, CheckoutLineAdmin)
admin.site.register(CheckoutMetadata, CheckoutMetadataAdmin)