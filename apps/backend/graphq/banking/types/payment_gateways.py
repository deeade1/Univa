# ============================================================================
# PAYMENT GATEWAY TYPES
# ============================================================================
import graphene
from graphene import String, relay
from graphene_django import DjangoObjectType



from banking.models.payment_gateways import (
    PaymentGateway,
    USSDOperation,
    USSDSession,
)

class PaymentGatewayNode(DjangoObjectType):
    """Payment gateway node type."""
    provider_display = graphene.String()
    formatted_daily_limit = graphene.String()
    health_status = graphene.String()

    class Meta:
        model = PaymentGateway
        interfaces = (relay.Node,)
        exclude = ["_public_key", "_secret_key", "_encryption_key"]
        filter_fields = {
            'name': ['exact', 'icontains'],
            'provider': ['exact'],
            'is_active': ['exact'],
            'is_default': ['exact'],
        }

    def resolve_provider_display(self, info):
        return dict(self.PROVIDER_CHOICES).get(self.provider, self.provider)

    def resolve_formatted_daily_limit(self, info):
        return f"₦{self.daily_transaction_limit:,.2f}"

    def resolve_health_status(self, info):
        if not self.is_active:
            return "Inactive"
        if self.uptime_percentage >= 95:
            return "Healthy"
        return "Degraded"


class USSDSessionNode(DjangoObjectType):
    """USSD session node type."""
    is_expired = graphene.Boolean()
    time_since_created = graphene.String()
    time_since_last_activity = graphene.String()

    class Meta:
        model = USSDSession
        interfaces = (relay.Node,)
        filter_fields = {
            'phone_number': ['exact'],
            'user': ['exact'],
            'is_active': ['exact'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_is_expired(self, info):
        return self.is_expired()

    def resolve_time_since_created(self, info):
        from django.utils.timesince import timesince
        return timesince(self.created_at)

    def resolve_time_since_last_activity(self, info):
        from django.utils.timesince import timesince
        return timesince(self.last_activity)


class USSDOperationNode(DjangoObjectType):
    """USSD operation node type."""
    operation_type_display = graphene.String()

    class Meta:
        model = USSDOperation
        interfaces = (relay.Node,)
        filter_fields = {
            'session': ['exact'],
            'operation_type': ['exact'],
            'is_successful': ['exact'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_operation_type_display(self, info):
        return dict(self.OPERATION_TYPES).get(self.operation_type, self.operation_type)

