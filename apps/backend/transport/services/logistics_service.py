import logging

from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class LogisticsService:
    """Main logistics service class"""
    
    def __init__(self):
        self.pricing_service = None
        self.routing_service = None
        self.tracking_service = None
        
        try:
            from ..services.pricing import PricingService
            from ..services.routing import RoutingService
            from ..services.tracking import TrackingService
            self.pricing_service = PricingService()
            self.routing_service = RoutingService()
            self.tracking_service = TrackingService()
        except ImportError:
            logger.warning("Logistics services not available")

    def create_shipment(self, shipment_data):
        """Create a new shipment"""
        try:
            self._validate_shipment_data(shipment_data)
            
            # Calculate pricing
            price_quote = (self.pricing_service.calculate_shipment_price(shipment_data) 
                          if self.pricing_service else self._fallback_pricing(shipment_data))
            
            # Optimize route
            optimal_route = (self.routing_service.optimize_delivery_route(shipment_data) 
                            if self.routing_service else self._fallback_route(shipment_data))
            
            # Create shipment record
            shipment = Delivery.objects.create(
                **shipment_data,
                estimated_distance=optimal_route['distance'],
                estimated_duration=optimal_route['duration'],
                total_fare=price_quote['total']
            )
            
            return {
                'shipment': shipment,
                'price_quote': price_quote,
                'estimated_delivery': optimal_route['eta']
            }
            
        except Exception as e:
            logger.error(f"Shipment creation failed: {e}")
            raise
    
    def _validate_shipment_data(self, shipment_data):
        """Validate shipment data"""
        required_fields = ['package_description', 'package_weight', 'recipient_name', 'recipient_phone']
        for field in required_fields:
            if field not in shipment_data:
                raise ValueError(f"Missing required field: {field}")
    
    def _fallback_pricing(self, shipment_data):
        """Fallback pricing calculation"""
        base_rate = 5.00
        distance_rate = 2.50
        weight_rate = 1.50
        
        distance_cost = shipment_data.get('distance_km', 0) * distance_rate
        weight_cost = shipment_data.get('package_weight', 0) * weight_rate
        
        total = base_rate + distance_cost + weight_cost
        
        return {
            'base_fare': base_rate,
            'distance_fare': distance_cost,
            'weight_fare': weight_cost,
            'total': round(total, 2)
        }
    
    def _fallback_route(self, shipment_data):
        """Fallback route optimization"""
        from django.utils import timezone
        return {
            'distance': shipment_data.get('distance_km', 0),
            'duration': shipment_data.get('estimated_duration', 0),
            'eta': timezone.now() + timezone.timedelta(hours=1)
        }