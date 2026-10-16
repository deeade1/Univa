# graphq/ecommerce/mutations/checkout.py

"""
Checkout GraphQL mutations.

Every mutation returns a payload with:
    - the affected checkout (or null on hard failure)
    - an `errors` list (never raises; errors are structured)

Business errors are always returned in the payload, not as
GraphQL-level errors. This lets the Univa app display them
precisely.

Every mutation that changes checkout state refreshes the
checkout instance before returning it, so computed fields
(lineCount, totalQuantity, subtotal, total, ...) reflect the
current database state rather than a stale in-memory relation
cache.
"""

from __future__ import annotations

from decimal import Decimal

import graphene
from graphene import relay
from graphql_relay import from_global_id, to_global_id

from core.exceptions import InsufficientStock
from ecommerce.models.channel import Channel
from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.product import ProductVariant
from ecommerce.models.shipping import ShippingMethod
from ecommerce.services.checkout import (
    CheckoutNotReady,
    add_variant_to_checkout,
    complete_checkout,
    ClaimError,
    claim_checkout,
    create_checkout,
    get_checkout_by_token,
    remove_checkout_line,
    set_checkout_billing_address,
    set_checkout_shipping_address,
    set_checkout_shipping_method,
    update_checkout_line_quantity,
)
from ecommerce.models.enums.errors import (
    CheckoutErrorCode,
    ClaimErrorCode,
)
from graphq.ecommerce.types.errors import (
    CheckoutError,
    ClaimErrorPayload,
)
from graphq.ecommerce.types.checkout import CheckoutNode



# =====================================================================
# HELPERS
# =====================================================================



def _get_checkout_or_error(token: str):
    """Return (checkout, errors)."""
    try:
        checkout = get_checkout_by_token(token)
    except (ValueError, TypeError):
        return None, [
            CheckoutError(
                message="Invalid checkout token.",
                code=CheckoutErrorCode.NOT_FOUND,
                field="token",
            )
        ]

    if checkout is None:
        return None, [
            CheckoutError(
                message="Checkout not found.",
                code=CheckoutErrorCode.NOT_FOUND,
                field="token",
            )
        ]

    return checkout, []


def _resolve_variant(global_id: str) -> ProductVariant | None:
    try:
        _, pk = from_global_id(global_id)
        return ProductVariant.objects.get(pk=pk)
    except (ValueError, TypeError, ProductVariant.DoesNotExist):
        return None


def _resolve_channel(slug: str) -> Channel | None:
    return Channel.objects.filter(slug=slug, is_active=True).first()


def _resolve_shipping_method(global_id: str) -> ShippingMethod | None:
    try:
        _, pk = from_global_id(global_id)
        return ShippingMethod.objects.get(pk=pk)
    except (ValueError, TypeError, ShippingMethod.DoesNotExist):
        return None


def _refresh(checkout: Checkout | None) -> Checkout | None:
    """
    Refresh a checkout instance from the database so computed
    fields reflect state after a mutation.

    Safe to call with None.
    """
    if checkout is None:
        return None
    checkout.refresh_from_db()
    return checkout


# =====================================================================
# MUTATIONS
# =====================================================================


class CheckoutCreate(relay.ClientIDMutation):
    """Create a new checkout on a channel."""

    class Input:
        channel_slug = graphene.String(required=True)
        email = graphene.String(
            description="Optional guest email."
        )
        currency = graphene.String(
            description="Optional. Defaults to the channel's currency."
        )

    checkout = graphene.Field(CheckoutNode)
    errors = graphene.List(
        graphene.NonNull(CheckoutError),
        required=True,
    )

    @classmethod
    def mutate_and_get_payload(
        cls, root, info, channel_slug, email=None, currency=None
    ):
        user = info.context.user if info.context.user.is_authenticated else None

        channel = _resolve_channel(channel_slug)
        if channel is None:
            return CheckoutCreate(
                checkout=None,
                errors=[
                    CheckoutError(
                        message="Channel not found.",
                        code=CheckoutErrorCode.NOT_FOUND,
                        field="channelSlug",
                    )
                ],
            )

        checkout = create_checkout(
            channel,
            user=user,
            email=email,
            currency=currency,
        )

        # Fresh instance was just created; no refresh needed.
        return CheckoutCreate(checkout=checkout, errors=[])


class CheckoutAddLine(relay.ClientIDMutation):
    """Add a variant to a checkout."""

    class Input:
        token = graphene.UUID(required=True)
        variant_id = graphene.ID(required=True)
        quantity = graphene.Decimal(required=True)
        replace = graphene.Boolean(
            default_value=False,
            description="If true, set quantity instead of adding.",
        )

    checkout = graphene.Field(CheckoutNode)
    checkout_line = graphene.Field(
        "graphq.ecommerce.types.checkout.CheckoutLineNode"
    )
    errors = graphene.List(
        graphene.NonNull(CheckoutError),
        required=True,
    )

    @classmethod
    def mutate_and_get_payload(
        cls, root, info, token, variant_id, quantity, replace=False
    ):
        checkout, errors = _get_checkout_or_error(str(token))
        if errors:
            return CheckoutAddLine(
                checkout=None, checkout_line=None, errors=errors
            )

        variant = _resolve_variant(variant_id)
        if variant is None:
            return CheckoutAddLine(
                checkout=checkout,
                checkout_line=None,
                errors=[
                    CheckoutError(
                        message="Variant not found.",
                        code=CheckoutErrorCode.NOT_FOUND,
                        field="variantId",
                    )
                ],
            )

        try:
            quantity_decimal = Decimal(str(quantity))
        except Exception:
            return CheckoutAddLine(
                checkout=checkout,
                checkout_line=None,
                errors=[
                    CheckoutError(
                        message="Invalid quantity.",
                        code=CheckoutErrorCode.INVALID,
                        field="quantity",
                    )
                ],
            )

        try:
            line = add_variant_to_checkout(
                checkout, variant, quantity_decimal, replace=replace
            )
        except InsufficientStock as e:
            variant_ids = [
                to_global_id(
                    "ProductVariantNode", str(item.variant.id)
                )
                for item in e.items
                if item.variant
            ]
            return CheckoutAddLine(
                checkout=_refresh(checkout),
                checkout_line=None,
                errors=[
                    CheckoutError(
                        message=str(e),
                        code=CheckoutErrorCode.INSUFFICIENT_STOCK,
                        field="quantity",
                        variants=variant_ids,
                    )
                ],
            )
        except ValueError as e:
            return CheckoutAddLine(
                checkout=_refresh(checkout),
                checkout_line=None,
                errors=[
                    CheckoutError(
                        message=str(e),
                        code=CheckoutErrorCode.INVALID,
                        field="quantity",
                    )
                ],
            )

        return CheckoutAddLine(
            checkout=_refresh(checkout),
            checkout_line=line,
            errors=[],
        )


class CheckoutUpdateLine(relay.ClientIDMutation):
    """Set the quantity of an existing checkout line."""

    class Input:
        token = graphene.UUID(required=True)
        line_id = graphene.ID(required=True)
        quantity = graphene.Decimal(required=True)

    checkout = graphene.Field(CheckoutNode)
    errors = graphene.List(
        graphene.NonNull(CheckoutError), required=True
    )

    @classmethod
    def mutate_and_get_payload(
        cls, root, info, token, line_id, quantity
    ):
        checkout, errors = _get_checkout_or_error(str(token))
        if errors:
            return CheckoutUpdateLine(checkout=None, errors=errors)

        try:
            _, line_pk = from_global_id(line_id)
            line = CheckoutLine.objects.get(pk=line_pk, checkout=checkout)
        except (ValueError, CheckoutLine.DoesNotExist):
            return CheckoutUpdateLine(
                checkout=checkout,
                errors=[
                    CheckoutError(
                        message="Checkout line not found.",
                        code=CheckoutErrorCode.NOT_FOUND,
                        field="lineId",
                    )
                ],
            )

        try:
            quantity_decimal = Decimal(str(quantity))
        except Exception:
            return CheckoutUpdateLine(
                checkout=checkout,
                errors=[
                    CheckoutError(
                        message="Invalid quantity.",
                        code=CheckoutErrorCode.INVALID,
                        field="quantity",
                    )
                ],
            )

        try:
            update_checkout_line_quantity(
                checkout, line, quantity_decimal
            )
        except InsufficientStock as e:
            return CheckoutUpdateLine(
                checkout=_refresh(checkout),
                errors=[
                    CheckoutError(
                        message=str(e),
                        code=CheckoutErrorCode.INSUFFICIENT_STOCK,
                        field="quantity",
                    )
                ],
            )

        return CheckoutUpdateLine(
            checkout=_refresh(checkout), errors=[]
        )


class CheckoutRemoveLine(relay.ClientIDMutation):
    """Remove a line from a checkout."""

    class Input:
        token = graphene.UUID(required=True)
        line_id = graphene.ID(required=True)

    checkout = graphene.Field(CheckoutNode)
    errors = graphene.List(
        graphene.NonNull(CheckoutError), required=True
    )

    @classmethod
    def mutate_and_get_payload(cls, root, info, token, line_id):
        checkout, errors = _get_checkout_or_error(str(token))
        if errors:
            return CheckoutRemoveLine(checkout=None, errors=errors)

        try:
            _, line_pk = from_global_id(line_id)
            line = CheckoutLine.objects.get(pk=line_pk, checkout=checkout)
        except (ValueError, CheckoutLine.DoesNotExist):
            return CheckoutRemoveLine(
                checkout=checkout,
                errors=[
                    CheckoutError(
                        message="Checkout line not found.",
                        code=CheckoutErrorCode.NOT_FOUND,
                        field="lineId",
                    )
                ],
            )

        remove_checkout_line(checkout, line)
        return CheckoutRemoveLine(
            checkout=_refresh(checkout), errors=[]
        )


class CheckoutSetShippingAddress(relay.ClientIDMutation):
    """Attach a shipping address to a checkout."""

    class Input:
        token = graphene.UUID(required=True)
        address_id = graphene.ID(required=True)

    checkout = graphene.Field(CheckoutNode)
    errors = graphene.List(
        graphene.NonNull(CheckoutError), required=True
    )

    @classmethod
    def mutate_and_get_payload(cls, root, info, token, address_id):
        from accounts.models import Address

        checkout, errors = _get_checkout_or_error(str(token))
        if errors:
            return CheckoutSetShippingAddress(checkout=None, errors=errors)

        try:
            _, address_pk = from_global_id(address_id)
            address = Address.objects.get(pk=address_pk)
        except (ValueError, Address.DoesNotExist):
            return CheckoutSetShippingAddress(
                checkout=checkout,
                errors=[
                    CheckoutError(
                        message="Address not found.",
                        code=CheckoutErrorCode.NOT_FOUND,
                        field="addressId",
                    )
                ],
            )

        set_checkout_shipping_address(checkout, address)
        return CheckoutSetShippingAddress(
            checkout=_refresh(checkout), errors=[]
        )


class CheckoutSetBillingAddress(relay.ClientIDMutation):
    """Attach a billing address to a checkout."""

    class Input:
        token = graphene.UUID(required=True)
        address_id = graphene.ID(required=True)

    checkout = graphene.Field(CheckoutNode)
    errors = graphene.List(
        graphene.NonNull(CheckoutError), required=True
    )

    @classmethod
    def mutate_and_get_payload(cls, root, info, token, address_id):
        from accounts.models import Address

        checkout, errors = _get_checkout_or_error(str(token))
        if errors:
            return CheckoutSetBillingAddress(checkout=None, errors=errors)

        try:
            _, address_pk = from_global_id(address_id)
            address = Address.objects.get(pk=address_pk)
        except (ValueError, Address.DoesNotExist):
            return CheckoutSetBillingAddress(
                checkout=checkout,
                errors=[
                    CheckoutError(
                        message="Address not found.",
                        code=CheckoutErrorCode.NOT_FOUND,
                        field="addressId",
                    )
                ],
            )

        set_checkout_billing_address(checkout, address)
        return CheckoutSetBillingAddress(
            checkout=_refresh(checkout), errors=[]
        )


class CheckoutSetShippingMethod(relay.ClientIDMutation):
    """Select a shipping method for a checkout."""

    class Input:
        token = graphene.UUID(required=True)
        shipping_method_id = graphene.ID(
            required=False,
            description="Pass null to clear the shipping method.",
        )

    checkout = graphene.Field(CheckoutNode)
    errors = graphene.List(
        graphene.NonNull(CheckoutError), required=True
    )

    @classmethod
    def mutate_and_get_payload(
        cls, root, info, token, shipping_method_id=None
    ):
        checkout, errors = _get_checkout_or_error(str(token))
        if errors:
            return CheckoutSetShippingMethod(checkout=None, errors=errors)

        if shipping_method_id is None:
            set_checkout_shipping_method(checkout, None)
            return CheckoutSetShippingMethod(
                checkout=_refresh(checkout), errors=[]
            )

        method = _resolve_shipping_method(shipping_method_id)
        if method is None:
            return CheckoutSetShippingMethod(
                checkout=checkout,
                errors=[
                    CheckoutError(
                        message="Shipping method not found.",
                        code=CheckoutErrorCode.NOT_FOUND,
                        field="shippingMethodId",
                    )
                ],
            )

        set_checkout_shipping_method(checkout, method)
        return CheckoutSetShippingMethod(
            checkout=_refresh(checkout), errors=[]
        )


class CheckoutComplete(relay.ClientIDMutation):
    """Convert a checkout into an order."""

    class Input:
        token = graphene.UUID(required=True)

    checkout = graphene.Field(
        CheckoutNode,
        description="The (now deleted) checkout, for reference.",
    )
    order_id = graphene.ID(
        description="Global ID of the created order."
    )
    errors = graphene.List(
        graphene.NonNull(CheckoutError), required=True
    )

    @classmethod
    def mutate_and_get_payload(cls, root, info, token):
        checkout, errors = _get_checkout_or_error(str(token))
        if errors:
            return CheckoutComplete(
                checkout=None, order_id=None, errors=errors
            )

        user = info.context.user if info.context.user.is_authenticated else None

        try:
            order = complete_checkout(checkout, user=user)
        except CheckoutNotReady as e:
            return CheckoutComplete(
                checkout=checkout,
                order_id=None,
                errors=[
                    CheckoutError(
                        message=str(e),
                        code=CheckoutErrorCode.INVALID,
                    )
                ],
            )
        except InsufficientStock as e:
            return CheckoutComplete(
                checkout=checkout,
                order_id=None,
                errors=[
                    CheckoutError(
                        message=str(e),
                        code=CheckoutErrorCode.INSUFFICIENT_STOCK,
                    )
                ],
            )

        order_gid = to_global_id("OrderNode", str(order.pk))
        return CheckoutComplete(
            checkout=None, order_id=order_gid, errors=[]
        )

class CheckoutClaim(relay.ClientIDMutation):
    """
    Claim an anonymous checkout for the currently authenticated user.

    See `ecommerce.services.checkout.claim` for merge rules.
    """

    class Input:
        token = graphene.UUID(required=True)
        merge = graphene.Boolean(
            default_value=True,
            description=(
                "If true (default), a non-empty guest cart is merged "
                "into the user's existing cart on the same channel. "
                "If false, the guest cart receives ownership directly "
                "and the user may end up with multiple active carts."
            ),
        )

    checkout = graphene.Field(CheckoutNode)
    errors = graphene.List(
        graphene.NonNull(ClaimErrorPayload), required=True
    )

    @classmethod
    def mutate_and_get_payload(cls, root, info, token, merge=True):
        user = info.context.user
        if user is None or not user.is_authenticated:
            return CheckoutClaim(
                checkout=None,
                errors=[
                    ClaimErrorPayload(
                        message="Authentication required.",
                        code=ClaimErrorCode.INVALID,
                    )
                ],
            )

        checkout, errors = _get_checkout_or_error(str(token))
        if errors:
            return CheckoutClaim(
                checkout=None,
                errors=[
                    ClaimErrorPayload(
                        message=e.message,
                        code=ClaimErrorCode(e.code.value),
                        field=e.field,
                    )
                    for e in errors
                ],
            )

        try:
            checkout = claim_checkout(checkout, user, merge=merge)
        except ClaimError as exc:
            return CheckoutClaim(
                checkout=checkout,
                errors=[
                    ClaimErrorPayload(
                        message=str(exc),
                        code=exc.code,
                    )
                ],
            )

        checkout.refresh_from_db()
        return CheckoutClaim(checkout=checkout, errors=[])
    
# =====================================================================
# AGGREGATE
# =====================================================================


class CheckoutMutations(graphene.ObjectType):
    """Checkout mutation root."""

    checkout_create = CheckoutCreate.Field()
    checkout_add_line = CheckoutAddLine.Field()
    checkout_update_line = CheckoutUpdateLine.Field()
    checkout_remove_line = CheckoutRemoveLine.Field()
    checkout_set_shipping_address = CheckoutSetShippingAddress.Field()
    checkout_set_billing_address = CheckoutSetBillingAddress.Field()
    checkout_set_shipping_method = CheckoutSetShippingMethod.Field()
    checkout_claim = CheckoutClaim.Field()
    checkout_complete = CheckoutComplete.Field()


__all__ = [
    "CheckoutMutations",
    "CheckoutCreate",
    "CheckoutAddLine",
    "CheckoutUpdateLine",
    "CheckoutRemoveLine",
    "CheckoutSetShippingAddress",
    "CheckoutSetBillingAddress",
    "CheckoutSetShippingMethod",
    "CheckoutComplete",
    "CheckoutClaim",
]


