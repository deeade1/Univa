# apps/backend/invoice/admin.py
import json

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from core import JobStatus

from .models import Invoice, InvoiceLineItem, InvoicePayment


class InvoiceLineItemInline(admin.TabularInline):
    """Inline admin for invoice line items."""
    model = InvoiceLineItem
    extra = 0
    fields = (
        'description',
        'sku',
        'quantity',
        'unit_price',
        'discount',
        'tax',
        'tax_rate',
        'total',
    )
    readonly_fields = ('total',)
    ordering = ('id',)
    show_change_link = True


class InvoicePaymentInline(admin.TabularInline):
    """Inline admin for invoice payments."""
    model = InvoicePayment
    extra = 0
    fields = (
        'amount',
        'payment_method',
        'payment_reference',
        'status',
        'payment_date',
        'transaction_id',
    )
    readonly_fields = ('payment_date',)
    ordering = ('-payment_date',)
    show_change_link = True


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin interface for Invoice model."""
    
    list_display = (
        'number',
        'customer_link',
        'order_link',
        'booking_link',
        'total_amount',
        'status_badge',
        'payment_status',
        'issue_date',
        'due_date',
        'created_at',
        'download_link',
    )
    
    list_filter = (
        'status',
        'issue_date',
        'due_date',
        'currency',
        ('created_at', admin.DateFieldListFilter),
        'created_by',
    )
    
    search_fields = (
        'number',
        'invoice_number',
        'customer__email',
        'customer__first_name',
        'customer__last_name',
        'billing_email',
        'billing_name',
        'payment_reference',
    )
    
    raw_id_fields = ('customer', 'order', 'booking', 'created_by', 'sent_by', 'verified_by')
    
    readonly_fields = (
        'created_at',
        'updated_at',
        'sent_at',
        'balance_due',
        'status_badge',
        'payment_status',
        'url_link',
        'file_preview',
        'metadata_display',
        'events_link',
    )
    
    inlines = [InvoiceLineItemInline, InvoicePaymentInline]
    
    fieldsets = (
        ('Invoice Information', {
            'fields': (
                ('number', 'invoice_number'),
                ('status_badge', 'payment_status'),
                ('customer', 'order', 'booking'),
                ('issue_date', 'due_date'),
                ('payment_terms', 'currency'),
            )
        }),
        ('Billing Information', {
            'fields': (
                'billing_name',
                'billing_email',
                'billing_phone',
                ('billing_address', 'billing_city'),
                ('billing_state', 'billing_country'),
                'billing_zip',
            ),
            'classes': ('collapse',)
        }),
        ('Financial Details', {
            'fields': (
                ('subtotal', 'tax_amount'),
                ('discount_amount', 'shipping_amount'),
                ('total_amount', 'amount_paid'),
                'balance_due',
            )
        }),
        ('Payment Information', {
            'fields': (
                'payment_method',
                'payment_reference',
                'payment_date',
            ),
            'classes': ('collapse',)
        }),
        ('Files & URLs', {
            'fields': (
                'invoice_file',
                'file_preview',
                'external_url',
                'url_link',
            ),
            'classes': ('collapse',)
        }),
        ('Audit & Metadata', {
            'fields': (
                ('created_by', 'sent_by', 'verified_by'),
                ('created_at', 'updated_at', 'sent_at'),
                'metadata_display',
                'events_link',
            ),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes', 'terms_and_conditions'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['regenerate_invoices', 'mark_as_sent', 'mark_as_paid', 'mark_as_overdue']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related."""
        return super().get_queryset(request).select_related(
            'customer',
            'order',
            'booking',
            'created_by',
            'sent_by',
            'verified_by',
        ).prefetch_related(
            'line_items',
            'payments',
        )
    
    # =========================================================================
    # List Display Methods
    # =========================================================================
    
    def customer_link(self, obj):
        """Display customer with link to user admin."""
        if not obj.customer:
            return "-"
        url = reverse("admin:accounts_user_change", args=(obj.customer.id,))
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.customer.email or str(obj.customer)
        )
    customer_link.short_description = _("Customer")
    customer_link.admin_order_field = 'customer__email'
    
    def order_link(self, obj):
        """Display order with link to order admin."""
        if not obj.order:
            return "-"
        if hasattr(obj.order, 'number'):
            display = f"#{obj.order.number}"
        else:
            display = f"Order {obj.order.id}"
        url = reverse("admin:ecommerce_order_change", args=(obj.order.id,))
        return format_html('<a href="{}">{}</a>', url, display)
    order_link.short_description = _("Order")
    order_link.admin_order_field = 'order__number'
    
    def booking_link(self, obj):
        """Display booking with link to booking admin."""
        if not obj.booking:
            return "-"
        url = reverse("admin:transport_booking_change", args=(obj.booking.id,))
        return format_html(
            '<a href="{}">Booking #{}</a>',
            url,
            obj.booking.id
        )
    booking_link.short_description = _("Booking")
    
    def status_badge(self, obj):
        """Display status with color badge."""
        status_colors = {
            'DRAFT': 'gray',
            'SENT': 'blue',
            'PAID': 'green',
            'OVERDUE': 'red',
            'CANCELLED': 'orange',
            'REFUNDED': 'purple',
            'VOID': 'dark',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="display: inline-block; padding: 2px 8px; '
            'background-color: {}; color: white; border-radius: 3px; '
            'font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_badge.short_description = _("Status")
    status_badge.admin_order_field = 'status'
    
    def payment_status(self, obj):
        """Display payment status."""
        if obj.balance_due <= 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Fully Paid</span>'
            )
        elif obj.amount_paid > 0:
            return format_html(
                '<span style="color: orange; font-weight: bold;">Partially Paid</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">Unpaid</span>'
            )
    payment_status.short_description = _("Payment Status")
    
    def download_link(self, obj):
        """Display download link for invoice file."""
        if not obj.invoice_file:
            return "-"
        return format_html(
            '<a href="{}" download style="font-size: 18px;">📄</a>',
            obj.invoice_file.url
        )
    download_link.short_description = _("Download")
    
    def url_link(self, obj):
        """Display URL link."""
        if not obj.url:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" style="font-size: 18px;">🔗</a>',
            obj.url
        )
    url_link.short_description = _("URL")
    
    def file_preview(self, obj):
        """Display file preview."""
        if not obj.invoice_file:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" style="font-size: 18px;">📄 View PDF</a>',
            obj.invoice_file.url
        )
    file_preview.short_description = _("File Preview")
    
    def events_link(self, obj):
        """Display link to events."""
        try:
            count = obj.events.count()
            url = reverse("admin:invoice_invoiceevent_changelist") + f"?invoice__id__exact={obj.id}"
            return format_html('<a href="{}">{} {}</a>', url, count, _("events"))
        except (AttributeError, Exception):
            return "-"
    events_link.short_description = _("Events")
    
    def metadata_display(self, obj):
        """Display metadata as formatted JSON."""
        if not obj.metadata:
            return "-"
        return format_html(
            "<pre style='background: #f5f5f5; padding: 10px; border-radius: 4px;'>{}</pre>",
            json.dumps(obj.metadata, indent=2, default=str)
        )
    metadata_display.short_description = _("Metadata")
    
    # =========================================================================
    # Admin Actions
    # =========================================================================
    
    def regenerate_invoices(self, request, queryset):
        """Regenerate selected invoices."""
        count = 0
        for invoice in queryset:
            # Add your invoice regeneration logic here
            # This could regenerate PDF, update totals, etc.
            count += 1
        self.message_user(
            request,
            _("Successfully regenerated {} invoice(s).").format(count)
        )
    regenerate_invoices.short_description = _("Regenerate selected invoices")
    
    def mark_as_sent(self, request, queryset):
        """Mark selected invoices as sent."""
        count = 0
        for invoice in queryset:
            if invoice.status == 'DRAFT':
                invoice.mark_as_sent(sent_by=request.user)
                count += 1
        self.message_user(
            request,
            _("Successfully marked {} invoice(s) as sent.").format(count)
        )
    mark_as_sent.short_description = _("Mark selected as sent")
    
    def mark_as_paid(self, request, queryset):
        """Mark selected invoices as paid."""
        count = 0
        for invoice in queryset:
            if invoice.status in ['SENT', 'OVERDUE']:
                invoice.mark_as_paid(verified_by=request.user)
                count += 1
        self.message_user(
            request,
            _("Successfully marked {} invoice(s) as paid.").format(count)
        )
    mark_as_paid.short_description = _("Mark selected as paid")
    
    def mark_as_overdue(self, request, queryset):
        """Mark selected invoices as overdue."""
        count = 0
        for invoice in queryset:
            if invoice.status == 'SENT':
                invoice.mark_as_overdue()
                count += 1
        self.message_user(
            request,
            _("Successfully marked {} invoice(s) as overdue.").format(count)
        )
    mark_as_overdue.short_description = _("Mark selected as overdue")


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    """Admin interface for InvoiceLineItem model."""
    
    list_display = (
        'id',
        'invoice_link',
        'description',
        'quantity',
        'unit_price',
        'total',
        'created_at',
    )
    
    list_filter = (
        'created_at',
        ('invoice', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'description',
        'sku',
        'invoice__number',
        'invoice__invoice_number',
    )
    
    raw_id_fields = ('invoice',)
    
    readonly_fields = ('total', 'created_at', 'updated_at')
    
    def invoice_link(self, obj):
        """Display invoice with link."""
        url = reverse("admin:invoice_invoice_change", args=(obj.invoice.id,))
        number = obj.invoice.number or obj.invoice.invoice_number or f"INV-{obj.invoice.id}"
        return format_html('<a href="{}">{}</a>', url, number)
    invoice_link.short_description = _("Invoice")
    
    fieldsets = (
        ('Line Item Information', {
            'fields': (
                'invoice',
                'description',
                'sku',
                'quantity',
                'unit_price',
            )
        }),
        ('Tax & Discount', {
            'fields': (
                'discount',
                'tax',
                'tax_rate',
                'total',
            )
        }),
        ('Audit', {
            'fields': (
                'created_at',
                'updated_at',
                'metadata',
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    """Admin interface for InvoicePayment model."""
    
    list_display = (
        'id',
        'invoice_link',
        'amount',
        'payment_method',
        'payment_reference',
        'status_badge',
        'payment_date',
        'transaction_id',
    )
    
    list_filter = (
        'status',
        'payment_method',
        'payment_date',
        ('invoice', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'payment_reference',
        'transaction_id',
        'invoice__number',
        'invoice__invoice_number',
        'invoice__customer__email',
    )
    
    raw_id_fields = ('invoice', 'created_by', 'verified_by')
    
    readonly_fields = ('payment_date', 'created_at', 'updated_at')
    
    actions = ['mark_as_completed', 'mark_as_failed', 'mark_as_refunded']
    
    def invoice_link(self, obj):
        """Display invoice with link."""
        url = reverse("admin:invoice_invoice_change", args=(obj.invoice.id,))
        number = obj.invoice.number or obj.invoice.invoice_number or f"INV-{obj.invoice.id}"
        return format_html('<a href="{}">{}</a>', url, number)
    invoice_link.short_description = _("Invoice")
    
    def status_badge(self, obj):
        """Display status with color badge."""
        status_colors = {
            'PENDING': 'orange',
            'PROCESSING': 'blue',
            'COMPLETED': 'green',
            'FAILED': 'red',
            'REFUNDED': 'purple',
            'PARTIAL': 'gold',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="display: inline-block; padding: 2px 8px; '
            'background-color: {}; color: white; border-radius: 3px; '
            'font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_badge.short_description = _("Status")
    status_badge.admin_order_field = 'status'
    
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'invoice',
                'amount',
                'payment_method',
                'payment_reference',
                'status_badge',
            )
        }),
        ('Transaction Details', {
            'fields': (
                'transaction_id',
                'gateway_response',
                'metadata',
            ),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': (
                ('created_by', 'verified_by'),
                ('payment_date', 'created_at', 'updated_at'),
            ),
            'classes': ('collapse',)
        }),
    )
    
    def mark_as_completed(self, request, queryset):
        """Mark selected payments as completed."""
        count = 0
        for payment in queryset:
            if payment.status != 'COMPLETED':
                payment.mark_as_completed(verified_by=request.user)
                count += 1
        self.message_user(
            request,
            _("Successfully marked {} payment(s) as completed.").format(count)
        )
    mark_as_completed.short_description = _("Mark selected as completed")
    
    def mark_as_failed(self, request, queryset):
        """Mark selected payments as failed."""
        count = 0
        for payment in queryset:
            if payment.status != 'FAILED':
                payment.mark_as_failed()
                count += 1
        self.message_user(
            request,
            _("Successfully marked {} payment(s) as failed.").format(count)
        )
    mark_as_failed.short_description = _("Mark selected as failed")
    
    def mark_as_refunded(self, request, queryset):
        """Mark selected payments as refunded."""
        count = 0
        for payment in queryset:
            if payment.status == 'COMPLETED':
                payment.mark_as_refunded()
                count += 1
        self.message_user(
            request,
            _("Successfully marked {} payment(s) as refunded.").format(count)
        )
    mark_as_refunded.short_description = _("Mark selected as refunded")