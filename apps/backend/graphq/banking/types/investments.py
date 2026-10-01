# ============================================================================
# INVESTMENTS TYPES
# ============================================================================
import graphene
from graphene import Decimal, Int, String, relay
from graphene_django import DjangoObjectType
from django.utils import timezone


from banking.models.investments import Investment, InvestmentEarnings, InvestmentProduct


class InvestmentProductNode(DjangoObjectType):
    """Investment product node type."""
    product_type_display = graphene.String()
    risk_level_display = graphene.String()
    interest_frequency_display = graphene.String()
    formatted_min_investment = graphene.String()
    formatted_max_investment = graphene.String()
    formatted_interest_rate = graphene.String()
    formatted_management_fee = graphene.String()
    formatted_early_withdrawal_fee = graphene.String()
    formatted_total_invested = graphene.String()
    available_slots = graphene.Decimal()
    is_available_now = graphene.Boolean()

    class Meta:
        model = InvestmentProduct
        interfaces = (relay.Node,)
        filter_fields = {
            'product_type': ['exact'],
            'risk_level': ['exact'],
            'is_active': ['exact'],
            'is_available': ['exact'],
            'name': ['exact', 'icontains'],
        }

    def resolve_product_type_display(self, info):
        return dict(self.PRODUCT_TYPES).get(self.product_type, self.product_type)

    def resolve_risk_level_display(self, info):
        return dict(self.RISK_LEVELS).get(self.risk_level, self.risk_level)

    def resolve_interest_frequency_display(self, info):
        return dict(self.FREQUENCY_CHOICES).get(self.interest_frequency, self.interest_frequency)

    def resolve_formatted_min_investment(self, info):
        return f"₦{self.min_investment:,.2f}"

    def resolve_formatted_max_investment(self, info):
        if self.max_investment:
            return f"₦{self.max_investment:,.2f}"
        return "Unlimited"

    def resolve_formatted_interest_rate(self, info):
        return f"{self.interest_rate}%"

    def resolve_formatted_management_fee(self, info):
        return f"{self.management_fee}%"

    def resolve_formatted_early_withdrawal_fee(self, info):
        return f"{self.early_withdrawal_fee}%"

    def resolve_formatted_total_invested(self, info):
        return f"₦{self.total_invested:,.2f}"

    def resolve_available_slots(self, info):
        return self.available_slots

    def resolve_is_available_now(self, info):
        now = timezone.now()
        return (self.is_active and self.is_available and 
                self.available_from <= now and 
                (not self.available_until or self.available_until >= now))


class InvestmentNode(DjangoObjectType):
    """Investment node type."""
    formatted_amount = graphene.String()
    formatted_expected_return = graphene.String()
    formatted_actual_return = graphene.String()
    formatted_total_return = graphene.String()
    formatted_interest_paid = graphene.String()
    formatted_early_withdrawal_fee = graphene.String()
    status_display = graphene.String()
    progress_percentage = graphene.Decimal()
    days_remaining = graphene.Int()
    is_matured = graphene.Boolean()

    class Meta:
        model = Investment
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'product': ['exact'],
            'status': ['exact'],
            'investment_reference': ['exact'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_formatted_expected_return(self, info):
        return f"₦{self.expected_return:,.2f}"

    def resolve_formatted_actual_return(self, info):
        if self.actual_return:
            return f"₦{self.actual_return:,.2f}"
        return "Pending"

    def resolve_formatted_total_return(self, info):
        if self.total_return:
            return f"₦{self.total_return:,.2f}"
        return "Pending"

    def resolve_formatted_interest_paid(self, info):
        return f"₦{self.interest_paid:,.2f}"

    def resolve_formatted_early_withdrawal_fee(self, info):
        return f"₦{self.early_withdrawal_fee:,.2f}"

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def resolve_progress_percentage(self, info):
        if self.expected_return > 0:
            return (self.interest_paid / self.expected_return) * 100
        return 0

    def resolve_days_remaining(self, info):
        now = timezone.now()
        if now < self.maturity_date:
            return (self.maturity_date - now).days
        return 0

    def resolve_is_matured(self, info):
        return self.is_matured()


class InvestmentEarningsNode(DjangoObjectType):
    """Investment earnings node type."""
    formatted_amount = graphene.String()
    earning_type_display = graphene.String()

    class Meta:
        model = InvestmentEarnings
        interfaces = (relay.Node,)
        filter_fields = {
            'investment': ['exact'],
            'user': ['exact'],
            'earning_type': ['exact'],
            'paid_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_earning_type_display(self, info):
        return dict(self.EARNING_TYPES).get(self.earning_type, self.earning_type)

