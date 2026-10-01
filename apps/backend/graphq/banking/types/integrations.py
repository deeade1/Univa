# ============================================================================
# INTEGRATIONS TYPES
# ============================================================================
import graphene
from graphene import String, relay
from graphene_django import DjangoObjectType
from banking.models.integrations import BankAPIIntegration, APITransactionLog


class BankAPIIntegrationNode(DjangoObjectType):
    """Bank API integration node type."""
    provider_display = graphene.String()
    formatted_max_amount = graphene.String()
    formatted_daily_amount_limit = graphene.String()
    health_status = graphene.String()

    class Meta:
        model = BankAPIIntegration
        interfaces = (relay.Node,)
        exclude = ["_api_key", "_secret_key"]
        filter_fields = {
            'name': ['exact', 'icontains'],
            'provider': ['exact'],
            'is_active': ['exact'],
            'is_default': ['exact'],
        }

    def resolve_provider_display(self, info):
        return dict(self.PROVIDER_CHOICES).get(self.provider, self.provider)

    def resolve_formatted_max_amount(self, info):
        return f"₦{self.max_amount_per_transaction:,.2f}"

    def resolve_formatted_daily_amount_limit(self, info):
        return f"₦{self.daily_amount_limit:,.2f}"

    def resolve_health_status(self, info):
        if not self.is_active:
            return "Inactive"
        if self.is_healthy():
            return "Healthy"
        return "Unhealthy"


class APITransactionLogNode(DjangoObjectType):
    """API transaction log node type."""
    formatted_duration = graphene.String()
    status_display = graphene.String()
    method_display = graphene.String()

    class Meta:
        model = APITransactionLog
        interfaces = (relay.Node,)
        filter_fields = {
            'integration': ['exact'],
            'is_successful': ['exact'],
            'http_status': ['exact'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
            'reference': ['exact'],
        }

    def resolve_formatted_duration(self, info):
        return f"{self.duration_ms:.0f}ms"

    def resolve_status_display(self, info):
        if self.is_successful:
            return "Success"
        return "Failed"

    def resolve_method_display(self, info):
        return self.method

