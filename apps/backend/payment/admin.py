# apps/backend/payment/admin.py

from django.contrib import admin

from .models import (
    Payment,
    PaymentMethod,
    TransactionEvent,
    TransactionItem,
    Transaction,
)


@admin.register(TransactionItem)
class TransactionItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_link",
        "checkout_link",
        "amount_authorized_display",
        "message",
    )

    search_fields = (
        "id",
        "token",
        "user__email",
        "user__phone_number",
    )

    readonly_fields = (
        "id",
        "order_link",
        "checkout_link",
        "amount_authorized_display",
    )

    list_filter = (
        "created_at",
    )

    ordering = ("-created_at",)

    # Only reference fields that actually exist on TransactionItem.
    raw_id_fields = tuple(
        field
        for field in (
            "order",
            "checkout",
            "user",
        )
        if any(
            model_field.name == field
            for model_field in TransactionItem._meta.get_fields()
        )
    )

    @admin.display(description="Order")
    def order_link(self, obj):
        order = getattr(obj, "order", None)
        if not order:
            return "—"
        return str(order)

    @admin.display(description="Checkout")
    def checkout_link(self, obj):
        checkout = getattr(obj, "checkout", None)
        if not checkout:
            return "—"
        return str(checkout)

    @admin.display(description="Authorized Amount")
    def amount_authorized_display(self, obj):
        value = getattr(obj, "amount_authorized", None)
        return value if value is not None else "—"


@admin.register(TransactionEvent)
class TransactionEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "transaction_link",
        "type_display",
        "amount_display",
        "message",
    )

    search_fields = (
        "message",
        "external_url",
        "transaction__token",
        "user__email",
    )

    readonly_fields = (
        "created_at",
        "transaction_link",
        "type_display",
        "amount_display",
    )

    list_filter = (
        "type",
        "created_at",
    )

    ordering = ("-created_at",)

    # Only reference relationships that actually exist.
    raw_id_fields = tuple(
        field
        for field in (
            "transaction",
            "user",
            "related_granted_refund",
        )
        if any(
            model_field.name == field
            for model_field in TransactionEvent._meta.get_fields()
        )
    )

    @admin.display(description="Transaction")
    def transaction_link(self, obj):
        transaction = getattr(obj, "transaction", None)
        if not transaction:
            return "—"
        return str(transaction)

    @admin.display(description="Type")
    def type_display(self, obj):
        value = getattr(obj, "type", None)
        return value or "—"

    @admin.display(description="Amount")
    def amount_display(self, obj):
        value = getattr(obj, "amount", None)
        return value if value is not None else "—"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment_link",
        "kind",
        "amount",
        "currency",
        "is_success",
        "created_at",
    )

    search_fields = (
        "token",
        "customer_id",
        "payment__id",
    )

    list_filter = (
        "kind",
        "is_success",
        "action_required",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "payment_link",
    )

    ordering = ("-created_at",)

    raw_id_fields = (
        "payment",
    )

    @admin.display(description="Payment")
    def payment_link(self, obj):
        payment = getattr(obj, "payment", None)
        if not payment:
            return "—"
        return str(payment)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_link",
        "checkout_link",
        "gateway",
        "psp_reference",
        "billing_email",
    )

    search_fields = (
        "id",
        "psp_reference",
        "gateway",
        "billing_email",
    )

    readonly_fields = (
        "order_link",
        "checkout_link",
        "total_display",
        "customer_id",
    )

    list_filter = (
        "gateway",
        "created_at",
    )

    ordering = ("-created_at",)

    # Only include relationships that actually exist.
    raw_id_fields = tuple(
        field
        for field in (
            "order",
            "checkout",
            "user",
        )
        if any(
            model_field.name == field
            for model_field in Payment._meta.get_fields()
        )
    )

    @admin.display(description="Order")
    def order_link(self, obj):
        order = getattr(obj, "order", None)
        if not order:
            return "—"
        return str(order)

    @admin.display(description="Checkout")
    def checkout_link(self, obj):
        checkout = getattr(obj, "checkout", None)
        if not checkout:
            return "—"
        return str(checkout)

    @admin.display(description="Total")
    def total_display(self, obj):
        value = getattr(obj, "total", None)
        if value is None:
            value = getattr(obj, "total_amount", None)
        return value if value is not None else "—"

    @admin.display(description="Customer ID")
    def customer_id(self, obj):
        user = getattr(obj, "user", None)
        if user is None:
            user = getattr(obj, "customer", None)
        return getattr(user, "pk", None) or "—"


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "type",
        "is_default",
        "created_at",
    )

    list_filter = (
        "type",
        "is_default",
        "is_active",
        "is_verified",
        "gateway",
    )

    search_fields = (
        "user__email",
        "user__phone_number",
        "name",
        "gateway",
        "cc_brand",
        "cc_last_digits",
    )

    raw_id_fields = (
        "user",
        "billing_address",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_used_at",
    )

    ordering = ("-created_at",)