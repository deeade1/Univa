"""
Test command to verify progressive enhancement
"""
from django.core.management.base import BaseCommand
from transport.models.core.service_request import ServiceRequest
from transport.services.dispatch import get_dispatcher, get_dispatch_health

class Command(BaseCommand):
    help = 'Test dispatch system with progressive enhancement'
    
    def handle(self, *args, **options):
        self.stdout.write("Testing Dispatch System...")
        
        # Check health
        health = get_dispatch_health()
        self.stdout.write(f"Health Status: {health}")
        
        # Get dispatcher
        dispatcher = get_dispatcher()
        self.stdout.write(f"Current Dispatcher: {type(dispatcher).__name__}")
        
        # Test with a sample request
        try:
            from transport.models.core.service_request import ServiceRequest
            from django.contrib.gis.geos import Point
            
            # Create a test request
            request = ServiceRequest.objects.create(
                service_type='taxi',
                status='requested',
                pickup_location=Point(0, 0),
                customer_id=1  # Replace with actual customer
            )
            
            # Try dispatch
            provider = dispatcher.dispatch_request(request)
            
            if provider:
                self.stdout.write(self.style.SUCCESS(f"✓ Dispatch successful! Provider: {provider.id}"))
            else:
                self.stdout.write(self.style.WARNING("⚠ No provider found"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Dispatch failed: {e}"))
        
        self.stdout.write("Test completed!")