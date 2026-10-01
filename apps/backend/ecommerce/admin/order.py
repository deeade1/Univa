import json

from django.contrib import admin
from django.db.models import Sum
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from prices import Money

from django_prices.templatetags import prices_i18n

from ecommerce.models.constant import (FulfillmentStatus, OrderChargeStatus, OrderGrantedRefundStatus,
               OrderStatus)
from ecommerce.models.order import (Fulfillment, FulfillmentLine, Order, OrderEvent,
                     OrderGrantedRefund, OrderGrantedRefundLine, OrderLine)

#from core.utils import prices_i18n  # adjust import if needed



class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    readonly_fields = (
        'product_link', 'variant_link', 'quantity_display', 
        'unit_price_display', 'total_price_display', 'tax_rate_display'
    )
    fields = (
        'product_link', 'variant_link', 'quantity_display', 
        'unit_price_display', 'total_price_display', 'tax_rate_display'
    )
    
    def product_link(self, obj):
        if not obj.variant:
            return obj.product_name
        url = reverse("admin:product_product_change", args=(obj.variant.product.id,))
        return format_html('<a href="{}">{}</a>', url, obj.product_name)
    product_link.short_description = _("Product")
    
    def variant_link(self, obj):
        if not obj.variant:
            return obj.variant_name or "-"
        url = reverse("admin:product_productvariant_change", args=(obj.variant.id,))
        return format_html('<a href="{}">{}</a>', url, obj.variant_name or obj.variant.sku)
    variant_link.short_description = _("Variant")
    
    def quantity_display(self, obj):
        return f"{obj.quantity_fulfilled}/{obj.quantity}"
    quantity_display.short_description = _("Quantity")
    
    def unit_price_display(self, obj):
        return prices_i18n.amount(obj.unit_price)
    unit_price_display.short_description = _("Unit Price")
    
    def total_price_display(self, obj):
        return prices_i18n.amount(obj.total_price)
    total_price_display.short_description = _("Total Price")
    
    def tax_rate_display(self, obj):
        return f"{float(obj.tax_rate or 0) * 100:.2f}%" if obj.tax_rate else "-"
    tax_rate_display.short_description = _("Tax Rate")
    
    def has_add_permission(self, request, obj=None):
        return False

class FulfillmentLineInline(admin.TabularInline):
    model = FulfillmentLine
    extra = 0
    readonly_fields = ('order_line_link', 'quantity', 'stock_link')
    fields = ('order_line_link', 'quantity', 'stock_link')
    
    def order_line_link(self, obj):
        url = reverse("admin:order_orderline_change", args=(obj.order_line.id,))
        return format_html('<a href="{}">{}</a>', url, obj.order_line)
    order_line_link.short_description = _("Order Line")
    
    def stock_link(self, obj):
        if not obj.stock:
            return "-"
        url = reverse("admin:warehouse_stock_change", args=(obj.stock.id,))
        return format_html('<a href="{}">{}</a>', url, obj.stock)
    stock_link.short_description = _("Stock")
    
    def has_add_permission(self, request, obj=None):
        return False

class FulfillmentInline(admin.TabularInline):
    model = Fulfillment
    extra = 0
    readonly_fields = (
        'status_display', 'tracking_number_display', 'created_at', 
        'total_refund_amount_display', 'fulfillment_lines_link'
    )
    fields = (
        'status_display', 'tracking_number_display', 'created_at', 
        'total_refund_amount_display', 'fulfillment_lines_link'
    )
    
    def status_display(self, obj):
        status_colors = {
            FulfillmentStatus.FULFILLED: 'green',
            FulfillmentStatus.CANCELED: 'red',
            FulfillmentStatus.REFUNDED: 'orange',
            FulfillmentStatus.RETURNED: 'blue',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_display.short_description = _("Status")
    
    def tracking_number_display(self, obj):
        if not obj.tracking_number:
            return "-"
        if obj.is_tracking_number_url:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.tracking_number, _("Track"))
        return obj.tracking_number
    tracking_number_display.short_description = _("Tracking")
    
    def total_refund_amount_display(self, obj):
        if not obj.total_refund_amount:
            return "-"
        return prices_i18n.amount(Money(obj.total_refund_amount, obj.order.currency))
    total_refund_amount_display.short_description = _("Refund Amount")
    
    def fulfillment_lines_link(self, obj):
        count = obj.lines.count()
        url = reverse("admin:order_fulfillmentline_changelist") + f"?fulfillment__id__exact={obj.id}"
        return format_html('<a href="{}">{} {}</a>', url, count, _("items"))
    fulfillment_lines_link.short_description = _("Items")
    
    def has_add_permission(self, request, obj=None):
        return False

class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    readonly_fields = ('date', 'type_display', 'user_link', 'parameters_display')
    fields = ('date', 'type_display', 'user_link', 'parameters_display')
    
    def type_display(self, obj):
        return obj.get_type_display()
    type_display.short_description = _("Type")
    
    def user_link(self, obj):
        if not obj.user:
            return "-"
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _("User")
    
    def parameters_display(self, obj):
        if not obj.parameters:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.parameters, indent=2))
    parameters_display.short_description = _("Parameters")
    
    def has_add_permission(self, request, obj=None):
        return False

class OrderGrantedRefundInline(admin.TabularInline):
    model = OrderGrantedRefund
    extra = 0
    readonly_fields = (
        'created_at', 'amount_display', 'status_display', 
        'user_link', 'shipping_costs_included', 'reason'
    )
    fields = (
        'created_at', 'amount_display', 'status_display', 
        'user_link', 'shipping_costs_included', 'reason'
    )
    
    def amount_display(self, obj):
        return prices_i18n.amount(obj.amount)
    amount_display.short_description = _("Amount")
    
    def status_display(self, obj):
        status_colors = {
            OrderGrantedRefundStatus.SUCCESS: 'green',
            OrderGrantedRefundStatus.FAILURE: 'red',
            OrderGrantedRefundStatus.PENDING: 'orange',
            OrderGrantedRefundStatus.NONE: 'gray',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_display.short_description = _("Status")
    
    def user_link(self, obj):
        if not obj.user:
            return "-"
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _("User")
    
    def has_add_permission(self, request, obj=None):
        return False




@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'number',
        'customer_display',
        'status_display',
        'payment_status',
        'fulfillment_status',
        'total_display',
        'created_at',
        'channel_display',
    )
    list_filter = (
        'status',
        'channel',
        'created_at',
        'charge_status',
        'authorize_status',
    )
    search_fields = (
        'number',
        'user_email',
        'user__email',
        'billing_address__first_name',
        'billing_address__last_name',
        'shipping_address__first_name',
        'shipping_address__last_name',
    )
    raw_id_fields = (
        'user',
        'billing_address',
        'shipping_address',
        'shipping_method',
        'collection_point',
        'channel',
        'original',
        'voucher',
    )
    readonly_fields = (
        'number',
        'created_at',
        'updated_at',
        'expired_at',
        'status_display',
        'payment_status',
        'fulfillment_status',
        'total_display',
        'subtotal_display',
        'shipping_price_display',
        'discounts_display',
        'customer_link',
        'billing_address_display',
        'shipping_address_display',
        'metadata_display',
        'private_metadata_display',
        'shipping_method_name',
        'channel_display',  # ✅ make sure this stays here
    )
    inlines = [
        OrderLineInline,
        FulfillmentInline,
        OrderEventInline,
        OrderGrantedRefundInline,
    ]
    fieldsets = (
        (None, {
            'fields': (
                'status_display',
                'payment_status',
                'fulfillment_status',
                'channel_display',
            )
        }),
        ('Customer', {
            'fields': (
                'customer_link',
                'user_email',
                'language_code',
            )
        }),
        ('Addresses', {
            'fields': (
                'billing_address_display',
                'shipping_address_display',
            ),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': (
                'total_display',
                'subtotal_display',
                'shipping_price_display',
                'discounts_display',
                'currency',
            )
        }),
        ('Shipping', {
            'fields': (
                'shipping_method',
                'collection_point',
                'weight',
            ),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': (
                'created_at',
                'updated_at',
                'expired_at',
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'metadata_display',
                'private_metadata_display',
            ),
            'classes': ('collapse',)
        }),
    )
    actions = [
        'capture_payments',
        'refund_payments',
        'cancel_orders',
    ]

    # =============================
    # === Custom Display Fields ===
    # =============================

    def customer_display(self, obj):
        if obj.user:
            url = reverse("admin:accounts_user_change", args=(obj.user.id,))
            return format_html('<a href="{}">{}</a>', url, obj.user_email)
        return obj.user_email
    customer_display.short_description = _("Customer")

    def status_display(self, obj):
        status_colors = {
            OrderStatus.DRAFT: 'gray',
            OrderStatus.UNCONFIRMED: 'orange',
            OrderStatus.UNFULFILLED: 'blue',
            OrderStatus.PARTIALLY_FULFILLED: 'teal',
            OrderStatus.FULFILLED: 'green',
            OrderStatus.CANCELED: 'red',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_display.short_description = _("Status")

    def payment_status(self, obj):
        status_colors = {
            OrderChargeStatus.NONE: 'gray',
            OrderChargeStatus.PARTIAL: 'orange',
            OrderChargeStatus.FULL: 'green',
            OrderChargeStatus.OVERCHARGED: 'red',
        }
        color = status_colors.get(obj.charge_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_charge_status_display().upper()
        )
    payment_status.short_description = _("Payment")

    def fulfillment_status(self, obj):
        fulfillments = obj.fulfillments.all()
        if not fulfillments:
            return "-"
        status_counts = {}
        for f in fulfillments:
            status_counts[f.status] = status_counts.get(f.status, 0) + 1
        parts = []
        for status, count in status_counts.items():
            status_colors = {
                FulfillmentStatus.FULFILLED: 'green',
                FulfillmentStatus.CANCELED: 'red',
                FulfillmentStatus.REFUNDED: 'orange',
                FulfillmentStatus.RETURNED: 'blue',
            }
            color = status_colors.get(status, 'gray')
            label = dict(FulfillmentStatus.CHOICES).get(status, status)
            parts.append(format_html(
                '<span style="color: {};">{} ({})</span>',
                color, label, count
            ))
        return mark_safe(", ".join(parts))
    fulfillment_status.short_description = _("Fulfillment")

    def total_display(self, obj):
        return prices_i18n.amount(obj.total)
    total_display.short_description = _("Total")

    def subtotal_display(self, obj):
        return prices_i18n.amount(obj.subtotal)
    subtotal_display.short_description = _("Subtotal")

    def shipping_price_display(self, obj):
        return prices_i18n.amount(obj.shipping_price)
    shipping_price_display.short_description = _("Shipping Price")

    def discounts_display(self, obj):
        discount = obj.undiscounted_total - obj.total
        if discount.amount <= 0:
            return "-"
        return prices_i18n.amount(discount)
    discounts_display.short_description = _("Discounts")

    def channel_display(self, obj):
        if not obj.channel:
            return "-"
        url = reverse("admin:channel_channel_change", args=(obj.channel.id,))
        return format_html('<a href="{}">{}</a>', url, obj.channel.name)
    channel_display.short_description = _("Channel")

    # =============================
    # === Utility / Meta Fields ===
    # =============================

    def customer_link(self, obj):
        if not obj.user:
            return obj.user_email
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user_email)
    customer_link.short_description = _("Customer")

    def billing_address_display(self, obj):
        if not obj.billing_address:
            return "-"
        return format_html(
            "{}<br>{}<br>{} {}<br>{}",
            f"{obj.billing_address.first_name} {obj.billing_address.last_name}",
            obj.billing_address.street_address_1,
            obj.billing_address.postal_code,
            obj.billing_address.city,
            obj.billing_address.country.name
        )
    billing_address_display.short_description = _("Billing Address")

    def shipping_address_display(self, obj):
        if not obj.shipping_address:
            return "-"
        return format_html(
            "{}<br>{}<br>{} {}<br>{}",
            f"{obj.shipping_address.first_name} {obj.shipping_address.last_name}",
            obj.shipping_address.street_address_1,
            obj.shipping_address.postal_code,
            obj.shipping_address.city,
            obj.shipping_address.country.name
        )
    shipping_address_display.short_description = _("Shipping Address")

    def metadata_display(self, obj):
        if not obj.metadata:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.metadata, indent=2))
    metadata_display.short_description = _("Metadata")

    def private_metadata_display(self, obj):
        if not obj.private_metadata:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.private_metadata, indent=2))
    private_metadata_display.short_description = _("Private Metadata")

    # =============================
    # === Admin Actions ===
    # =============================

    def capture_payments(self, request, queryset):
        count = queryset.count()
        self.message_user(request, _("Queued {} orders for payment capture.").format(count))
    capture_payments.short_description = _("Capture payments for selected orders")

    def refund_payments(self, request, queryset):
        count = queryset.count()
        self.message_user(request, _("Queued {} orders for refund.").format(count))
    refund_payments.short_description = _("Refund payments for selected orders")

    def cancel_orders(self, request, queryset):
        count = queryset.count()
        self.message_user(request, _("Queued {} orders for cancellation.").format(count))
    cancel_orders.short_description = _("Cancel selected orders")

    # =============================
    # === Query Optimization ===
    # =============================

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user',
            'billing_address',
            'shipping_address',
            'channel',
            'shipping_method',
            'collection_point',
            'voucher',
        ).prefetch_related('fulfillments')



@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = (
        'product_display',
        'variant_display',
        'order_link',
        'quantity_display',
        'unit_price_display',
        'total_price_display',
        'tax_rate_display',
    )
    list_filter = ('is_shipping_required', 'is_gift_card', 'created_at')
    search_fields = ('order__number', 'product_name', 'variant_name', 'product_sku')
    raw_id_fields = ('order', 'variant')
    readonly_fields = (
        'created_at',
        'product_display',
        'variant_display',
        'order_link',
        'quantity_display',
        'unit_price_display',
        'total_price_display',
        'tax_rate_display',
        'discounts_display',
        'metadata_display',
    )

    # --- FIXED: add missing display methods ---

    def product_display(self, obj):
        if obj.variant and obj.variant.product_id:
            url = reverse("admin:product_product_change", args=[obj.variant.product_id])
            return format_html('<a href="{}">{}</a>', url, obj.product_name)
        return obj.product_name
    product_display.short_description = _("Product")

    def variant_display(self, obj):
        if not obj.variant:
            return obj.variant_name or "-"
        url = reverse("admin:product_productvariant_change", args=[obj.variant.id])
        return format_html('<a href="{}">{}</a>', url, obj.variant_name or obj.variant.sku)
    variant_display.short_description = _("Variant")

    def order_link(self, obj):
        if not obj.order:
            return "-"
        url = reverse("admin:order_order_change", args=[obj.order.id])
        return format_html('<a href="{}">#{}</a>', url, obj.order.number)
    order_link.short_description = _("Order")

    def quantity_display(self, obj):
        return f"{obj.quantity_fulfilled}/{obj.quantity}"
    quantity_display.short_description = _("Quantity")

    def unit_price_display(self, obj):
        return prices_i18n.amount(obj.unit_price)
    unit_price_display.short_description = _("Unit Price")

    def total_price_display(self, obj):
        return prices_i18n.amount(obj.total_price)
    total_price_display.short_description = _("Total Price")

    def tax_rate_display(self, obj):
        return f"{float(obj.tax_rate or 0) * 100:.2f}%" if obj.tax_rate else "-"
    tax_rate_display.short_description = _("Tax Rate")

    # --- your safe discount display ---
    def discounts_display(self, obj):
        """Safely show total discount amount."""
        undiscounted = getattr(obj, "undiscounted_total_price", None)
        total = getattr(obj, "total_price", None)

        if not undiscounted or not total:
            return "-"

        try:
            discount = undiscounted - total
            if discount.amount <= 0:
                return "-"
            return prices_i18n.amount(discount)
        except Exception:
            return "-"
    discounts_display.short_description = _("Discounts")

    def metadata_display(self, obj):
        if not obj.metadata:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.metadata, indent=2))
    metadata_display.short_description = _("Metadata")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'variant', 'variant__product'
        )


@admin.register(Fulfillment)
class FulfillmentAdmin(admin.ModelAdmin):
    list_display = (
        'order_link',
        'status_display',
        'tracking_number_display',
        'created_at',
        'total_refund_amount_display',
    )
    list_filter = (
        'status',
        'created_at',
    )
    search_fields = (
        'order__number',
        'tracking_number',
    )
    raw_id_fields = (
        'order',
    )
    readonly_fields = (
        'created_at',
        'status_display',
        'order_link',
        'tracking_number_display',
        'total_refund_amount_display',
        'fulfillment_lines_link',
        'metadata_display',
    )
    inlines = [FulfillmentLineInline]
    
    def order_link(self, obj):
        url = reverse("admin:order_order_change", args=(obj.order.id,))
        return format_html('<a href="{}">#{}</a>', url, obj.order.number)
    order_link.short_description = _("Order")
    
    def status_display(self, obj):
        status_colors = {
            FulfillmentStatus.FULFILLED: 'green',
            FulfillmentStatus.CANCELED: 'red',
            FulfillmentStatus.REFUNDED: 'orange',
            FulfillmentStatus.RETURNED: 'blue',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_display.short_description = _("Status")
    
    def tracking_number_display(self, obj):
        if not obj.tracking_number:
            return "-"
        if obj.is_tracking_number_url:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.tracking_number, _("Track"))
        return obj.tracking_number
    tracking_number_display.short_description = _("Tracking")
    
    def total_refund_amount_display(self, obj):
        if not obj.total_refund_amount:
            return "-"
        return prices_i18n.amount(Money(obj.total_refund_amount, obj.order.currency))
    total_refund_amount_display.short_description = _("Refund Amount")
    
    def fulfillment_lines_link(self, obj):
        count = obj.lines.count()
        url = reverse("admin:order_fulfillmentline_changelist") + f"?fulfillment__id__exact={obj.id}"
        return format_html('<a href="{}">{} {}</a>', url, count, _("items"))
    fulfillment_lines_link.short_description = _("Items")
    
    def metadata_display(self, obj):
        if not obj.metadata:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.metadata, indent=2))
    metadata_display.short_description = _("Metadata")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order')

@admin.register(FulfillmentLine)
class FulfillmentLineAdmin(admin.ModelAdmin):
    list_display = (
        'order_line_link',
        'fulfillment_link',
        'quantity',
        'stock_link',
    )
    list_filter = ('quantity',)
    search_fields = (
        'order_line__product_name',
        'order_line__variant_name',
        'order_line__product_sku',
    )
    raw_id_fields = (
        'order_line',
        'fulfillment',
        'stock',
    )
    readonly_fields = (
        'order_line_link',
        'fulfillment_link',
        'stock_link',
    )
    
    def order_line_link(self, obj):
        url = reverse("admin:order_orderline_change", args=(obj.order_line.id,))
        return format_html('<a href="{}">{}</a>', url, obj.order_line)
    order_line_link.short_description = _("Order Line")
    
    def fulfillment_link(self, obj):
        url = reverse("admin:order_fulfillment_change", args=(obj.fulfillment.id,))
        return format_html('<a href="{}">#{}</a>', url, obj.fulfillment.order.number)
    fulfillment_link.short_description = _("Fulfillment")
    
    def stock_link(self, obj):
        if not obj.stock:
            return "-"
        url = reverse("admin:warehouse_stock_change", args=(obj.stock.id,))
        return format_html('<a href="{}">{}</a>', url, obj.stock)
    stock_link.short_description = _("Stock")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order_line',
            'fulfillment',
            'fulfillment__order',
            'stock',
        )

@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'order_link',
        'type_display',
        'user_link',
        'parameters_preview',
    )
    list_filter = (
        'type',
        'date',
    )
    search_fields = (
        'order__number',
        'user__email',
    )
    raw_id_fields = (
        'order',
        'user',
        'related',
    )
    readonly_fields = (
        'date',
        'type_display',
        'order_link',
        'user_link',
        'related_link',
        'parameters_display',
    )
    
    def order_link(self, obj):
        url = reverse("admin:order_order_change", args=(obj.order.id,))
        return format_html('<a href="{}">#{}</a>', url, obj.order.number)
    order_link.short_description = _("Order")
    
    def type_display(self, obj):
        return obj.get_type_display()
    type_display.short_description = _("Type")
    
    def user_link(self, obj):
        if not obj.user:
            return "-"
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _("User")
    
    def related_link(self, obj):
        if not obj.related:
            return "-"
        url = reverse("admin:order_orderevent_change", args=(obj.related.id,))
        return format_html('<a href="{}">{}</a>', url, obj.related.type)
    related_link.short_description = _("Related Event")
    
    def parameters_preview(self, obj):
        if not obj.parameters:
            return "-"
        preview = ", ".join(f"{k}: {v}" for k, v in list(obj.parameters.items())[:3])
        if len(obj.parameters) > 3:
            preview += "..."
        return preview
    parameters_preview.short_description = _("Parameters")
    
    def parameters_display(self, obj):
        if not obj.parameters:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.parameters, indent=2))
    parameters_display.short_description = _("Parameters Details")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order',
            'user',
            'related',
        )

@admin.register(OrderGrantedRefund)
class OrderGrantedRefundAdmin(admin.ModelAdmin):
    list_display = (
        'order_link',
        'amount_display',
        'status_display',
        'created_at',
        'user_link',
    )
    list_filter = (
        'status',
        'created_at',
    )
    search_fields = (
        'order__number',
        'user__email',
    )
    raw_id_fields = (
        'order',
        'user',
        'transaction_item',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
        'order_link',
        'amount_display',
        'status_display',
        'user_link',
        'transaction_item_link',
        'reason',
        'shipping_costs_included',
        'metadata_display',
    )
    inlines = []
    
    def order_link(self, obj):
        url = reverse("admin:order_order_change", args=(obj.order.id,))
        return format_html('<a href="{}">#{}</a>', url, obj.order.number)
    order_link.short_description = _("Order")
    
    def amount_display(self, obj):
        return prices_i18n.amount(obj.amount)
    amount_display.short_description = _("Amount")
    
    def status_display(self, obj):
        status_colors = {
            OrderGrantedRefundStatus.SUCCESS: 'green',
            OrderGrantedRefundStatus.FAILURE: 'red',
            OrderGrantedRefundStatus.PENDING: 'orange',
            OrderGrantedRefundStatus.NONE: 'gray',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_display.short_description = _("Status")
    
    def user_link(self, obj):
        if not obj.user:
            return "-"
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _("User")
    
    def transaction_item_link(self, obj):
        if not obj.transaction_item:
            return "-"
        url = reverse("admin:payment_transactionitem_change", args=(obj.transaction_item.id,))
        return format_html('<a href="{}">{}</a>', url, obj.transaction_item)
    transaction_item_link.short_description = _("Transaction")
    
    def metadata_display(self, obj):
        if not obj.metadata:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.metadata, indent=2))
    metadata_display.short_description = _("Metadata")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order',
            'user',
            'transaction_item',
        )

@admin.register(OrderGrantedRefundLine)
class OrderGrantedRefundLineAdmin(admin.ModelAdmin):
    list_display = (
        'order_line_link',
        'granted_refund_link',
        'quantity',
        'reason_short',
    )
    list_filter = ('quantity',)
    search_fields = (
        'order_line__product_name',
        'order_line__variant_name',
        'order_line__product_sku',
        'granted_refund__order__number',
    )
    raw_id_fields = (
        'order_line',
        'granted_refund',
    )
    readonly_fields = (
        'order_line_link',
        'granted_refund_link',
        'reason_display',
    )
    
    def order_line_link(self, obj):
        url = reverse("admin:order_orderline_change", args=(obj.order_line.id,))
        return format_html('<a href="{}">{}</a>', url, obj.order_line)
    order_line_link.short_description = _("Order Line")
    
    def granted_refund_link(self, obj):
        url = reverse("admin:order_ordergrantedrefund_change", args=(obj.granted_refund.id,))
        return format_html('<a href="{}">#{}</a>', url, obj.granted_refund.order.number)
    granted_refund_link.short_description = _("Granted Refund")
    
    def reason_short(self, obj):
        return obj.reason[:50] + "..." if obj.reason and len(obj.reason) > 50 else obj.reason or "-"
    reason_short.short_description = _("Reason")
    
    def reason_display(self, obj):
        return obj.reason or "-"
    reason_display.short_description = _("Reason")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order_line',
            'granted_refund',
            'granted_refund__order',
        )