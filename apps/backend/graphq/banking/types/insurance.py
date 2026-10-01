# ============================================================================
# INSURANCE TYPES
# ============================================================================
import graphene
from graphene import Int, String, relay
from graphene_django import DjangoObjectType
from django.utils import timezone


from banking.models.insurance import (
    InsuranceClaim,
    InsurancePolicy,
    InsuranceProduct,
    InsuranceProvider,
)

class InsuranceProviderNode(DjangoObjectType):
    """Insurance provider node type."""
    is_active_display = graphene.String()

    class Meta:
        model = InsuranceProvider
        interfaces = (relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains'],
            'code': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_is_active_display(self, info):
        return "Active" if self.is_active else "Inactive"


class InsuranceProductNode(DjangoObjectType):
    """Insurance product node type."""
    insurance_type_display = graphene.String()
    payment_frequency_display = graphene.String()
    formatted_coverage_amount_min = graphene.String()
    formatted_coverage_amount_max = graphene.String()
    formatted_premium_min = graphene.String()
    formatted_premium_max = graphene.String()
    is_active_display = graphene.String()

    class Meta:
        model = InsuranceProduct
        interfaces = (relay.Node,)
        filter_fields = {
            'provider': ['exact'],
            'insurance_type': ['exact'],
            'is_active': ['exact'],
            'name': ['exact', 'icontains'],
        }

    def resolve_insurance_type_display(self, info):
        return dict(self.INSURANCE_TYPES).get(self.insurance_type, self.insurance_type)

    def resolve_payment_frequency_display(self, info):
        return self.payment_frequency.replace('_', ' ').title()

    def resolve_formatted_coverage_amount_min(self, info):
        return f"₦{self.coverage_amount_min:,.2f}"

    def resolve_formatted_coverage_amount_max(self, info):
        return f"₦{self.coverage_amount_max:,.2f}"

    def resolve_formatted_premium_min(self, info):
        return f"₦{self.premium_min:,.2f}"

    def resolve_formatted_premium_max(self, info):
        return f"₦{self.premium_max:,.2f}"

    def resolve_is_active_display(self, info):
        return "Active" if self.is_active else "Inactive"


class InsurancePolicyNode(DjangoObjectType):
    """Insurance policy node type."""
    formatted_coverage_amount = graphene.String()
    formatted_premium_amount = graphene.String()
    formatted_total_claimed = graphene.String()
    formatted_total_paid = graphene.String()
    status_display = graphene.String()
    is_active_policy = graphene.Boolean()
    is_expiring_soon = graphene.Boolean()
    days_until_expiry = graphene.Int()

    class Meta:
        model = InsurancePolicy
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'product': ['exact'],
            'status': ['exact'],
            'policy_number': ['exact'],
        }

    def resolve_formatted_coverage_amount(self, info):
        return f"₦{self.coverage_amount:,.2f}"

    def resolve_formatted_premium_amount(self, info):
        return f"₦{self.premium_amount:,.2f}"

    def resolve_formatted_total_claimed(self, info):
        return f"₦{self.total_claimed:,.2f}"

    def resolve_formatted_total_paid(self, info):
        return f"₦{self.total_paid:,.2f}"

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def resolve_is_active_policy(self, info):
        return self.is_active()

    def resolve_is_expiring_soon(self, info):
        return self.is_expiring_soon()

    def resolve_days_until_expiry(self, info):
        if self.status != "ACTIVE":
            return 0
        days_left = (self.end_date - timezone.now()).days
        return max(days_left, 0)


class InsuranceClaimNode(DjangoObjectType):
    """Insurance claim node type."""
    formatted_claim_amount = graphene.String()
    formatted_approved_amount = graphene.String()
    formatted_paid_amount = graphene.String()
    status_display = graphene.String()
    time_since_filed = graphene.String()

    class Meta:
        model = InsuranceClaim
        interfaces = (relay.Node,)
        filter_fields = {
            'policy': ['exact'],
            'user': ['exact'],
            'status': ['exact'],
            'claim_number': ['exact'],
        }

    def resolve_formatted_claim_amount(self, info):
        return f"₦{self.claim_amount:,.2f}"

    def resolve_formatted_approved_amount(self, info):
        if self.approved_amount:
            return f"₦{self.approved_amount:,.2f}"
        return "Pending"

    def resolve_formatted_paid_amount(self, info):
        return f"₦{self.paid_amount:,.2f}"

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def resolve_time_since_filed(self, info):
        from django.utils.timesince import timesince
        return timesince(self.filed_at)


