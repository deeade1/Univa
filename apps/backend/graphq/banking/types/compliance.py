# ============================================================================
# COMPLIANCE TYPES
# ============================================================================
import graphene
from graphene import Int, String, relay
from graphene_django import DjangoObjectType



from banking.models.compliance import (
    Webhook, 
    WebhookDelivery,
    CurrencyExchangeRate,
    Contact, 
    ATMCard,
    ATMTransaction,
    CardIssuance
)

class WebhookNode(DjangoObjectType):
    """Webhook node type."""
    event_type_display = graphene.String()

    class Meta:
        model = Webhook
        interfaces = (relay.Node,)
        filter_fields = {
            'event_type': ['exact'],
            'is_active': ['exact'],
            'url': ['exact', 'icontains'],
        }

    def resolve_event_type_display(self, info):
        return dict(self.EVENT_TYPES).get(self.event_type, self.event_type)


class WebhookDeliveryNode(DjangoObjectType):
    """Webhook delivery node type."""
    formatted_attempts = graphene.String()

    class Meta:
        model = WebhookDelivery
        interfaces = (relay.Node,)
        filter_fields = {
            'webhook': ['exact'],
            'delivered': ['exact'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_formatted_attempts(self, info):
        return f"{self.attempts} attempt(s)"


class CurrencyExchangeRateNode(DjangoObjectType):
    """Currency exchange rate node type."""
    formatted_rate = graphene.String()
    inverse_rate = graphene.Float()

    class Meta:
        model = CurrencyExchangeRate
        interfaces = (relay.Node,)
        filter_fields = {
            'base_currency': ['exact'],
            'target_currency': ['exact'],
        }

    def resolve_formatted_rate(self, info):
        return f"1 {self.base_currency} = {self.rate:,.4f} {self.target_currency}"

    def resolve_inverse_rate(self, info):
        return 1 / self.rate if self.rate != 0 else 0


class ContactNode(DjangoObjectType):
    """Contact node type."""
    full_name = graphene.String()
    phone_number = graphene.String()

    class Meta:
        model = Contact
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'account_number': ['exact', 'icontains'],
            'bank_name': ['exact', 'icontains'],
            'is_beneficiary': ['exact'],
        }

    def resolve_full_name(self, info):
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.email
        return "Unknown"

    def resolve_phone_number(self, info):
        if self.user:
            return getattr(self.user, 'phone_number', None)
        return None


class ATMCardNode(DjangoObjectType):
    """ATM card node type."""
    masked_number = graphene.String()
    expiry_month = graphene.Int()
    expiry_year = graphene.Int()
    card_type_display = graphene.String()
    status_display = graphene.String()

    class Meta:
        model = ATMCard
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'account': ['exact'],
            'card_type': ['exact'],
            'status': ['exact'],
        }

    def resolve_masked_number(self, info):
        if self.card_number and len(self.card_number) >= 4:
            return f"**** **** **** {self.card_number[-4:]}"
        return ""

    def resolve_expiry_month(self, info):
        return self.expiry_date.month if self.expiry_date else None

    def resolve_expiry_year(self, info):
        return self.expiry_date.year if self.expiry_date else None

    def resolve_card_type_display(self, info):
        return dict(self.CARD_TYPES).get(self.card_type, self.card_type)

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


class ATMTransactionNode(DjangoObjectType):
    """ATM transaction node type."""
    formatted_amount = graphene.String()
    transaction_type_display = graphene.String()
    status_display = graphene.String()
    location_map_url = graphene.String()

    class Meta:
        model = ATMTransaction
        interfaces = (relay.Node,)
        filter_fields = {
            'card': ['exact'],
            'account': ['exact'],
            'user': ['exact'],
            'transaction_type': ['exact'],
            'status': ['exact'],
            'created_at': ['exact', 'gte', 'lte'],
        }

    def resolve_formatted_amount(self, info):
        if self.amount:
            return f"₦{self.amount:,.2f}"
        return "N/A"

    def resolve_transaction_type_display(self, info):
        return dict(self.TRANSACTION_TYPES).get(self.transaction_type, self.transaction_type)

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def resolve_location_map_url(self, info):
        if self.location:
            return f"https://maps.google.com/?q={self.location}"
        return None


class CardIssuanceNode(DjangoObjectType):
    """Card issuance node type."""
    request_type_display = graphene.String()
    status_display = graphene.String()
    formatted_fee = graphene.String()

    class Meta:
        model = CardIssuance
        interfaces = (relay.Node,)
        filter_fields = {
            'card': ['exact'],
            'status': ['exact'],
            'tracking_number': ['exact'],
        }

    def resolve_request_type_display(self, info):
        return dict(self.REQUEST_TYPES).get(self.request_type, self.request_type)

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def resolve_formatted_fee(self, info):
        return f"₦{self.fee:,.2f}"

