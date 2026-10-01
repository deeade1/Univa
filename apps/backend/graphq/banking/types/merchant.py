# ============================================================================
# MERCHANT TYPES
# ============================================================================
import graphene
from graphene import Decimal, String, relay
from graphene_django import DjangoObjectType



from banking.models.merchant import Merchant, MerchantTransaction

class MerchantNode(DjangoObjectType):
    """Merchant node type."""
    merchant_type_display = graphene.String()
    verification_status_display = graphene.String()
    formatted_transaction_fee = graphene.String()
    formatted_daily_limit = graphene.String()
    formatted_monthly_limit = graphene.String()
    formatted_total_volume = graphene.String()
    formatted_avg_transaction = graphene.Decimal()

    class Meta:
        model = Merchant
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'business_name': ['exact', 'icontains'],
            'business_type': ['exact'],
            'verification_status': ['exact'],
            'is_active': ['exact'],
            'is_flagged': ['exact'],
        }

    def resolve_merchant_type_display(self, info):
        return dict(self.MERCHANT_TYPES).get(self.business_type, self.business_type)

    def resolve_verification_status_display(self, info):
        return dict(self.VERIFICATION_STATUS).get(self.verification_status, self.verification_status)

    def resolve_formatted_transaction_fee(self, info):
        return f"{self.transaction_fee_percentage}%"

    def resolve_formatted_daily_limit(self, info):
        return f"₦{self.daily_transaction_limit:,.2f}"

    def resolve_formatted_monthly_limit(self, info):
        return f"₦{self.monthly_transaction_limit:,.2f}"

    def resolve_formatted_total_volume(self, info):
        return f"₦{self.total_volume:,.2f}"

    def resolve_formatted_avg_transaction(self, info):
        if self.total_transactions > 0:
            return self.total_volume / self.total_transactions
        return 0


class MerchantTransactionNode(DjangoObjectType):
    """Merchant transaction node type."""
    formatted_amount = graphene.String()
    formatted_fee = graphene.String()
    formatted_net_amount = graphene.String()
    transaction_type_display = graphene.String()
    status_display = graphene.String()

    class Meta:
        model = MerchantTransaction
        interfaces = (relay.Node,)
        filter_fields = {
            'merchant': ['exact'],
            'customer': ['exact'],
            'transaction_type': ['exact'],
            'status': ['exact'],
            'reference': ['exact'],
            'is_settled': ['exact'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_formatted_fee(self, info):
        return f"₦{self.fee:,.2f}"

    def resolve_formatted_net_amount(self, info):
        return f"₦{self.net_amount:,.2f}"

    def resolve_transaction_type_display(self, info):
        return dict(self.TRANSACTION_TYPES).get(self.transaction_type, self.transaction_type)

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

