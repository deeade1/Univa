# graphq/ecommerce/types/checkout.py

"""
GraphQL Nodes for Checkout and CheckoutLine.

Totals are computed live via `ecommerce.services.checkout.calculations`
rather than read from cached columns, so the client always sees
up-to-date values after mutations.

Money fields on the model (MoneyField / TaxedMoneyField) are
auto-converted to GraphQL `Money` / `TaxedMoney` types via the
converters registered in `graphq.core.types.money`.
"""

from __future__ import annotations

import graphene
from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from graphq.core.types.money import Money, TaxedMoney
from ecommerce.models.checkout import Checkout, CheckoutLine


# =====================================================================
# CHECKOUT LINE
# =====================================================================


class CheckoutLineNode(OptimizedDjangoObjectType):
    """A line in a checkout (cart)."""

    total_price = graphene.Field(
        TaxedMoney,
        description=(
            "Effective taxed total for this line "
            "(unit price × quantity)."
        ),
    )
    unit_price = graphene.Field(
        TaxedMoney,
        description="Effective taxed unit price for this line.",
    )
    is_shipping_required = graphene.Boolean(
        description="Whether the variant requires shipping.",
    )
    quantity_unit_display = graphene.String(
        description="Human-readable quantity unit label.",
    )

    class Meta:
        model = CheckoutLine
        interfaces = (Node,)
        fields = (
            "id",
            "variant",
            "quantity",
            "quantity_unit",
            "is_gift",
            "price_override",
            "currency",
            "created_at",
        )
        filter_fields = {
            "checkout": ["exact"],
            "variant": ["exact"],
            "quantity": ["exact", "gte", "lte"],
            "quantity_unit": ["exact"],
            "is_gift": ["exact"],
            "currency": ["exact"],
            "created_at": ["exact", "gte", "lte"],
        }

    def resolve_total_price(self, info):
        from ecommerce.services.checkout.calculations import (
            _calculate_line_total,
        )

        checkout = self.checkout
        country_code = checkout.get_country()
        return _calculate_line_total(self, checkout, country_code)

    def resolve_unit_price(self, info):
        from ecommerce.services.product.pricing import (
            get_variant_availability,
        )

        checkout = self.checkout
        country_code = checkout.get_country()
        availability = get_variant_availability(
            self.variant, checkout.channel, country_code
        )
        if availability is None:
            return None
        return availability.price

    def resolve_is_shipping_required(self, info):
        return self.variant.is_shipping_required()

    def resolve_quantity_unit_display(self, info):
        from core.pricing.quantity_unit import QuantityUnit, label

        try:
            return label(QuantityUnit(self.quantity_unit))
        except ValueError:
            return self.quantity_unit


# =====================================================================
# CHECKOUT
# =====================================================================


class CheckoutNode(OptimizedDjangoObjectType):
    """A checkout (cart) belonging to a user or a guest session."""

    # ------------------------------------------------------------------
    # Lines (plain list — carts are small, clients want all lines)
    # ------------------------------------------------------------------

    lines = graphene.List(
        graphene.NonNull(
            "graphq.ecommerce.types.checkout.CheckoutLineNode"
        ),
        description=(
            "All lines in this checkout, ordered by creation. "
            "Returned as a plain list — carts are small and "
            "clients need all lines in one response."
        ),
    )

    # ------------------------------------------------------------------
    # Computed totals
    # ------------------------------------------------------------------

    subtotal = graphene.Field(
        TaxedMoney,
        description="Effective taxed subtotal of all lines.",
    )
    shipping_price = graphene.Field(
        TaxedMoney,
        description="Taxed shipping price for the selected method.",
    )
    total = graphene.Field(
        TaxedMoney,
        description="Effective taxed grand total (subtotal + shipping).",
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    is_locked = graphene.Boolean(
        description="Whether the checkout is being completed.",
    )
    is_shipping_required = graphene.Boolean(
        description="Whether any line requires shipping.",
    )
    is_completable = graphene.Boolean(
        description="Whether the checkout is ready to complete.",
    )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    customer_email = graphene.String(
        description="Customer email (user's or guest's).",
    )
    line_count = graphene.Int(
        description="Number of lines in the checkout.",
    )
    total_quantity = graphene.Decimal(
        description="Sum of line quantities (Decimal for weighted items).",
    )

    class Meta:
        model = Checkout
        interfaces = (Node,)
        fields = (
            "id",
            "token",
            "user",
            "email",
            "language_code",
            "channel",
            "currency",
            "country",
            "billing_address",
            "shipping_address",
            "shipping_method",
            "collection_point",
            "note",
            "created_at",
            "last_change",
            "completing_started_at",
            "price_expiration",
            "authorize_status",
            "charge_status",
            # "lines" intentionally omitted — declared explicitly
            # above as a plain graphene.List so it is not wrapped
            # into a Relay connection by Graphene-Django.
        )
        filter_fields = {
            "user": ["exact"],
            "user__email": ["exact", "icontains"],
            "channel": ["exact"],
            "channel__slug": ["exact"],
            "email": ["exact", "icontains"],
            "token": ["exact"],
            "currency": ["exact"],
            "country": ["exact"],
            "created_at": ["exact", "gte", "lte"],
            "last_change": ["exact", "gte", "lte"],
            "completing_started_at": ["exact", "gte", "lte", "isnull"],
        }

    # ------------------------------------------------------------------
    # Lines resolver
    # ------------------------------------------------------------------

    def resolve_lines(self, info):
        return self.lines.all().order_by("created_at")

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    def resolve_subtotal(self, info):
        from ecommerce.services.checkout.calculations import (
            calculate_checkout_subtotal,
        )

        return calculate_checkout_subtotal(self, self.get_country())

    def resolve_shipping_price(self, info):
        from ecommerce.services.checkout.calculations import (
            calculate_checkout_shipping,
        )

        return calculate_checkout_shipping(self, self.get_country())

    def resolve_total(self, info):
        from ecommerce.services.checkout.calculations import (
            calculate_checkout_total,
        )

        return calculate_checkout_total(self, self.get_country())

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def resolve_is_locked(self, info):
        return self.completing_started_at is not None

    def resolve_is_shipping_required(self, info):
        return self.is_shipping_required()

    def resolve_is_completable(self, info):
        from ecommerce.services.checkout.complete import (
            CheckoutNotReady,
            validate_checkout_for_completion,
        )

        try:
            validate_checkout_for_completion(self)
        except CheckoutNotReady:
            return False
        return True

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def resolve_customer_email(self, info):
        return self.get_customer_email()

    def resolve_line_count(self, info):
        return self.lines.count()

    def resolve_total_quantity(self, info):
        from decimal import Decimal

        return sum(
            (line.quantity for line in self.lines.all()),
            start=Decimal("0"),
        )


__all__ = [
    "CheckoutLineNode",
    "CheckoutNode",
]