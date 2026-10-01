import graphene
from graphene import Decimal, String, relay
from graphene_django import DjangoObjectType

from banking.models.core import Bank, Account

from graphq.banking.filters import BankFilterSet


# ============================================================================
# CORE TYPES
# ============================================================================

class BankNode(DjangoObjectType):
    """Bank node type."""
    logo_url = graphene.String()

    class Meta:
        model = Bank
        interfaces = (relay.Node,)
        exclude = (
            "api_key_encrypted",
            "api_secret_encrypted",
        )
        filterset_class = BankFilterSet

    def resolve_logo_url(self, info):
        if self.logo and hasattr(self.logo, 'url'):
            return self.logo.url
        return None


class AccountNode(DjangoObjectType):
    """Account node type."""
    display_name = graphene.String()
    is_univa_account = graphene.Boolean()
    balance = graphene.Decimal()
    formatted_balance = graphene.String()

    class Meta:
        model = Account
        interfaces = (relay.Node,)
        filter_fields = {
            'account_name': ['exact', 'icontains'],
            'phone_number': ['exact'],
            'bank': ['exact'],
            'user': ['exact'],
            'nuban_number': ['exact', 'icontains'],
        }

    def resolve_display_name(self, info):
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.email
        return self.account_name or self.nuban_number

    def resolve_is_univa_account(self, info):
        return self.bank.is_virtual_provider if self.bank else True

    def resolve_balance(self, info):
        return self.get_balance()

    def resolve_formatted_balance(self, info):
        balance = self.get_balance()
        return f"₦{balance:,.2f}"

