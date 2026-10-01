# apps/backend/transport/services/accessibility_service.py
import logging

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Q

logger = logging.getLogger(__name__)

class AccessibilityService:
    """Service for handling accessibility requirements"""
    
    def __init__(self):
        self.supported_features = self.load_supported_features()
    
    def load_supported_features(self):
        """Load supported accessibility features"""
        return {
            'mobility': ['wheelchair', 'walker', 'cane', 'ramp', 'lift', 'kneeling'],
            'visual': ['large_print', 'audio_announcements', 'high_contrast', 'braille'],
            'hearing': ['visual_alerts', 'asl_support', 'hearing_loop'],
            'cognitive': ['simple_instructions', 'extra_time']
        }
    
    def find_accessible_vehicles(self, user_requirements, location, max_distance_km=10):
        """Find vehicles that match user's accessibility requirements"""
        try:
            accessible_vehicles = AccessibleVehicle.objects.filter(
                vehicle__is_active=True,
                vehicle__current_location__isnull=False
            )
            
            # Apply distance filter
            if location:
                point = Point(location['lng'], location['lat'], srid=4326)
                accessible_vehicles = accessible_vehicles.annotate(
                    distance=Distance('vehicle__current_location', point)
                ).filter(distance__lte=max_distance_km * 1000)  # Convert to meters
            
            # Build dynamic filters based on user requirements
            filters = Q()
            
            # Mobility requirements
            if user_requirements.mobility_type == 'wheelchair':
                filters &= Q(is_wheelchair_accessible=True)
            if user_requirements.requires_ramp:
                filters &= Q(has_ramp=True)
            if user_requirements.requires_kneeling_vehicle:
                filters &= Q(can_kneel=True)
            
            # Visual requirements
            if user_requirements.requires_audio_announcements:
                filters &= Q(has_audio_announcements=True)
            if user_requirements.requires_visual_alerts:
                filters &= Q(has_visual_alerts=True)
            
            # Apply filters
            accessible_vehicles = accessible_vehicles.filter(filters)
            
            return accessible_vehicles.order_by('distance')
            
        except Exception as e:
            logger.error(f"Error finding accessible vehicles: {str(e)}")
            return AccessibleVehicle.objects.none()
    
    def calculate_accessibility_score(self, vehicle, user_requirements):
        """Calculate how well a vehicle matches user requirements (0-100)"""
        score = 0
        total_possible = 0
        
        requirements_mapping = {
            'wheelchair_required': ('is_wheelchair_accessible', 10),
            'ramp_required': ('has_ramp', 8),
            'kneeling_required': ('can_kneel', 6),
            'audio_required': ('has_audio_announcements', 7),
            'visual_alerts_required': ('has_visual_alerts', 7),
        }
        
        for req_field, (vehicle_field, weight) in requirements_mapping.items():
            if getattr(user_requirements, req_field, False):
                total_possible += weight
                if getattr(vehicle, vehicle_field, False):
                    score += weight
        
        return (score / total_possible * 100) if total_possible > 0 else 100
    
    def validate_route_accessibility(self, route, user_requirements):
        """Validate if a route meets accessibility requirements"""
        issues = []
        
        # Check if all vehicles on route are accessible
        for vehicle in route.vehicles.all():
            if not self.vehicle_meets_requirements(vehicle, user_requirements):
                issues.append(f"Vehicle {vehicle.id} doesn't meet requirements")
        
        # Check stops accessibility
        for stop in route.stops.all():
            if not stop.is_accessible:
                issues.append(f"Stop {stop.name} is not accessible")
        
        return len(issues) == 0, issues

    def vehicle_meets_requirements(self, vehicle, user_requirements):
        """Check if a single vehicle meets user requirements"""
        try:
            accessible_vehicle = vehicle.accessibility_features
            
            # Check mobility requirements
            if (user_requirements.mobility_type == 'wheelchair' and 
                not accessible_vehicle.is_wheelchair_accessible):
                return False
            
            if (user_requirements.requires_ramp and 
                not accessible_vehicle.has_ramp):
                return False
                
            # Check sensory requirements
            if (user_requirements.requires_audio_announcements and 
                not accessible_vehicle.has_audio_announcements):
                return False
                
            return True
            
        except AccessibleVehicle.DoesNotExist:
            return False