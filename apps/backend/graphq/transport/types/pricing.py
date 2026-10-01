# graphql/transport/types/pricing.py

"""
GraphQL Nodes for Pricing Profiles and Receipts/Invoices.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.financial.pricing import PricingProfile
from invoice.models import Invoice


class PricingProfileNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Pricing Profile with full pricing details.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    is_current = Boolean(description="Whether this is the current active pricing")
    service_type_display = String(description="Human-readable service type display")
    base_fare_display = String(description="Formatted base fare")
    per_km_rate_display = String(description="Formatted per km rate")
    per_minute_rate_display = String(description="Formatted per minute rate")
    min_fare_display = String(description="Formatted minimum fare")
    surge_multiplier_display = String(description="Formatted surge multiplier")
    is_effective = Boolean(description="Whether pricing is currently effective")
    days_effective = Int(description="Number of days this pricing has been effective")
    
    class Meta:
        model = PricingProfile
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # String fields
            'service_type': ['exact'],
            
            # Numeric fields
            'base_fare': ['exact', 'gte', 'lte'],
            'per_km_rate': ['exact', 'gte', 'lte'],
            'per_minute_rate': ['exact', 'gte', 'lte', 'isnull'],
            'min_fare': ['exact', 'gte', 'lte'],
            'surge_multiplier': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_active': ['exact'],
            
            # Date fields
            'effective_from': ['exact', 'gte', 'lte'],
            'effective_to': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_is_current(self, info):
        """Resolve whether this is the current active pricing."""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.effective_from and self.effective_from > now:
            return False
        if self.effective_to and self.effective_to < now:
            return False
        
        # Check if there's a newer pricing profile
        newer = PricingProfile.objects.filter(
            service_type=self.service_type,
            is_active=True,
            effective_from__gt=self.effective_from,
            effective_from__lte=now
        ).exclude(
            Q(effective_to__isnull=False) & Q(effective_to__lt=now)
        ).exists()
        
        return not newer
    
    def resolve_service_type_display(self, info):
        """Resolve human-readable service type display."""
        return self.get_service_type_display()
    
    def resolve_base_fare_display(self, info):
        """Resolve formatted base fare."""
        return f"${self.base_fare:,.2f}"
    
    def resolve_per_km_rate_display(self, info):
        """Resolve formatted per km rate."""
        return f"${self.per_km_rate:,.2f}/km"
    
    def resolve_per_minute_rate_display(self, info):
        """Resolve formatted per minute rate."""
        if self.per_minute_rate is not None:
            return f"${self.per_minute_rate:,.2f}/min"
        return None
    
    def resolve_min_fare_display(self, info):
        """Resolve formatted minimum fare."""
        return f"${self.min_fare:,.2f}"
    
    def resolve_surge_multiplier_display(self, info):
        """Resolve formatted surge multiplier."""
        return f"{self.surge_multiplier}x"
    
    def resolve_is_effective(self, info):
        """Resolve whether pricing is currently effective."""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.effective_from and self.effective_from > now:
            return False
        if self.effective_to and self.effective_to < now:
            return False
        return True
    
    def resolve_days_effective(self, info):
        """Resolve number of days this pricing has been effective."""
        if not self.is_effective:
            return 0
        end_date = self.effective_to or timezone.now()
        return (end_date - self.effective_from).days
class ReceiptNode(OptimizedDjangoObjectType):
    """GraphQL node for Invoice."""

    # ---- Derived booleans ---------------------------------------------
    is_paid = Boolean()
    is_overdue = Boolean()
    is_draft = Boolean()
    is_sent = Boolean()
    is_verified = Boolean()

    # ---- Formatted displays -------------------------------------------
    total_display = String()
    subtotal_display = String()
    tax_display = String()
    balance_due_display = String()
    payment_status_display = String()
    days_overdue = Int()

    class Meta:
        model = Invoice
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # ---- Forward relations ------------------------------------
            "order": ["exact"],
            "booking": ["exact"],
            "customer": ["exact"],
            "customer__email": ["exact", "icontains"],
            "customer__first_name": ["exact", "icontains"],
            "customer__last_name": ["exact", "icontains"],
            "created_by": ["exact"],
            "sent_by": ["exact"],
            "verified_by": ["exact"],

            # ---- Identifiers ------------------------------------------
            "number": ["exact", "icontains"],
            "invoice_number": ["exact", "icontains"],
            "payment_reference": ["exact", "icontains"],

            # ---- Status / choices -------------------------------------
            "status": ["exact", "in"],
            "currency": ["exact"],
            "payment_method": ["exact", "icontains"],

            # ---- Financial amounts ------------------------------------
            "subtotal": ["exact", "gte", "lte", "lt", "gt"],
            "tax_amount": ["exact", "gte", "lte", "lt", "gt"],
            "discount_amount": ["exact", "gte", "lte", "lt", "gt"],
            "shipping_amount": ["exact", "gte", "lte", "lt", "gt"],
            "total_amount": ["exact", "gte", "lte", "lt", "gt"],
            "amount_paid": ["exact", "gte", "lte", "lt", "gt"],
            "balance_due": ["exact", "gte", "lte", "lt", "gt"],

            # ---- Billing info -----------------------------------------
            "billing_name": ["exact", "icontains"],
            "billing_email": ["exact", "icontains"],
            "billing_phone": ["exact", "icontains"],
            "billing_city": ["exact", "icontains"],
            "billing_state": ["exact", "icontains"],
            "billing_country": ["exact", "icontains"],
            "billing_zip": ["exact", "icontains"],

            # ---- Dates ------------------------------------------------
            "issue_date": ["exact", "gte", "lte", "lt", "gt"],
            "due_date": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "payment_date": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "sent_at": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "created": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }
       

    # ------------------------------------------------------------------
    # Resolvers
    # ------------------------------------------------------------------

    def resolve_is_paid(self, info):
        return self.status == "PAID"

    def resolve_is_overdue(self, info):
        if self.is_paid():
            return False
        if not self.due_date:
            return False
        from django.utils import timezone
        return timezone.now().date() > self.due_date

    def resolve_is_draft(self, info):
        return self.status == "DRAFT"

    def resolve_is_sent(self, info):
        return self.status == "SENT"

    def resolve_is_verified(self, info):
        return self.verified_by_id is not None

    def resolve_total_display(self, info):
        return f"{self.currency} {self.total_amount:,.2f}"

    def resolve_subtotal_display(self, info):
        return f"{self.currency} {self.subtotal:,.2f}"

    def resolve_tax_display(self, info):
        return f"{self.currency} {self.tax_amount:,.2f}"

    def resolve_balance_due_display(self, info):
        return f"{self.currency} {self.balance_due:,.2f}"

    def resolve_payment_status_display(self, info):
        return self.get_status_display()

    def resolve_days_overdue(self, info):
        if not self.is_overdue():
            return 0
        from django.utils import timezone
        return (timezone.now().date() - self.due_date).days