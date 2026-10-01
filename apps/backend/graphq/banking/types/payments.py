# ============================================================================
# PAYMENTS TYPES
# ============================================================================
import graphene
from graphene import Decimal, Int, String, relay
from graphene_django import DjangoObjectType


from banking.models.payments import PaymentStat, Transaction, MoneyTransfer, Wallet

class TransactionNode(DjangoObjectType):
    """Transaction node type."""
    formatted_amount = graphene.String()
    type_display = graphene.String()
    status_display = graphene.String()
    account_owner_name = graphene.String()

    class Meta:
        model = Transaction
        interfaces = (relay.Node,)
        filter_fields = {
            'type': ['exact'],
            'amount': ['exact', 'gte', 'lte'],
            'status': ['exact'],
            'created_at': ['exact', 'gte', 'lte'],
            'reference': ['exact'],
            'account': ['exact'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_type_display(self, info):
        return dict(self.TRANSACTION_TYPES).get(self.type, self.type)

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def resolve_account_owner_name(self, info):
        if self.account and self.account.user:
            return f"{self.account.user.first_name} {self.account.user.last_name}".strip()
        return "Unknown"


class PaymentStatNode(DjangoObjectType):
    """Payment stat node type."""
    formatted_total_payments = graphene.String()
    formatted_last_transaction = graphene.String()
    formatted_daily_limit = graphene.String()
    formatted_monthly_limit = graphene.String()

    class Meta:
        model = PaymentStat
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'number_of_payments': ['exact', 'gt', 'gte', 'lt', 'lte'],
            'total_payments_amount': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_formatted_total_payments(self, info):
        return f"₦{self.total_payments_amount:,.2f}"

    def resolve_formatted_last_transaction(self, info):
        if self.last_transaction_amount:
            return f"₦{self.last_transaction_amount:,.2f}"
        return "N/A"

    def resolve_formatted_daily_limit(self, info):
        return f"₦{self.daily_limit:,.2f}"

    def resolve_formatted_monthly_limit(self, info):
        return f"₦{self.monthly_limit:,.2f}"


class MoneyTransferNode(DjangoObjectType):
    """Money transfer node type."""
    formatted_amount = graphene.String()
    sender_name = graphene.String()
    receiver_name = graphene.String()
    formatted_fee = graphene.String()
    status_display = graphene.String()

    class Meta:
        model = MoneyTransfer
        interfaces = (relay.Node,)
        filter_fields = {
            'reference': ['exact'],
            'amount': ['exact', 'gte', 'lte'],
            'status': ['exact'],
            'created_at': ['exact', 'gte', 'lte'],
            'sender': ['exact'],
            'receiver': ['exact'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_formatted_fee(self, info):
        return f"₦{self.fee:,.2f}"

    def resolve_sender_name(self, info):
        if self.sender:
            return f"{self.sender.first_name} {self.sender.last_name}".strip() or self.sender.email
        return "Unknown"

    def resolve_receiver_name(self, info):
        if self.receiver:
            return f"{self.receiver.first_name} {self.receiver.last_name}".strip() or self.receiver.email
        return "Unknown"

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

class WalletNode(DjangoObjectType):
    """Wallet node type."""

    balance = graphene.Decimal()
    formatted_balance = graphene.String()
    is_active = graphene.Boolean()
    has_balance = graphene.Boolean()
    remaining_daily_limit = graphene.Decimal()
    remaining_daily_transactions = graphene.Int()

    class Meta:
        model = Wallet
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'status': ['exact'],
            'wallet_reference': ['exact'],
        }

    def resolve_balance(self, info):
        return self.balance

    def resolve_formatted_balance(self, info):
        return f"₦{self.balance:,.2f}"

    def resolve_is_active(self, info):
        return self.is_active

    def resolve_has_balance(self, info):
        return self.has_balance

    def resolve_remaining_daily_limit(self, info):
        return self.remaining_daily_limit

    def resolve_remaining_daily_transactions(self, info):
        return self.remaining_daily_transactions