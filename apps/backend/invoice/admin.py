# apps/backend/invoice/admin.py

import json

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .enums import (
    InvoiceEventType,
    InvoicePaymentType,
    InvoiceShareChannel,
    InvoiceStatus,
)
from .models import (
    Invoice,
    InvoiceEvent,
    InvoiceLineItem,
    InvoiceParty,
    InvoicePayment,
    InvoiceShare,
    InvoiceSource,
)


# =====================================================================
# INVOICE PARTY
# =====================================================================


@admin.register(InvoiceParty)
class InvoicePartyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_organization",
        "tax_id",
        "email",
        "user_link",
        "is_active",
    )
    list_filter = (
        "is_organization",
        "is_active",
    )
    search_fields = (
        "name",
        "tax_id",
        "email",
        "user__email",
    )
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "name",
                    "is_organization",
                    "tax_id",
                    "user",
                    "is_active",
                )
            },
        ),
        (
            "Contact",
            {
                "fields": (
                    "email",
                    "phone",
                )
            },
        ),
        (
            "Billing address",
            {
                "fields": (
                    "billing_address",
                    ("billing_city", "billing_state"),
                    ("billing_country", "billing_zip"),
                )
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def user_link(self, obj):
        if not obj.user_id:
            return "-"
        url = reverse("admin:accounts_user_change", args=(obj.user_id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _("User")
    user_link.admin_order_field = "user__email"


# =====================================================================
# INLINE ADMINS
# =====================================================================


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    fields = (
        "description",
        "quantity",
        "unit_price",
        "discount_amount",
        "tax_rate",
        "tax_amount",
        "line_total",
        "currency",
    )
    readonly_fields = ("line_total",)
    ordering = ("pk",)
    show_change_link = True


class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 0
    fields = (
        "idempotency_key",
        "payment_type",
        "payment_id",
        "amount",
        "currency",
        "applied_at",
        "applied_by",
    )
    readonly_fields = (
        "idempotency_key",
        "payment_type",
        "payment_id",
        "amount",
        "currency",
        "applied_at",
        "applied_by",
    )
    ordering = ("-applied_at",)
    can_delete = False
    show_change_link = True


class InvoiceSourceInline(admin.TabularInline):
    model = InvoiceSource
    extra = 0
    fields = (
        "source_type",
        "source_id",
        "source_reference",
    )
    readonly_fields = (
        "source_type",
        "source_id",
        "source_reference",
    )
    ordering = ("source_type", "source_id")
    can_delete = False
    show_change_link = True


class InvoiceShareInline(admin.TabularInline):
    model = InvoiceShare
    extra = 0
    fields = (
        "token_short",
        "label",
        "channel",
        "expires_at",
        "is_active_display",
        "view_count",
    )
    readonly_fields = (
        "token_short",
        "label",
        "channel",
        "expires_at",
        "is_active_display",
        "view_count",
    )
    ordering = ("-created_at",)
    can_delete = False
    show_change_link = True

    def token_short(self, obj):
        return f"{obj.token[:12]}…" if obj.token else "-"
    token_short.short_description = _("Token")

    def is_active_display(self, obj):
        if obj.is_revoked:
            return format_html(
                '<span style="color: gray;">{}</span>',
                _("Revoked"),
            )
        if obj.is_expired:
            return format_html(
                '<span style="color: red;">{}</span>',
                _("Expired"),
            )
        return format_html(
            '<span style="color: green;">{}</span>',
            _("Active"),
        )
    is_active_display.short_description = _("State")


# =====================================================================
# INVOICE
# =====================================================================


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "recipient_link",
        "issuer_link",
        "total_amount",
        "currency",
        "status_badge",
        "payment_status",
        "issue_date",
        "due_date",
        "rendered_link",
    )

    list_filter = (
        "status",
        "currency",
        "issue_date",
        "due_date",
        "issuer",
    )

    search_fields = (
        "number",
        "recipient__name",
        "recipient__email",
        "issuer__name",
        "sources__source_reference",
        "sources__source_id",
    )

    raw_id_fields = (
        "issuer",
        "recipient",
    )

    readonly_fields = (
        "id",
        "number",
        "subtotal_amount",
        "tax_amount",
        "total_amount",
        "amount_paid",
        "balance_due",
        "rendered_at",
        "status_badge",
        "payment_status",
        "created_at",
        "updated_at",
        "rendered_preview",
        "events_link",
        "shares_link",
        "metadata_display",
    )

    inlines = [
        InvoiceLineItemInline,
        InvoicePaymentInline,
        InvoiceSourceInline,
        InvoiceShareInline,
    ]

    fieldsets = (
        (
            _("Identity"),
            {
                "fields": (
                    "id",
                    "number",
                    ("status_badge", "payment_status"),
                    ("issue_date", "due_date", "payment_terms"),
                    "currency",
                )
            },
        ),
        (
            _("Parties"),
            {
                "fields": (
                    "issuer",
                    "recipient",
                )
            },
        ),
        (
            _("Amounts"),
            {
                "fields": (
                    ("subtotal_amount", "tax_amount"),
                    ("discount_amount", "shipping_amount"),
                    ("total_amount", "amount_paid"),
                    "balance_due",
                )
            },
        ),
        (
            _("Presentation"),
            {
                "fields": (
                    "notes",
                    "terms_and_conditions",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Rendering"),
            {
                "fields": (
                    "rendered_file",
                    "rendered_at",
                    "rendered_preview",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit"),
            {
                "fields": (
                    ("created_at", "updated_at"),
                    "events_link",
                    "shares_link",
                    "metadata_display",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = [
        "action_mark_issued",
        "action_mark_sent",
        "action_mark_overdue",
        "action_render_pdf",
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("issuer", "recipient")
            .prefetch_related(
                "line_items",
                "payments",
                "sources",
                "shares",
                "events",
            )
        )

    # ------------------------------------------------------------------
    # List display
    # ------------------------------------------------------------------

    def recipient_link(self, obj):
        url = reverse(
            "admin:invoice_invoiceparty_change",
            args=(obj.recipient_id,),
        )
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.recipient.name,
        )
    recipient_link.short_description = _("Recipient")
    recipient_link.admin_order_field = "recipient__name"

    def issuer_link(self, obj):
        url = reverse(
            "admin:invoice_invoiceparty_change",
            args=(obj.issuer_id,),
        )
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.issuer.name,
        )
    issuer_link.short_description = _("Issuer")
    issuer_link.admin_order_field = "issuer__name"

    def status_badge(self, obj):
        status_colors = {
            InvoiceStatus.DRAFT: "#6c757d",
            InvoiceStatus.ISSUED: "#0d6efd",
            InvoiceStatus.SENT: "#17a2b8",
            InvoiceStatus.PAID: "#28a745",
            InvoiceStatus.PARTIALLY_PAID: "#fd7e14",
            InvoiceStatus.OVERDUE: "#dc3545",
            InvoiceStatus.CANCELLED: "#6f42c1",
            InvoiceStatus.REFUNDED: "#6f42c1",
            InvoiceStatus.VOID: "#343a40",
        }
        color = status_colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="display: inline-block; padding: 2px 8px; '
            'background-color: {}; color: white; border-radius: 3px; '
            'font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper(),
        )
    status_badge.short_description = _("Status")
    status_badge.admin_order_field = "status"

    def payment_status(self, obj):
        if obj.balance_due <= 0 and obj.amount_paid > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">'
                '✓ {}</span>',
                _("Paid"),
            )
        if obj.amount_paid > 0:
            return format_html(
                '<span style="color: #fd7e14; font-weight: bold;">'
                '{}</span>',
                _("Partial"),
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">'
            '{}</span>',
            _("Unpaid"),
        )
    payment_status.short_description = _("Payment")

    def rendered_link(self, obj):
        if not obj.rendered_file:
            return "-"
        return format_html(
            '<a href="{}" target="_blank">📄</a>',
            obj.rendered_file.url,
        )
    rendered_link.short_description = _("PDF")

    def rendered_preview(self, obj):
        if not obj.rendered_file:
            return "-"
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            obj.rendered_file.url,
            _("Open PDF"),
        )
    rendered_preview.short_description = _("Preview")

    def events_link(self, obj):
        url = (
            reverse("admin:invoice_invoiceevent_changelist")
            + f"?invoice__id__exact={obj.id}"
        )
        return format_html(
            '<a href="{}">{} ({})</a>',
            url,
            _("View events"),
            obj.events.count(),
        )
    events_link.short_description = _("Events")

    def shares_link(self, obj):
        url = (
            reverse("admin:invoice_invoiceshare_changelist")
            + f"?invoice__id__exact={obj.id}"
        )
        return format_html(
            '<a href="{}">{} ({})</a>',
            url,
            _("View shares"),
            obj.shares.count(),
        )
    shares_link.short_description = _("Shares")

    def metadata_display(self, obj):
        if not obj.metadata:
            return "-"
        return format_html(
            "<pre style='background: #f5f5f5; padding: 10px; "
            "border-radius: 4px;'>{}</pre>",
            json.dumps(obj.metadata, indent=2, default=str),
        )
    metadata_display.short_description = _("Metadata")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_mark_issued(self, request, queryset):
        from .services import mark_issued

        ok, skipped = 0, 0
        for invoice in queryset:
            try:
                mark_issued(invoice, actor=request.user)
                ok += 1
            except Exception:
                skipped += 1

        self.message_user(
            request,
            _("Issued {ok} invoice(s); {skipped} skipped.").format(
                ok=ok, skipped=skipped
            ),
        )
    action_mark_issued.short_description = _("Mark selected as issued")

    def action_mark_sent(self, request, queryset):
        from .services import mark_sent

        ok, skipped = 0, 0
        for invoice in queryset:
            try:
                mark_sent(invoice, actor=request.user)
                ok += 1
            except Exception:
                skipped += 1

        self.message_user(
            request,
            _("Marked {ok} invoice(s) as sent; {skipped} skipped.").format(
                ok=ok, skipped=skipped
            ),
        )
    action_mark_sent.short_description = _("Mark selected as sent")

    def action_mark_overdue(self, request, queryset):
        from .services import mark_overdue

        ok, skipped = 0, 0
        for invoice in queryset:
            try:
                mark_overdue(invoice, actor=request.user)
                ok += 1
            except Exception:
                skipped += 1

        self.message_user(
            request,
            _("Marked {ok} invoice(s) overdue; {skipped} skipped.").format(
                ok=ok, skipped=skipped
            ),
        )
    action_mark_overdue.short_description = _("Mark selected as overdue")

    def action_render_pdf(self, request, queryset):
        from .services import RenderBackendUnavailable, render_and_attach

        ok, failed = 0, 0
        for invoice in queryset:
            try:
                render_and_attach(invoice, actor=request.user)
                ok += 1
            except RenderBackendUnavailable:
                failed += 1
            except Exception:
                failed += 1

        self.message_user(
            request,
            _("Rendered {ok} invoice(s); {failed} failed.").format(
                ok=ok, failed=failed
            ),
        )
    action_render_pdf.short_description = _("Render selected to PDF")


# =====================================================================
# INVOICE LINE ITEM
# =====================================================================


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice_link",
        "description",
        "quantity",
        "unit_price",
        "line_total",
        "currency",
    )
    list_filter = (
        "currency",
        ("invoice", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "description",
        "invoice__number",
    )
    raw_id_fields = ("invoice",)
    readonly_fields = ("line_total", "created_at", "updated_at")

    fieldsets = (
        (
            _("Line"),
            {
                "fields": (
                    "invoice",
                    "description",
                    "quantity",
                    "unit_price",
                    "currency",
                )
            },
        ),
        (
            _("Tax and discount"),
            {
                "fields": (
                    "discount_amount",
                    "tax_rate",
                    "tax_amount",
                    "line_total",
                )
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ("metadata",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def invoice_link(self, obj):
        url = reverse(
            "admin:invoice_invoice_change",
            args=(obj.invoice_id,),
        )
        return format_html('<a href="{}">{}</a>', url, obj.invoice.number)
    invoice_link.short_description = _("Invoice")
    invoice_link.admin_order_field = "invoice__number"


# =====================================================================
# INVOICE PAYMENT
# =====================================================================


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice_link",
        "amount",
        "currency",
        "payment_type",
        "payment_id",
        "applied_at",
        "applied_by",
    )
    list_filter = (
        "payment_type",
        "currency",
        "applied_at",
    )
    search_fields = (
        "idempotency_key",
        "payment_id",
        "invoice__number",
        "invoice__recipient__name",
        "invoice__recipient__email",
    )
    raw_id_fields = ("invoice", "applied_by")
    readonly_fields = (
        "id",
        "idempotency_key",
        "payment_type",
        "payment_id",
        "amount",
        "currency",
        "applied_at",
        "applied_by",
        "created_at",
        "metadata_display",
    )

    fieldsets = (
        (
            _("Application"),
            {
                "fields": (
                    "id",
                    "invoice",
                    ("amount", "currency"),
                    ("payment_type", "payment_id"),
                    "idempotency_key",
                )
            },
        ),
        (
            _("Audit"),
            {
                "fields": (
                    "applied_at",
                    "applied_by",
                    "created_at",
                )
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ("metadata_display",),
                "classes": ("collapse",),
            },
        ),
    )

    # Payments are immutable once applied. Reversals are new rows.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def invoice_link(self, obj):
        url = reverse(
            "admin:invoice_invoice_change",
            args=(obj.invoice_id,),
        )
        return format_html('<a href="{}">{}</a>', url, obj.invoice.number)
    invoice_link.short_description = _("Invoice")
    invoice_link.admin_order_field = "invoice__number"

    def metadata_display(self, obj):
        if not obj.metadata:
            return "-"
        return format_html(
            "<pre style='background: #f5f5f5; padding: 10px; "
            "border-radius: 4px;'>{}</pre>",
            json.dumps(obj.metadata, indent=2, default=str),
        )
    metadata_display.short_description = _("Metadata")


# =====================================================================
# INVOICE SOURCE
# =====================================================================


@admin.register(InvoiceSource)
class InvoiceSourceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice_link",
        "source_type",
        "source_id",
        "source_reference",
        "created_at",
    )
    list_filter = ("source_type",)
    search_fields = (
        "source_id",
        "source_reference",
        "invoice__number",
    )
    raw_id_fields = ("invoice",)
    readonly_fields = (
        "invoice",
        "source_type",
        "source_id",
        "source_reference",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def invoice_link(self, obj):
        url = reverse(
            "admin:invoice_invoice_change",
            args=(obj.invoice_id,),
        )
        return format_html('<a href="{}">{}</a>', url, obj.invoice.number)
    invoice_link.short_description = _("Invoice")
    invoice_link.admin_order_field = "invoice__number"


# =====================================================================
# INVOICE EVENT
# =====================================================================


@admin.register(InvoiceEvent)
class InvoiceEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice_link",
        "type",
        "occurred_at",
        "actor",
    )
    list_filter = (
        "type",
        "occurred_at",
    )
    search_fields = (
        "invoice__number",
        "actor__email",
    )
    raw_id_fields = ("invoice", "actor")
    readonly_fields = (
        "invoice",
        "type",
        "occurred_at",
        "actor",
        "parameters_display",
    )

    # Events are append-only.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def invoice_link(self, obj):
        url = reverse(
            "admin:invoice_invoice_change",
            args=(obj.invoice_id,),
        )
        return format_html('<a href="{}">{}</a>', url, obj.invoice.number)
    invoice_link.short_description = _("Invoice")
    invoice_link.admin_order_field = "invoice__number"

    def parameters_display(self, obj):
        if not obj.parameters:
            return "-"
        return format_html(
            "<pre style='background: #f5f5f5; padding: 10px; "
            "border-radius: 4px;'>{}</pre>",
            json.dumps(obj.parameters, indent=2, default=str),
        )
    parameters_display.short_description = _("Parameters")


# =====================================================================
# INVOICE SHARE
# =====================================================================


@admin.register(InvoiceShare)
class InvoiceShareAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice_link",
        "label",
        "channel",
        "created_by",
        "expires_at",
        "state_badge",
        "view_count",
    )
    list_filter = (
        "channel",
        "include_line_items",
        "expires_at",
    )
    search_fields = (
        "token",
        "label",
        "recipient_email",
        "recipient_phone",
        "invoice__number",
    )
    raw_id_fields = (
        "invoice",
        "created_by",
        "revoked_by",
    )
    readonly_fields = (
        "id",
        "token",
        "invoice",
        "created_by",
        "first_viewed_at",
        "last_viewed_at",
        "view_count",
        "created_at",
        "updated_at",
        "revoked_at",
        "revoked_by",
    )

    fieldsets = (
        (
            _("Share"),
            {
                "fields": (
                    "id",
                    "token",
                    "invoice",
                    "created_by",
                    "label",
                )
            },
        ),
        (
            _("Delivery"),
            {
                "fields": (
                    "channel",
                    "recipient_email",
                    "recipient_phone",
                    "include_line_items",
                )
            },
        ),
        (
            _("Lifetime"),
            {
                "fields": (
                    "expires_at",
                    "revoked_at",
                    "revoked_by",
                    "revoked_reason",
                )
            },
        ),
        (
            _("Usage"),
            {
                "fields": (
                    "first_viewed_at",
                    "last_viewed_at",
                    "view_count",
                )
            },
        ),
        (
            _("Audit"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["action_revoke"]

    def invoice_link(self, obj):
        url = reverse(
            "admin:invoice_invoice_change",
            args=(obj.invoice_id,),
        )
        return format_html('<a href="{}">{}</a>', url, obj.invoice.number)
    invoice_link.short_description = _("Invoice")
    invoice_link.admin_order_field = "invoice__number"

    def state_badge(self, obj):
        if obj.is_revoked:
            return format_html(
                '<span style="color: #6c757d; font-weight: bold;">'
                '{}</span>',
                _("Revoked"),
            )
        if obj.is_expired:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">'
                '{}</span>',
                _("Expired"),
            )
        return format_html(
            '<span style="color: #28a745; font-weight: bold;">'
            '{}</span>',
            _("Active"),
        )
    state_badge.short_description = _("State")

    def action_revoke(self, request, queryset):
        from .services import revoke_share

        ok, skipped = 0, 0
        for share in queryset:
            try:
                revoke_share(
                    share_id=share.pk,
                    by=request.user,
                    reason="Revoked from admin",
                )
                ok += 1
            except Exception:
                skipped += 1

        self.message_user(
            request,
            _("Revoked {ok} share(s); {skipped} skipped.").format(
                ok=ok, skipped=skipped
            ),
        )
    action_revoke.short_description = _("Revoke selected shares")