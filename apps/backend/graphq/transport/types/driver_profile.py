# graphql/transport/types/driver_profile.py

"""
GraphQL Node for Driver Profile with full driver management capabilities.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime, Date
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.driver_profile import DriverProfile
from transport.models.financial.earnings import DriverEarning, IncentiveProgram
from transport.models.core.service_provider import ServiceProviderProfile
from transport.models.core.service_request import ServiceRequest
from transport.models.rating.ratings import ProviderRating




class DriverProfileNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Driver Profile with full driver information and analytics.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Status checks
    has_license = Boolean(description="Whether driver has a license")
    has_insurance = Boolean(description="Whether driver has insurance")
    has_vehicle = Boolean(description="Whether driver has a vehicle")
    is_fully_verified = Boolean(description="Whether driver is fully verified")
    insurance_is_valid = Boolean(description="Whether insurance is still valid")
    insurance_days_remaining = Int(description="Days remaining until insurance expires")
    
    # Display fields
    display_name = String(description="Driver display name")
    vehicle_display = String(description="Vehicle display string")
    license_display = String(description="License number with masking")
    # Earnings and financials
    total_earnings = Float(description="Total earnings")
    pending_earnings = Float(description="Pending earnings")
    paid_earnings = Float(description="Paid earnings")
    
    average_rating = Float(description="Average rating")
    rating_count = Int(description="Total number of ratings")
    
    service_count = Int(description="Total service count")
    completion_rate = Float(description="Service completion rate")
    
    class Meta:
        model = DriverProfile
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'profile': ['exact'],
            'profile__email': ['exact', 'icontains'],
            'profile__first_name': ['exact', 'icontains'],
            'profile__last_name': ['exact', 'icontains'],
            
            # String fields
            'license_number': ['exact', 'icontains', 'istartswith'],
            'vehicle_type': ['exact', 'icontains'],
            'vehicle_plate': ['exact', 'icontains'],
            'vehicle_make': ['exact', 'icontains'],
            'vehicle_model': ['exact', 'icontains'],
            'insurance_provider': ['exact', 'icontains'],
            
            # Numeric fields
            'vehicle_year': ['exact', 'gte', 'lte', 'isnull'],
            
            # Date fields
            'insurance_expiry': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_has_license(self, info):
        """Resolve whether driver has a license."""
        return bool(self.license_number) and bool(self.license_image)
    
    def resolve_has_insurance(self, info):
        """Resolve whether driver has insurance."""
        return bool(self.insurance_provider) and self.insurance_expiry is not None
    
    def resolve_has_vehicle(self, info):
        """Resolve whether driver has a vehicle."""
        return bool(self.vehicle_type) or bool(self.vehicle_plate)
    
    def resolve_is_fully_verified(self, info):
        """Resolve whether driver is fully verified."""
        return all([
            self.has_license,
            self.has_insurance,
            self.has_vehicle,
            self.insurance_is_valid,
        ])
    
    def resolve_insurance_is_valid(self, info):
        """Resolve whether insurance is still valid."""
        if not self.insurance_expiry:
            return False
        from django.utils import timezone
        return self.insurance_expiry >= timezone.now().date()
    
    def resolve_insurance_days_remaining(self, info):
        """Resolve days remaining until insurance expires."""
        if not self.insurance_expiry:
            return None
        from django.utils import timezone
        now = timezone.now().date()
        if self.insurance_expiry < now:
            return 0
        return (self.insurance_expiry - now).days
    
    def resolve_display_name(self, info):
        """Resolve driver display name."""
        if self.profile:
            return self.profile.get_full_name() or self.profile.email
        return f"Driver #{self.id}"
    
    def resolve_vehicle_display(self, info):
        """Resolve vehicle display string."""
        parts = []
        if self.vehicle_make:
            parts.append(self.vehicle_make)
        if self.vehicle_model:
            parts.append(self.vehicle_model)
        if self.vehicle_year:
            parts.append(str(self.vehicle_year))
        if self.vehicle_plate:
            parts.append(f"({self.vehicle_plate})")
        return " ".join(parts) if parts else "No vehicle"
    
    def resolve_license_display(self, info):
        """Resolve license number with masking."""
        if self.license_number and len(self.license_number) > 4:
            return f"****{self.license_number[-4:]}"
        return self.license_number or "No license"
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_user_details(self, info):
        """Resolve user who owns this driver profile."""
        return self.profile
    
    def resolve_service_provider_details(self, info):
        """Resolve service provider profile."""
        return getattr(self.profile, 'service_provider', None) if self.profile else None
    
    def resolve_vehicle_details(self, info):
        """Resolve vehicle associated with this driver."""
        if self.profile and hasattr(self.profile, 'service_provider'):
            provider = self.profile.service_provider
            if provider and hasattr(provider, 'vehicle'):
                return provider.vehicle
        return None
    
    def resolve_earnings(self, info):
        """Resolve driver earnings history."""
        if self.profile and hasattr(self.profile, 'service_provider'):
            provider = self.profile.service_provider
            if provider:
                return DriverEarning.objects.filter(driver=provider).order_by('-period_start')
        return []
    
    def resolve_total_earnings(self, info):
        """Resolve total earnings."""
        earnings = self.resolve_earnings(info)
        if earnings:
            result = earnings.aggregate(total=models.Sum('net_earnings'))
            return result['total'] or 0
        return 0
    
    def resolve_pending_earnings(self, info):
        """Resolve pending earnings."""
        earnings = self.resolve_earnings(info)
        if earnings:
            result = earnings.filter(
                payout_status=DriverEarning.PayoutStatus.PENDING
            ).aggregate(total=models.Sum('net_earnings'))
            return result['total'] or 0
        return 0
    
    def resolve_paid_earnings(self, info):
        """Resolve paid earnings."""
        earnings = self.resolve_earnings(info)
        if earnings:
            result = earnings.filter(
                payout_status=DriverEarning.PayoutStatus.PAID
            ).aggregate(total=models.Sum('net_earnings'))
            return result['total'] or 0
        return 0
    
    def resolve_ratings(self, info):
        """Resolve provider ratings."""
        if self.profile and hasattr(self.profile, 'service_provider'):
            provider = self.profile.service_provider
            if provider:
                return ProviderRating.objects.filter(provider=provider).order_by('-created_at')
        return []
    
    def resolve_average_rating(self, info):
        """Resolve average rating."""
        ratings = self.resolve_ratings(info)
        if ratings:
            result = ratings.aggregate(avg=models.Avg('overall_rating'))
            return round(result['avg'] or 0, 2)
        return 0
    
    def resolve_rating_count(self, info):
        """Resolve total number of ratings."""
        ratings = self.resolve_ratings(info)
        return ratings.count() if ratings else 0
    
    def resolve_recent_services(self, info):
        """Resolve recent services."""
        if self.profile and hasattr(self.profile, 'service_provider'):
            provider = self.profile.service_provider
            if provider:
                return ServiceRequest.objects.filter(
                    provider=provider
                ).order_by('-created_at')[:10]
        return []
    
    def resolve_active_services(self, info):
        """Resolve active services."""
        if self.profile and hasattr(self.profile, 'service_provider'):
            provider = self.profile.service_provider
            if provider:
                return ServiceRequest.objects.filter(
                    provider=provider,
                    status__in=[
                        ServiceRequest.Status.REQUESTED,
                        ServiceRequest.Status.ACCEPTED,
                        ServiceRequest.Status.IN_PROGRESS,
                        ServiceRequest.Status.SCHEDULED,
                    ]
                ).order_by('-created_at')
        return []
    
    def resolve_service_count(self, info):
        """Resolve total service count."""
        if self.profile and hasattr(self.profile, 'service_provider'):
            provider = self.profile.service_provider
            if provider:
                return ServiceRequest.objects.filter(provider=provider).count()
        return 0
    
    def resolve_completion_rate(self, info):
        """Resolve service completion rate."""
        if self.profile and hasattr(self.profile, 'service_provider'):
            provider = self.profile.service_provider
            if provider:
                total = ServiceRequest.objects.filter(provider=provider).count()
                if total > 0:
                    completed = ServiceRequest.objects.filter(
                        provider=provider,
                        status=ServiceRequest.Status.COMPLETED
                    ).count()
                    return round((completed / total) * 100, 1)
        return 0
