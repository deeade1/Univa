# ============================================================================
# CARDS TYPES
# ============================================================================
import graphene
from graphene import String, relay
from graphene_django import DjangoObjectType


from banking.models.cards import CardBrand, CardTransaction, PhysicalCard, VirtualCard


class CardBrandNode(DjangoObjectType):
    """Card brand node type."""

    class Meta:
        model = CardBrand
        interfaces = (relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains'],
            'code': ['exact'],
            'is_active': ['exact'],
        }


class VirtualCardNode(DjangoObjectType):
    """Virtual card node type."""
    masked_number = graphene.String()
    is_expired = graphene.Boolean()
    card_type_display = graphene.String()
    status_display = graphene.String()
    formatted_daily_limit = graphene.String()
    formatted_monthly_limit = graphene.String()
    formatted_per_transaction_limit = graphene.String()
    formatted_daily_usage = graphene.String()
    formatted_monthly_usage = graphene.String()
    formatted_total_usage = graphene.String()

    class Meta:
        model = VirtualCard
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'wallet': ['exact'],
            'card_brand': ['exact'],
            'card_type': ['exact'],
            'status': ['exact'],
            'is_active': ['exact'],
            'last_four': ['exact'],
        }

    def resolve_masked_number(self, info):
        return f"**** **** **** {self.last_four}" if self.last_four else ""

    def resolve_is_expired(self, info):
        return self.is_expired()

    def resolve_card_type_display(self, info):
        return dict(self.CARD_TYPES).get(self.card_type, self.card_type)

    def resolve_status_display(self, info):
        return dict(self.CARD_STATUS).get(self.status, self.status)

    def resolve_formatted_daily_limit(self, info):
        return f"₦{self.daily_limit:,.2f}"

    def resolve_formatted_monthly_limit(self, info):
        return f"₦{self.monthly_limit:,.2f}"

    def resolve_formatted_per_transaction_limit(self, info):
        return f"₦{self.per_transaction_limit:,.2f}"

    def resolve_formatted_daily_usage(self, info):
        return f"₦{self.daily_usage:,.2f}"

    def resolve_formatted_monthly_usage(self, info):
        return f"₦{self.monthly_usage:,.2f}"

    def resolve_formatted_total_usage(self, info):
        return f"₦{self.total_usage:,.2f}"


class CardTransactionNode(DjangoObjectType):
    """Card transaction node type."""
    formatted_amount = graphene.String()
    formatted_auth_amount = graphene.String()
    transaction_type_display = graphene.String()
    status_display = graphene.String()

    class Meta:
        model = CardTransaction
        interfaces = (relay.Node,)
        filter_fields = {
            'card': ['exact'],
            'user': ['exact'],
            'transaction_type': ['exact'],
            'status': ['exact'],
            'acquirer_reference': ['exact'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_formatted_auth_amount(self, info):
        if self.auth_amount:
            return f"₦{self.auth_amount:,.2f}"
        return None

    def resolve_transaction_type_display(self, info):
        return dict(self.TRANSACTION_TYPES).get(self.transaction_type, self.transaction_type)

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


class PhysicalCardNode(DjangoObjectType):
    """Physical card node type."""
    formatted_card_fee = graphene.String()
    formatted_shipping_fee = graphene.String()
    formatted_total_fee = graphene.String()
    delivery_status_display = graphene.String()

    class Meta:
        model = PhysicalCard
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'virtual_card': ['exact'],
            'delivery_status': ['exact'],
            'tracking_number': ['exact'],
        }

    def resolve_formatted_card_fee(self, info):
        return f"₦{self.card_fee:,.2f}"

    def resolve_formatted_shipping_fee(self, info):
        return f"₦{self.shipping_fee:,.2f}"

    def resolve_formatted_total_fee(self, info):
        return f"₦{self.total_fee:,.2f}"

    def resolve_delivery_status_display(self, info):
        return dict(self.DELIVERY_STATUS).get(self.delivery_status, self.delivery_status)

