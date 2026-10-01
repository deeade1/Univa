# ============================================================================
# RECONCILIATION TYPES
# ============================================================================
import graphene
from graphene import  String, relay
from graphene_django import DjangoObjectType

from banking.models.reconciliation import (
    ReconciliationMatch,
    ReconciliationRun,
    UnreconciledTransaction,
)

class ReconciliationRunNode(DjangoObjectType):
    """Reconciliation run node type."""
    status_display = graphene.String()
    formatted_total_transactions = graphene.String()
    formatted_matched_transactions = graphene.String()
    formatted_unmatched_transactions = graphene.String()
    formatted_total_discrepancy = graphene.String()
    match_rate = graphene.Float()
    duration_display = graphene.String()

    class Meta:
        model = ReconciliationRun
        interfaces = (relay.Node,)
        filter_fields = {
            'status': ['exact'],
            'run_date': ['exact', 'gt', 'gte', 'lt', 'lte'],
            'reference': ['exact'],
        }

    def resolve_status_display(self, info):
        return dict(self.RUN_STATUS).get(self.status, self.status)

    def resolve_formatted_total_transactions(self, info):
        return f"{self.total_transactions:,}"

    def resolve_formatted_matched_transactions(self, info):
        return f"{self.matched_transactions:,}"

    def resolve_formatted_unmatched_transactions(self, info):
        return f"{self.unmatched_transactions:,}"

    def resolve_formatted_total_discrepancy(self, info):
        return f"₦{self.total_discrepancy:,.2f}"

    def resolve_match_rate(self, info):
        if self.total_transactions > 0:
            return (self.matched_transactions / self.total_transactions) * 100
        return 0

    def resolve_duration_display(self, info):
        if self.duration_seconds:
            minutes = int(self.duration_seconds // 60)
            seconds = int(self.duration_seconds % 60)
            return f"{minutes}m {seconds}s"
        return "N/A"


class ReconciliationMatchNode(DjangoObjectType):
    """Reconciliation match node type."""
    formatted_internal_amount = graphene.String()
    formatted_external_amount = graphene.String()
    formatted_amount_difference = graphene.String()
    match_type_display = graphene.String()
    confidence_display = graphene.String()

    class Meta:
        model = ReconciliationMatch
        interfaces = (relay.Node,)
        filter_fields = {
            'reconciliation_run': ['exact'],
            'match_type': ['exact'],
            'float_account': ['exact'],
            'external_reference': ['exact'],
        }

    def resolve_formatted_internal_amount(self, info):
        return f"₦{self.internal_amount:,.2f}"

    def resolve_formatted_external_amount(self, info):
        return f"₦{self.external_amount:,.2f}"

    def resolve_formatted_amount_difference(self, info):
        return f"₦{self.amount_difference:,.2f}"

    def resolve_match_type_display(self, info):
        return dict(self.MATCH_TYPE).get(self.match_type, self.match_type)

    def resolve_confidence_display(self, info):
        return f"{self.match_confidence * 100:.0f}%"


class UnreconciledTransactionNode(DjangoObjectType):
    """Unreconciled transaction node type."""
    formatted_amount = graphene.String()
    source_display = graphene.String()
    resolution_status_display = graphene.String()

    class Meta:
        model = UnreconciledTransaction
        interfaces = (relay.Node,)
        filter_fields = {
            'reconciliation_run': ['exact'],
            'source': ['exact'],
            'resolution_status': ['exact'],
            'float_account': ['exact'],
            'transaction_reference': ['exact'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_source_display(self, info):
        return dict(self.SOURCE_CHOICES).get(self.source, self.source)

    def resolve_resolution_status_display(self, info):
        return dict(self.RESOLUTION_STATUS).get(self.resolution_status, self.resolution_status)

