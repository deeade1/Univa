# ============================================================================
# REGULATORY TYPES
# ============================================================================
import graphene
from graphene import Int, String, relay
from graphene_django import DjangoObjectType



from banking.models.regulatory import BVNVerification, CBNReport

class BVNVerificationNode(DjangoObjectType):
    """BVN verification node type."""
    verification_status_display = graphene.String()
    masked_bvn = graphene.String()
    can_attempt = graphene.Boolean()
    attempts_remaining = graphene.Int()

    class Meta:
        model = BVNVerification
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'verification_status': ['exact'],
            'bvn_number': ['exact'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_verification_status_display(self, info):
        return dict(self.VERIFICATION_STATUS).get(self.verification_status, self.verification_status)

    def resolve_masked_bvn(self, info):
        if self.bvn_number and len(self.bvn_number) >= 8:
            return f"******{self.bvn_number[-4:]}"
        return "******"

    def resolve_can_attempt(self, info):
        return self.can_attempt_verification()

    def resolve_attempts_remaining(self, info):
        return max(5 - self.verification_attempts, 0)


class CBNReportNode(DjangoObjectType):
    """CBN report node type."""
    report_type_display = graphene.String()
    status_display = graphene.String()
    formatted_reporting_period = graphene.String()

    class Meta:
        model = CBNReport
        interfaces = (relay.Node,)
        filter_fields = {
            'report_type': ['exact'],
            'status': ['exact'],
            'reporting_period': ['exact'],
        }

    def resolve_report_type_display(self, info):
        return dict(self.REPORT_TYPES).get(self.report_type, self.report_type)

    def resolve_status_display(self, info):
        return dict(self.REPORT_STATUS).get(self.status, self.status)

    def resolve_formatted_reporting_period(self, info):
        return self.reporting_period

