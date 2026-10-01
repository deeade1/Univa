# ============================================================================
# SCHEDULED TYPES
# ============================================================================
import graphene
from graphene import Decimal,  Int,  String, relay
from graphene_django import DjangoObjectType
from django.utils import timezone

from banking.models.scheduled import (
    APIKey,
    CreditProduct,
    ExchangeRate,
    InternationalTransfer,
    RemittanceProvider,
    ScheduledPayment,
    SupportTicket,
)

class ScheduledPaymentNode(DjangoObjectType):
    """Scheduled payment node type."""
    frequency_display = graphene.String()
    formatted_amount = graphene.String()
    is_active_display = graphene.String()
    days_until_next = graphene.Int()

    class Meta:
        model = ScheduledPayment
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'source_account': ['exact'],
            'frequency': ['exact'],
            'is_active': ['exact'],
            'beneficiary_account': ['exact'],
        }

    def resolve_frequency_display(self, info):
        return dict(self.FREQUENCY_CHOICES).get(self.frequency, self.frequency)

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_is_active_display(self, info):
        return "Active" if self.is_active else "Inactive"

    def resolve_days_until_next(self, info):
        now = timezone.now()
        if now < self.next_processing:
            return (self.next_processing - now).days
        return 0


class CreditProductNode(DjangoObjectType):
    """Credit product node type."""
    product_type_display = graphene.String()
    formatted_min_amount = graphene.String()
    formatted_max_amount = graphene.String()
    formatted_interest_rate = graphene.String()

    class Meta:
        model = CreditProduct
        interfaces = (relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains'],
            'product_type': ['exact'],
        }

    def resolve_product_type_display(self, info):
        return dict(self.PRODUCT_TYPES).get(self.product_type, self.product_type)

    def resolve_formatted_min_amount(self, info):
        return f"₦{self.min_amount:,.2f}"

    def resolve_formatted_max_amount(self, info):
        return f"₦{self.max_amount:,.2f}"

    def resolve_formatted_interest_rate(self, info):
        return f"{self.interest_rate}%"


class SupportTicketNode(DjangoObjectType):
    """Support ticket node type."""
    priority_display = graphene.String()
    status_display = graphene.String()
    time_since_created = graphene.String()

    class Meta:
        model = SupportTicket
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'assigned_to': ['exact'],
            'status': ['exact'],
            'priority': ['exact'],
            'ticket_id': ['exact'],
        }

    def resolve_priority_display(self, info):
        return dict(self.PRIORITY_CHOICES).get(self.priority, self.priority)

    def resolve_status_display(self, info):
        return self.status

    def resolve_time_since_created(self, info):
        from django.utils.timesince import timesince
        return timesince(self.created_at)


class APIKeyNode(DjangoObjectType):
    """API key node type."""
    masked_key = graphene.String()
    permissions_display = graphene.String()
    is_active_display = graphene.String()

    class Meta:
        model = APIKey
        interfaces = (relay.Node,)
        exclude = ["secret"]
        filter_fields = {
            'merchant': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_masked_key(self, info):
        if self.key and len(self.key) >= 8:
            return f"{self.key[:6]}...{self.key[-4:]}"
        return "****"

    def resolve_permissions_display(self, info):
        return ", ".join(self.permissions) if self.permissions else "None"

    def resolve_is_active_display(self, info):
        return "Active" if self.is_active else "Inactive"


class RemittanceProviderNode(DjangoObjectType):
    """Remittance provider node type."""
    provider_display = graphene.String()
    formatted_min_amount = graphene.String()
    formatted_max_amount = graphene.String()
    formatted_daily_limit = graphene.String()
    formatted_exchange_margin = graphene.String()

    class Meta:
        model = RemittanceProvider
        interfaces = (relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains'],
            'provider_code': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_provider_display(self, info):
        return dict(self.PROVIDER_CHOICES).get(self.provider_code, self.provider_code)

    def resolve_formatted_min_amount(self, info):
        return f"₦{self.min_amount:,.2f}"

    def resolve_formatted_max_amount(self, info):
        return f"₦{self.max_amount:,.2f}"

    def resolve_formatted_daily_limit(self, info):
        return f"₦{self.daily_limit:,.2f}"

    def resolve_formatted_exchange_margin(self, info):
        return f"{self.exchange_margin}%"


class InternationalTransferNode(DjangoObjectType):
    """International transfer node type."""
    formatted_source_amount = graphene.String()
    formatted_target_amount = graphene.String()
    formatted_exchange_rate = graphene.String()
    formatted_provider_fee = graphene.String()
    formatted_platform_fee = graphene.String()
    formatted_total_fee = graphene.String()
    transfer_type_display = graphene.String()
    status_display = graphene.String()
    payout_method_display = graphene.String()

    class Meta:
        model = InternationalTransfer
        interfaces = (relay.Node,)
        filter_fields = {
            'sender': ['exact'],
            'recipient': ['exact'],
            'provider': ['exact'],
            'transfer_type': ['exact'],
            'status': ['exact'],
            'reference': ['exact'],
        }

    def resolve_formatted_source_amount(self, info):
        return f"{self.source_amount:,.2f} {self.source_currency}"

    def resolve_formatted_target_amount(self, info):
        return f"{self.target_amount:,.2f} {self.target_currency}"

    def resolve_formatted_exchange_rate(self, info):
        return f"1 {self.source_currency} = {self.exchange_rate:.4f} {self.target_currency}"

    def resolve_formatted_provider_fee(self, info):
        return f"₦{self.provider_fee:,.2f}"

    def resolve_formatted_platform_fee(self, info):
        return f"₦{self.platform_fee:,.2f}"

    def resolve_formatted_total_fee(self, info):
        return f"₦{self.total_fee:,.2f}"

    def resolve_transfer_type_display(self, info):
        return dict(self.TRANSFER_TYPES).get(self.transfer_type, self.transfer_type)

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def resolve_payout_method_display(self, info):
        return dict(self.PAYOUT_METHODS).get(self.payout_method, self.payout_method)


class ExchangeRateNode(DjangoObjectType):
    """Exchange rate node type."""
    formatted_buy_rate = graphene.String()
    formatted_sell_rate = graphene.String()
    formatted_mid_rate = graphene.String()
    spread = graphene.Decimal()
    is_active_display = graphene.String()

    class Meta:
        model = ExchangeRate
        interfaces = (relay.Node,)
        filter_fields = {
            'base_currency': ['exact'],
            'target_currency': ['exact'],
            'provider': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_formatted_buy_rate(self, info):
        return f"{self.buy_rate:.4f}"

    def resolve_formatted_sell_rate(self, info):
        return f"{self.sell_rate:.4f}"

    def resolve_formatted_mid_rate(self, info):
        return f"{self.mid_rate:.4f}"

    def resolve_spread(self, info):
        return self.sell_rate - self.buy_rate

    def resolve_is_active_display(self, info):
        return "Active" if self.is_active else "Inactive"

