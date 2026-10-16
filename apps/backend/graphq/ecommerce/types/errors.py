# graphq/ecommerce/types/errors.py

"""
Shared GraphQL error types for ecommerce mutations.
"""

from __future__ import annotations

import graphene

from ecommerce.models.enums.errors import (
    CheckoutCreateFromOrderErrorCode,
    CheckoutCreateFromOrderUnavailableVariantErrorCode,
    CheckoutErrorCode,
    OrderCreateFromCheckoutErrorCode,
    OrderErrorCode, 
    ClaimErrorCode,
    
)


# =====================================================================
# ENUMS
# =====================================================================


CheckoutErrorCodeEnum = graphene.Enum.from_enum(
    CheckoutErrorCode,
    name="CheckoutErrorCode",
)

OrderCreateFromCheckoutErrorCodeEnum = graphene.Enum.from_enum(
    OrderCreateFromCheckoutErrorCode,
    name="OrderCreateFromCheckoutErrorCode",
)

CheckoutCreateFromOrderErrorCodeEnum = graphene.Enum.from_enum(
    CheckoutCreateFromOrderErrorCode,
    name="CheckoutCreateFromOrderErrorCode",
)

CheckoutCreateFromOrderUnavailableVariantErrorCodeEnum = (
    graphene.Enum.from_enum(
        CheckoutCreateFromOrderUnavailableVariantErrorCode,
        name="CheckoutCreateFromOrderUnavailableVariantErrorCode",
    )
)

OrderErrorCodeEnum = graphene.Enum.from_enum(
    OrderErrorCode,
    name="OrderErrorCode",
)

ClaimErrorCodeEnum = graphene.Enum.from_enum(
    ClaimErrorCode,
    name="ClaimErrorCode",
)
# =====================================================================
# ERROR TYPES
# =====================================================================


class CheckoutError(graphene.ObjectType):
    """A business error returned from a checkout mutation."""

    field = graphene.String(
        description="Input field that caused the error, if any.",
    )
    message = graphene.String(
        required=True,
        description="Human-readable error message.",
    )
    code = graphene.Field(
        CheckoutErrorCodeEnum,
        required=True,
        description="Machine-readable error code.",
    )
    variants = graphene.List(
        graphene.NonNull(graphene.ID),
        description="Variant global IDs affected by this error, if any.",
    )

    def __init__(
        self,
        message: str,
        code: CheckoutErrorCode = CheckoutErrorCode.INVALID,
        field: str | None = None,
        variants: list[str] | None = None,
    ):
        super().__init__()
        self.message = message
        self.code = code
        self.field = field
        self.variants = variants or []

    def resolve_code(self, info):
        """Return the enum member's name for GraphQL serialization."""
        return self.code.name


class OrderError(graphene.ObjectType):
    """A business error returned from an order mutation."""

    field = graphene.String(
        description="Input field that caused the error, if any.",
    )
    message = graphene.String(
        required=True,
        description="Human-readable error message.",
    )
    code = graphene.Field(
        OrderErrorCodeEnum,
        required=True,
        description="Machine-readable error code.",
    )
    order_lines = graphene.List(
        graphene.NonNull(graphene.ID),
        description="Order line global IDs affected by this error, if any.",
    )

    def __init__(
        self,
        message: str,
        code: OrderErrorCode = OrderErrorCode.INVALID,
        field: str | None = None,
        order_lines: list[str] | None = None,
    ):
        super().__init__()
        self.message = message
        self.code = code
        self.field = field
        self.order_lines = order_lines or []

    def resolve_code(self, info):
        """Return the enum member's name for GraphQL serialization."""
        return self.code.name

class ClaimErrorPayload(graphene.ObjectType):
    """A business error returned from a checkout claim mutation."""

    field = graphene.String(
        description="Input field that caused the error, if any.",
    )
    message = graphene.String(
        required=True,
        description="Human-readable error message.",
    )
    code = graphene.Field(
        ClaimErrorCodeEnum,
        required=True,
        description="Machine-readable error code.",
    )

    def __init__(
        self,
        message: str,
        code: ClaimErrorCode = ClaimErrorCode.INVALID,
        field: str | None = None,
    ):
        super().__init__()
        self.message = message
        self.code = code
        self.field = field

    def resolve_code(self, info):
        return self.code.name
    
__all__ = [
    "CheckoutError",
    "CheckoutErrorCodeEnum",
    "OrderError",
    "OrderErrorCodeEnum",
    "OrderCreateFromCheckoutErrorCodeEnum",
    "CheckoutCreateFromOrderErrorCodeEnum",
    "CheckoutCreateFromOrderUnavailableVariantErrorCodeEnum",
    "ClaimErrorPayload",
    "ClaimErrorCodeEnum",
    
]