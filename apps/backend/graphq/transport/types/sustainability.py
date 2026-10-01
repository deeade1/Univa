# graphql/transport/types/sustainability.py

"""
GraphQL Nodes for Sustainability Profile and Carbon Credits.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.shared.sustainability import SustainabilityProfile, CarbonCredit
from transport.models.rides.trip import Trip




class SustainabilityProfileNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Sustainability Profile with sustainability tracking and goals.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    co2_reduction_progress = Float(description="Progress towards CO2 reduction goal as percentage")
    monthly_ride_progress = Float(description="Progress towards monthly ride goal as percentage")
    car_avoidance_progress = Float(description="Progress towards car avoidance goal as percentage")
    overall_sustainability_score = Float(description="Overall sustainability score (0-100)")
    is_on_track = Boolean(description="Whether user is on track with sustainability goals")
    co2_saved_equivalent = String(description="CO2 saved in human-readable equivalent")
    trees_equivalent = Float(description="Number of trees equivalent to CO2 saved")
    
    class Meta:
        model = SustainabilityProfile
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'user': ['exact'],
            'user__email': ['exact', 'icontains'],
            
            # Numeric fields
            'co2_reduction_goal_kg': ['exact', 'gte', 'lte'],
            'monthly_ride_goal': ['exact', 'gte', 'lte'],
            'car_avoidance_goal': ['exact', 'gte', 'lte'],
            'total_co2_saved_kg': ['exact', 'gte', 'lte'],
            'total_car_trips_avoided': ['exact', 'gte', 'lte'],
            'current_streak_days': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'prefer_electric_vehicles': ['exact'],
            'prefer_shared_rides': ['exact'],
            'offset_carbon_footprint': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_co2_reduction_progress(self, info):
        """Resolve progress towards CO2 reduction goal as percentage."""
        if self.co2_reduction_goal_kg and self.co2_reduction_goal_kg > 0:
            progress = (self.total_co2_saved_kg / self.co2_reduction_goal_kg) * 100
            return round(min(progress, 100), 1)
        return 0
    
    def resolve_monthly_ride_progress(self, info):
        """Resolve progress towards monthly ride goal as percentage."""
        if self.monthly_ride_goal and self.monthly_ride_goal > 0:
            # Get rides this month
            from django.utils import timezone
            from transport.models.trip.trip import Trip
            
            start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            rides_this_month = Trip.objects.filter(
                customer=self.user,
                created_at__gte=start_of_month,
                status=Trip.Status.COMPLETED
            ).count()
            
            progress = (rides_this_month / self.monthly_ride_goal) * 100
            return round(min(progress, 100), 1)
        return 0
    
    def resolve_car_avoidance_progress(self, info):
        """Resolve progress towards car avoidance goal as percentage."""
        if self.car_avoidance_goal and self.car_avoidance_goal > 0:
            progress = (self.total_car_trips_avoided / self.car_avoidance_goal) * 100
            return round(min(progress, 100), 1)
        return 0
    
    def resolve_overall_sustainability_score(self, info):
        """Resolve overall sustainability score (0-100)."""
        scores = []
        
        # CO2 reduction (40% weight)
        co2_progress = self.resolve_co2_reduction_progress(info)
        scores.append(co2_progress * 0.4)
        
        # Ride goal (30% weight)
        ride_progress = self.resolve_monthly_ride_progress(info)
        scores.append(ride_progress * 0.3)
        
        # Car avoidance (30% weight)
        car_progress = self.resolve_car_avoidance_progress(info)
        scores.append(car_progress * 0.3)
        
        # Streak bonus (up to 10 extra points)
        streak_bonus = min(self.current_streak_days * 0.5, 10)
        
        total = sum(scores) + streak_bonus
        return round(min(total, 100), 1)
    
    def resolve_is_on_track(self, info):
        """Resolve whether user is on track with sustainability goals."""
        overall_score = self.resolve_overall_sustainability_score(info)
        return overall_score >= 70
    
    def resolve_co2_saved_equivalent(self, info):
        """Resolve CO2 saved in human-readable equivalent."""
        co2_saved = self.total_co2_saved_kg
        if co2_saved >= 1000:
            return f"{co2_saved / 1000:.1f} tonnes CO₂"
        return f"{co2_saved:.1f} kg CO₂"
    
    def resolve_trees_equivalent(self, info):
        """Resolve number of trees equivalent to CO2 saved."""
        # Average tree absorbs ~22kg CO2 per year
        return round(self.total_co2_saved_kg / 22, 2)
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_user_details(self, info):
        """Resolve user who owns this profile."""
        return self.user
    
    def resolve_carbon_credits(self, info):
        """Resolve carbon credits earned."""
        return CarbonCredit.objects.filter(user=self.user).order_by('-transaction_date')
    
    def resolve_total_credits_earned(self, info):
        """Resolve total carbon credits earned."""
        result = CarbonCredit.objects.filter(
            user=self.user,
            transaction_type__in=['earned', 'purchased']
        ).aggregate(total=models.Sum('credits_amount'))
        return result['total'] or 0
    
    def resolve_total_credits_redeemed(self, info):
        """Resolve total carbon credits redeemed."""
        result = CarbonCredit.objects.filter(
            user=self.user,
            transaction_type='redeemed'
        ).aggregate(total=models.Sum('credits_amount'))
        return result['total'] or 0


class CarbonCreditNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Carbon Credit with transaction tracking.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    transaction_type_display = String(description="Human-readable transaction type display")
    is_earned = Boolean(description="Whether credit was earned")
    is_purchased = Boolean(description="Whether credit was purchased")
    is_redeemed = Boolean(description="Whether credit was redeemed")
    is_offset = Boolean(description="Whether credit was used for offset")
    is_verified_status = Boolean(description="Whether credit is verified")
    credits_display = String(description="Formatted credits amount")
   
    class Meta:
        model = CarbonCredit
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'user': ['exact'],
            'user__email': ['exact', 'icontains'],
            'ride': ['exact'],
            'ride__id': ['exact'],
            
            # String fields
            'transaction_type': ['exact'],
            'verification_code': ['exact', 'icontains', 'istartswith'],
            
            # Numeric fields
            'credits_amount': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_verified': ['exact'],
            
            # Date fields
            'transaction_date': ['exact', 'gte', 'lte'],
        }
        ordering = [
            '-transaction_date',
            '-id',
        ]
    
    def resolve_transaction_type_display(self, info):
        """Resolve human-readable transaction type display."""
        return dict(self._meta.model._meta.get_field('transaction_type').choices).get(
            self.transaction_type, self.transaction_type
        )
    
    def resolve_is_earned(self, info):
        """Resolve whether credit was earned."""
        return self.transaction_type == 'earned'
    
    def resolve_is_purchased(self, info):
        """Resolve whether credit was purchased."""
        return self.transaction_type == 'purchased'
    
    def resolve_is_redeemed(self, info):
        """Resolve whether credit was redeemed."""
        return self.transaction_type == 'redeemed'
    
    def resolve_is_offset(self, info):
        """Resolve whether credit was used for offset."""
        return self.transaction_type == 'offset'
    
    def resolve_is_verified_status(self, info):
        """Resolve whether credit is verified."""
        return self.is_verified
    
    def resolve_credits_display(self, info):
        """Resolve formatted credits amount."""
        return f"{self.credits_amount:.2f} credits"
    
    def resolve_user_details(self, info):
        """Resolve user who owns this credit."""
        return self.user
    
    def resolve_ride_details(self, info):
        """Resolve ride associated with this credit."""
        return self.ride

