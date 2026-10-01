import os
import tempfile

from django.conf import settings
from django.contrib import admin, messages
from django.core.mail import send_mail
from django.utils.html import format_html

from ecommerce.models.gotomarket import InvoiceCounter, MarketItem, Purchase, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    readonly_fields = ("line_total",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "purchase_number",
        "user",
        "created_at",
        "subtotal",
        "vat_amount",
        "discount",
        "total",
        "pdf_preview",
    )
    readonly_fields = ("purchase_number", "created_at", "receipt_preview")
    inlines = [PurchaseItemInline]
    search_fields = ("purchase_number", "user__username", "user__email")
    list_filter = ("created_at",)

    def save_model(self, request, obj, form, change):
        """Ensure totals recalc each save."""
        subtotal = sum(line.line_total for line in obj.items.all())
        obj.subtotal = subtotal
        obj.vat_amount = subtotal * obj.vat_rate
        obj.total = subtotal + obj.vat_amount - obj.discount
        super().save_model(request, obj, form, change)

    # --- PDF + HTML PREVIEWS ---
    def pdf_preview(self, obj):
        return format_html(
            "<a class='button' target='_blank' href='/admin/market/purchase/{}/pdf/'>Download PDF</a>",
            obj.pk,
        )
    pdf_preview.short_description = "Receipt PDF"

    def receipt_preview(self, obj):
        return format_html(obj.receipt_html)
    receipt_preview.short_description = "Receipt Preview"

    # --- Actions ---
    actions = ["send_receipt_email"]

    def send_receipt_email(self, request, queryset):
        """Send receipts by email to purchase users."""
        for purchase in queryset:
            if purchase.user.email:
                send_mail(
                    subject=f"Your Receipt {purchase.purchase_number}",
                    message=purchase.receipt_text,
                    html_message=purchase.receipt_html,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[purchase.user.email],
                    fail_silently=False,
                )
        self.message_user(request, "Receipts sent successfully.", messages.SUCCESS)
    send_receipt_email.short_description = "📧 Send receipt to customer"


@admin.register(MarketItem)
class MarketItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "subcategory", "price_per_unit", "stock", "is_available")
    list_filter = ("category", "subcategory")
    search_fields = ("name",)


@admin.register(InvoiceCounter)
class InvoiceCounterAdmin(admin.ModelAdmin):
    list_display = ("year", "counter")
