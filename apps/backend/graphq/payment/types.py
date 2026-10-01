# apps/backend/graphq/payment/types.py

"""
GraphQL types for the Payment domain.

This module contains all GraphQL node types for payment models including:
    - Payment: Core payment model
    - Transaction: Payment transaction model
    - TransactionEvent: Transaction event model
    - TransactionItem: Transaction item model
    - PaymentMethod: Stored payment methods
"""

import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene.types.generic import GenericScalar
from decimal import Decimal

from payment.models import (
    Payment,
    Transaction,
    TransactionEvent,
    TransactionItem,
    PaymentMethod,
)


# ============================================================================
# TRANSACTION ITEM NODE
# ============================================================================

class TransactionItemNode(DjangoObjectType):
    """Transaction item node type."""
    
    formatted_amount_charged = graphene.String()
    formatted_amount_authorized = graphene.String()
    formatted_amount_refunded = graphene.String()
    formatted_amount_canceled = graphene.String()
    formatted_amount_refund_pending = graphene.String()
    formatted_amount_charge_pending = graphene.String()
    formatted_amount_authorize_pending = graphene.String()
    formatted_amount_cancel_pending = graphene.String()
    checkout_id = graphene.ID()
    order_id = graphene.ID()
    user_id = graphene.ID()
    
    class Meta:
        model = TransactionItem
        interfaces = (relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "token": ["exact"],
            "order__id": ["exact"],
            "user__id": ["exact"],
            "currency": ["exact", "icontains"],
            "created_at": ["exact", "gt", "gte", "lt", "lte"],
            "modified_at": ["exact", "gt", "gte", "lt", "lte"],
            "idempotency_key": ["exact", "icontains"],
        }

    def resolve_formatted_amount_charged(self, info):
        return f"{self.currency} {self.charged_value:,.2f}"

    def resolve_formatted_amount_authorized(self, info):
        return f"{self.currency} {self.authorized_value:,.2f}"

    def resolve_formatted_amount_refunded(self, info):
        return f"{self.currency} {self.refunded_value:,.2f}"

    def resolve_formatted_amount_canceled(self, info):
        return f"{self.currency} {self.canceled_value:,.2f}"

    def resolve_formatted_amount_refund_pending(self, info):
        return f"{self.currency} {self.refund_pending_value:,.2f}"

    def resolve_formatted_amount_charge_pending(self, info):
        return f"{self.currency} {self.charge_pending_value:,.2f}"

    def resolve_formatted_amount_authorize_pending(self, info):
        return f"{self.currency} {self.authorize_pending_value:,.2f}"

    def resolve_formatted_amount_cancel_pending(self, info):
        return f"{self.currency} {self.cancel_pending_value:,.2f}"

    def resolve_checkout_id(self, info):
        if self.checkout_id:
            return self.checkout_id
        return None

    def resolve_order_id(self, info):
        if self.order_id:
            return self.order_id
        return None

    def resolve_user_id(self, info):
        if self.user_id:
            return self.user_id
        return None


# ============================================================================
# TRANSACTION EVENT NODE
# ============================================================================

class TransactionEventNode(DjangoObjectType):
    """Transaction event node type."""
    
    formatted_amount = graphene.String()
    transaction_id = graphene.ID()
    user_id = graphene.ID()
    type_display = graphene.String()
    related_granted_refund_id = graphene.ID()
    
    class Meta:
        model = TransactionEvent
        interfaces = (relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "transaction__id": ["exact"],
            "currency": ["exact", "icontains"],
            "type": ["exact"],
            "created_at": ["exact", "gt", "gte", "lt", "lte"],
            "idempotency_key": ["exact", "icontains"],
        }

    def resolve_formatted_amount(self, info):
        return f"{self.currency} {self.amount_value:,.2f}"

    def resolve_transaction_id(self, info):
        return self.transaction_id

    def resolve_user_id(self, info):
        if self.user_id:
            return self.user_id
        return None

    def resolve_type_display(self, info):
        return dict(TransactionEventType.CHOICES).get(self.type, self.type)

    def resolve_related_granted_refund_id(self, info):
        if hasattr(self, 'related_granted_refund_id'):
            return self.related_granted_refund_id
        return None


# ============================================================================
# PAYMENT NODE
# ============================================================================

class PaymentNode(DjangoObjectType):
    """Payment node type."""
    
    formatted_total = graphene.String()
    formatted_captured_amount = graphene.String()
    checkout_id = graphene.ID()
    order_id = graphene.ID()
    charge_status_display = graphene.String()
    store_payment_method_display = graphene.String()
    is_authorized = graphene.Boolean()
    can_capture = graphene.Boolean()
    can_refund = graphene.Boolean()
    can_void = graphene.Boolean()
    
    class Meta:
        model = Payment
        interfaces = (relay.Node,)
        filter_fields = {
            "gateway": ["exact", "icontains"],
            "currency": ["exact", "icontains"],
            "charge_status": ["exact"],
            "is_active": ["exact"],
            "created_at": ["exact", "gt", "gte", "lt", "lte"],
            "token": ["exact", "icontains"],
        }

    def resolve_formatted_total(self, info):
        return f"{self.currency} {self.total:,.2f}"

    def resolve_formatted_captured_amount(self, info):
        return f"{self.currency} {self.captured_amount:,.2f}"

    def resolve_checkout_id(self, info):
        if self.checkout_id:
            return self.checkout_id
        return None

    def resolve_order_id(self, info):
        if self.order_id:
            return self.order_id
        return None

    def resolve_charge_status_display(self, info):
        return dict(ChargeStatus.CHOICES).get(self.charge_status, self.charge_status)

    def resolve_store_payment_method_display(self, info):
        return dict(StorePaymentMethod.CHOICES).get(self.store_payment_method, self.store_payment_method)

    def resolve_is_authorized(self, info):
        return self.is_authorized

    def resolve_can_capture(self, info):
        return self.can_capture()

    def resolve_can_refund(self, info):
        return self.can_refund()

    def resolve_can_void(self, info):
        return self.can_void()


# ============================================================================
# TRANSACTION NODE
# ============================================================================

class TransactionNode(DjangoObjectType):
    """Transaction node type."""
    
    formatted_amount = graphene.String()
    payment_id = graphene.ID()
    kind_display = graphene.String()
    formatted_univa_discount = graphene.String()
    
    class Meta:
        model = Transaction
        interfaces = (relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "payment__id": ["exact"],
            "kind": ["exact"],
            "is_success": ["exact"],
            "currency": ["exact", "icontains"],
            "created_at": ["exact", "gt", "gte", "lt", "lte"],
            "token": ["exact", "icontains"],
            "is_univa_payment": ["exact"],
        }

    def resolve_formatted_amount(self, info):
        return f"{self.currency} {self.amount:,.2f}"

    def resolve_payment_id(self, info):
        return self.payment_id

    def resolve_kind_display(self, info):
        return dict(TransactionKind.CHOICES).get(self.kind, self.kind)

    def resolve_formatted_univa_discount(self, info):
        return f"{self.currency} {self.univa_discount_applied:,.2f}"


# ============================================================================
# PAYMENT METHOD NODE
# ============================================================================

class PaymentMethodNode(DjangoObjectType):
    """Payment method node type."""
    
    type_display = graphene.String()
    gateway_display = graphene.String()
    card_brand_display = graphene.String()
    is_card = graphene.Boolean()
    is_expired = graphene.Boolean()
    display_name = graphene.String()
    last_four = graphene.String()
    billing_address_id = graphene.ID()
    formatted_created_at = graphene.String()
    formatted_updated_at = graphene.String()
    formatted_last_used_at = graphene.String()
    
    class Meta:
        model = PaymentMethod
        interfaces = (relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "user__id": ["exact"],
            "type": ["exact"],
            "is_default": ["exact"],
            "is_active": ["exact"],
            "gateway": ["exact"],
            "gateway_token": ["exact", "icontains"],
            "created_at": ["exact", "gt", "gte", "lt", "lte"],
        }

    def resolve_type_display(self, info):
        return dict(PaymentMethod.PaymentType.choices).get(self.type, self.type)

    def resolve_gateway_display(self, info):
        return dict(PaymentMethod.GatewayProvider.choices).get(self.gateway, self.gateway)

    def resolve_card_brand_display(self, info):
        return dict(PaymentMethod.CardBrand.choices).get(self.cc_brand, self.cc_brand)

    def resolve_is_card(self, info):
        return self.is_card

    def resolve_is_expired(self, info):
        return self.is_expired

    def resolve_display_name(self, info):
        return self.display_name

    def resolve_last_four(self, info):
        return self.last_four

    def resolve_billing_address_id(self, info):
        if self.billing_address_id:
            return self.billing_address_id
        return None

    def resolve_formatted_created_at(self, info):
        return self.created_at.strftime("%Y-%m-%d %H:%M:%S")

    def resolve_formatted_updated_at(self, info):
        return self.updated_at.strftime("%Y-%m-%d %H:%M:%S")

    def resolve_formatted_last_used_at(self, info):
        if self.last_used_at:
            return self.last_used_at.strftime("%Y-%m-%d %H:%M:%S")
        return None




# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "TransactionItemNode",
    "TransactionEventNode",
    "PaymentNode",
    "TransactionNode",
    "PaymentMethodNode",
    "PaymentQuery",
]