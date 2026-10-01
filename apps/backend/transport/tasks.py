'''import logging
import asyncio
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from celery import shared_task
from geopy.distance import geodesic
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from twilio.rest import Client

# Models
from .models import (
    ServiceProviderProfile, ServiceRequest, Vehicle, Trip, Delivery,
    SharedTrip, WaitlistEntry, Booking, Tracking, TrackingEvent,
    PricingProfile, TripScheduleTemplate, BoardingTicket
)

# Services
from transport.services import prediction, pricing, seat_reallocation
from graphq.transport.dispatch import EnhancedUnifiedDispatcher

logger = logging.getLogger('transport.tasks')
channel_layer = get_channel_layer()

# ==============================================
# Utility Functions
# ==============================================

def publish_trip_update(trip_id, payload):
    """Publish trip update via WebSocket"""
    try:
        async_to_sync(channel_layer.group_send)(
            f"trip_{trip_id}",
            {
                "type": "trip.update",
                "payload": payload,
            },
        )
    except Exception as e:
        logger.error(f"Failed to publish trip update: {str(e)}")

def calculate_eta(request):
    """Calculate estimated time of arrival"""
    return timezone.now() + timedelta(minutes=15)

def calculate_estimated_completion(request):
    """Calculate estimated completion time for tracking"""
    return timezone.now() + timedelta(minutes=request.estimated_duration) if request.estimated_duration else None

def generate_tracking_number(request):
    """Generate unique tracking number"""
    import secrets
    import string
    rand_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"{request.service_type[:3].upper()}-{request.id}-{rand_part}"

# ==============================================
# Trip Scheduling Tasks
# ==============================================

@shared_task
def instantiate_daily_schedules():
    """Create trips from templates for the next 7 days"""
    today = timezone.now().date()
    templates = TripScheduleTemplate.objects.filter(active=True)
    created = []
    
    for template in templates:
        for delta in range(1, 8):
            date = today + timedelta(days=delta)
            if date.weekday() in (template.days_of_week or []):
                exists = Trip.objects.filter(
                    departure_city=template.departure_city,
                    destination_city=template.destination_city,
                    departure_time__date=date,
                ).exists()
                
                if not exists:
                    trip = template.instantiate_for_date(date)
                    created.append(str(trip.id))
    
    logger.info(f"Created {len(created)} daily schedules")
    return {"created": created}

@shared_task
def handle_seat_open(trip_id):
    """Notify waitlist when seats become available"""
    try:
        trip = Trip.objects.get(id=trip_id)
        entries = trip.waitlist_entries.filter(notified=False).order_by("created_at")[:trip.available_seats or 1]
        notified = []
        
        for entry in entries:
            entry.notify()
            notified.append(str(entry.id))
        
        publish_trip_update(trip_id, {
            "type": "trip.seats_open", 
            "available_seats": trip.available_seats
        })
        
        return {"notified": notified}
    except Trip.DoesNotExist:
        logger.error(f"Trip {trip_id} not found")
    except Exception as e:
        logger.error(f"Error in handle_seat_open: {str(e)}")

# ==============================================
# Dispatch & Service Request Tasks
# ==============================================

@shared_task(bind=True, max_retries=3)
def dispatch_service_request(self, request_id):
    """Assign the best available provider to a service request"""
    try:
        request = ServiceRequest.objects.get(id=request_id)
        
        # Skip if already assigned or cancelled
        if request.provider or request.status == ServiceRequest.Status.CANCELLED:
            return
        
        # Find available providers within radius
        providers = ServiceProviderProfile.objects.filter(
            is_available=True,
            is_online=True,
            provider_type=(
                'driver' if request.service_type in ['taxi', 'shared'] 
                else 'courier'
            ),
            location__distance_lte=(request.pickup_location, 10000)
        ).annotate_distance(request.pickup_location).order_by('distance')
        
        # Filter by requirements
        if request.service_type == 'taxi':
            providers = providers.filter(
                current_vehicle__category__in=['taxi', 'dual'],
                current_vehicle__passenger_capacity__gte=request.rider_count
            )
        elif request.service_type == 'delivery':
            providers = providers.filter(
                current_vehicle__category__in=['logistics', 'dual'],
                current_vehicle__cargo_capacity__gte=request.package_weight
            )
        
        # Assign nearest provider
        for provider in providers[:5]:
            try:
                with transaction.atomic():
                    provider.is_available = False
                    provider.current_service = request
                    provider.save()
                    
                    request.provider = provider
                    request.vehicle = provider.current_vehicle
                    request.status = ServiceRequest.Status.ACCEPTED
                    request.save()
                    
                    # Send notifications
                    notify_provider_assignment.delay(request.id)
                    notify_customer_assignment.delay(request.id)
                    create_tracking_record.delay(request.id)
                    
                    return
            except Exception as e:
                logger.error(f"Failed to assign provider {provider.id}: {str(e)}")
                continue
        
        # Retry if no providers found
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        else:
            logger.warning(f"Failed to dispatch request {request_id} after retries")
            
    except ServiceRequest.DoesNotExist:
        logger.error(f"Service request {request_id} not found")
    except Exception as e:
        logger.error(f"Error in dispatch_service_request: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

@shared_task
def batch_dispatch_requests():
    """Process pending service requests in batches"""
    try:
        pending_requests = ServiceRequest.objects.filter(
            status=ServiceRequest.Status.REQUESTED
        ).order_by('created_at')[:50]
        
        for request in pending_requests:
            dispatch_service_request.delay(request.id)
            
    except Exception as e:
        logger.error(f"Error in batch_dispatch_requests: {str(e)}")

# ==============================================
# Notification Tasks
# ==============================================

@shared_task
def notify_provider_assignment(request_id):
    """Notify provider about new assignment"""
    try:
        request = ServiceRequest.objects.get(id=request_id)
        provider = request.provider
        
        notification_data = {
            'type': 'new_assignment',
            'request_id': str(request.id),
            'service_type': request.service_type,
            'pickup_address': request.pickup_address,
            'estimated_distance': request.estimated_distance,
            'estimated_duration': request.estimated_duration,
            'total_fare': str(request.total_fare) if request.total_fare else None
        }
        
        # WebSocket notification
        async_to_sync(channel_layer.group_send)(
            f"provider_{provider.user.id}",
            {
                "type": "provider.notification",
                "notification": notification_data
            }
        )
        
        # Push notification
        if provider.user.notification_preferences.push_notifications:
            send_push_notification.delay(
                provider.user.id,
                "New Service Assignment",
                f"You have a new {request.get_service_type_display()} request",
                notification_data
            )
            
    except Exception as e:
        logger.error(f"Error in notify_provider_assignment: {str(e)}")

@shared_task
def notify_customer_assignment(request_id):
    """Notify customer about provider assignment"""
    try:
        request = ServiceRequest.objects.get(id=request_id)
        
        notification_data = {
            'type': 'provider_assigned',
            'request_id': str(request.id),
            'provider_name': request.provider.user.get_full_name(),
            'provider_rating': str(request.provider.rating),
            'vehicle_info': str(request.vehicle),
            'estimated_arrival': calculate_eta(request)
        }
        
        # WebSocket notification
        async_to_sync(channel_layer.group_send)(
            f"customer_{request.customer.id}",
            {
                "type": "customer.notification",
                "notification": notification_data
            }
        )
        
        # Email notification
        if request.customer.notification_preferences.email_notifications:
            queue_email_notification.delay(
                request.customer.id,
                notification_data
            )
            
    except Exception as e:
        logger.error(f"Error in notify_customer_assignment: {str(e)}")

@shared_task
def send_seat_available_notification(user_id, trip_id):
    """Send seat available notification"""
    try:
        from accounts.models import UserProfile
        user = UserProfile.objects.get(id=user_id)
        trip = ServiceRequest.objects.get(id=trip_id)
        shared_trip = trip.shared_info
        
        notification_data = {
            'type': 'seat_available',
            'trip_id': str(trip.id),
            'pickup_address': trip.pickup_address,
            'dropoff_address': trip.dropoff_address,
            'available_seats': shared_trip.available_seats,
            'departure_time': str(trip.started_at),
            'price': str(trip.total_fare)
        }
        
        # WebSocket notification
        async_to_sync(channel_layer.group_send)(
            f"customer_{user.id}",
            {
                "type": "customer.notification",
                "notification": notification_data
            }
        )
        
        # Email notification
        if user.notification_preferences.email_notifications:
            queue_email_notification.delay(user.id, notification_data)
            
        # SMS notification
        if (user.notification_preferences.sms_notifications and 
            user.notification_preferences.phone_number):
            queue_sms_notification.delay(
                user.notification_preferences.phone_number,
                notification_data
            )
            
    except Exception as e:
        logger.error(f"Error in send_seat_available_notification: {str(e)}")

# ==============================================
# Tracking & Location Tasks
# ==============================================

@shared_task
def create_tracking_record(request_id):
    """Initialize tracking for a service request"""
    try:
        request = ServiceRequest.objects.get(id=request_id)
        
        if hasattr(request, 'tracking'):
            return
            
        tracking = Tracking.objects.create(
            service_request=request,
            current_status='processing',
            estimated_delivery=calculate_estimated_completion(request),
            tracking_number=generate_tracking_number(request)
        )
        
        TrackingEvent.objects.create(
            tracking=tracking,
            status='processing',
            location=request.pickup_address,
            description="Service request received and being processed"
        )
        
    except Exception as e:
        logger.error(f"Error in create_tracking_record: {str(e)}")

@shared_task
def update_provider_location(provider_id, latitude, longitude):
    """Update provider location and check proximity"""
    try:
        provider = ServiceProviderProfile.objects.get(id=provider_id)
        provider.update_location(latitude, longitude)
        
        if provider.current_service and provider.current_service.status == 'in_progress':
            tracking_event = TrackingEvent.objects.create(
                tracking=provider.current_service.tracking,
                status='in_transit',
                location=f"{latitude}, {longitude}",
                coordinates=f"POINT({longitude} {latitude})",
                description="Provider location update"
            )
            
            # Broadcast to customer
            async_to_sync(channel_layer.group_send)(
                f"service_{provider.current_service.id}",
                {
                    "type": "location.update",
                    "latitude": latitude,
                    "longitude": longitude,
                    "timestamp": str(timezone.now())
                }
            )
            
            check_arrival_status.delay(provider.current_service.id)
            
    except Exception as e:
        logger.error(f"Error in update_provider_location: {str(e)}")

# ==============================================
# System Maintenance Tasks
# ==============================================

@shared_task(bind=True, ignore_result=True, max_retries=3, default_retry_delay=30)
def run_dispatcher(self):
    """Run the EnhancedUnifiedDispatcher continuously"""
    lock_id = "dispatch_lock"

    if cache.get(lock_id):
        logger.warning("Dispatcher already running — skipping new instance.")
        return

    cache.set(lock_id, True, timeout=600)

    dispatcher = EnhancedUnifiedDispatcher()

    async def start():
        logger.info("Starting EnhancedUnifiedDispatcher (Celery)...")
        await dispatcher.run_continuous_dispatch()

    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        logger.info("Dispatcher stopped manually.")
    except Exception as e:
        logger.error(f"Dispatcher crashed: {e}")
        try:
            self.retry(exc=e)
        except Exception:
            logger.error("Retry failed or max retries reached for dispatcher task.")
    finally:
        cache.delete(lock_id)

@shared_task
def update_demand_predictions():
    """Periodically update demand predictions"""
    try:
        predictor = prediction.DemandPredictor()
        predictor.train_model()
    except Exception as e:
        logger.error(f"Error updating demand predictions: {str(e)}")

@shared_task
def adjust_dynamic_pricing():
    """Periodically adjust dynamic pricing"""
    try:
        # Implementation would analyze current demand and adjust pricing
        pass
    except Exception as e:
        logger.error(f"Error adjusting dynamic pricing: {str(e)}")

@shared_task
def send_safety_report():
    """Send periodic safety reports"""
    try:
        # Generate and send safety reports to administrators
        pass
    except Exception as e:
        logger.error(f"Error sending safety report: {str(e)}")

# ==============================================
# Notification Queue Processing
# ==============================================

@shared_task
def process_notification_queue():
    """Process pending notifications in batches"""
    try:
        # Process email notifications
        email_notifications = NotificationQueue.objects.filter(
            channel='email',
            status='pending'
        )[:50]
        
        for notification in email_notifications:
            try:
                send_mail(
                    notification.subject,
                    notification.message,
                    settings.DEFAULT_FROM_EMAIL,
                    [notification.user.email],
                    html_message=notification.message,
                    fail_silently=False
                )
                
                notification.status = 'sent'
                notification.sent_at = timezone.now()
                notification.save()
            except Exception as e:
                notification.status = 'failed'
                notification.save()
                logger.error(f"Failed to send email: {str(e)}")
        
        # Process SMS notifications
        if hasattr(settings, 'TWILIO_ACCOUNT_SID'):
            sms_notifications = NotificationQueue.objects.filter(
                channel='sms',
                status='pending'
            )[:50]
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            for notification in sms_notifications:
                try:
                    client.messages.create(
                        body=notification.message,
                        from_=settings.TWILIO_PHONE_NUMBER,
                        to=notification.user.notification_preferences.phone_number
                    )
                    
                    notification.status = 'sent'
                    notification.sent_at = timezone.now()
                    notification.save()
                except Exception as e:
                    notification.status = 'failed'
                    notification.save()
                    logger.error(f"Failed to send SMS: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error in process_notification_queue: {str(e)}")'''