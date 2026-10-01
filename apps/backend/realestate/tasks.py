# tasks.py
'''import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.mail import send_mail
from twilio.rest import Client

from .models import NotificationQueue

logger = logging.getLogger(__name__)

import json
import logging
from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from twilio.rest import Client

from .models import (Listing, LiveTourSchedule, Message, MessageThread,
                     NotificationQueue, PropertySubscription, SavedSearch,
                     UserProfile, VirtualTour)

logger = logging.getLogger(__name__)

# ==============================================
# Notification Tasks
# ==============================================

@shared_task(bind=True, max_retries=3)
def send_websocket_notification(self, user_id, notification_data):
    """
    Send real-time notification via WebSocket
    """
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "property.notification",
                "notification": notification_data
            }
        )
        logger.info(f"WebSocket notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket notification failed for user {user_id}: {str(e)}")
        self.retry(exc=e, countdown=60)

@shared_task
def notify_new_listing(listing_id):
    """
    Notify subscribed users about a new property listing
    """
    try:
        listing = Listing.objects.get(id=listing_id)
        subscriptions = PropertySubscription.objects.filter(
            Q(property_type=listing.listing_type.property_type) | 
            Q(property_type__isnull=True)
        )
        
        if listing.location_point:
            # Add location-based subscriptions
            location_subs = PropertySubscription.objects.filter(
                location_point__distance_lte=(
                    listing.location_point, 
                    D(km=F('radius_km'))
                )
            )
            subscriptions = (subscriptions | location_subs).distinct()

        for subscription in subscriptions:
            notification_data = {
                'type': 'new_listing',
                'listing_id': str(listing.id),
                'title': listing.title,
                'price': str(listing.price),
                'property_type': listing.listing_type.property_type,
                'url': f"{settings.FRONTEND_URL}/listings/{listing.id}",
                'timestamp': str(timezone.now())
            }
            
            # Send WebSocket notification
            send_websocket_notification.delay(
                subscription.user.id,
                notification_data
            )
            
            # Queue email notification if user has email notifications enabled
            if subscription.user.notification_preferences.email_notifications:
                queue_email_notification.delay(
                    subscription.user.id,
                    notification_data
                )
                
            # Queue SMS notification if enabled
            if (subscription.user.notification_preferences.sms_notifications and 
                subscription.user.notification_preferences.phone_number):
                queue_sms_notification.delay(
                    subscription.user.notification_preferences.phone_number,
                    notification_data
                )
                
    except Listing.DoesNotExist:
        logger.error(f"Listing {listing_id} not found")
    except Exception as e:
        logger.error(f"Error in notify_new_listing: {str(e)}")

@shared_task
def notify_listing_update(listing_id, changed_fields):
    """
    Notify interested users about property updates
    """
    try:
        listing = Listing.objects.get(id=listing_id)
        
        # Notify users who saved this property
        saved_users = UserProfile.objects.filter(
            saved_properties=listing
        )
        
        # Notify users who messaged about this property
        thread_users = UserProfile.objects.filter(
            Q(message_threads__property=listing) |
            Q(received_messages__thread__property=listing)
        ).distinct()
        
        # Combine all interested users
        interested_users = (saved_users | thread_users).distinct()
        
        for user in interested_users:
            notification_data = {
                'type': 'listing_update',
                'listing_id': str(listing.id),
                'title': listing.title,
                'changed_fields': changed_fields,
                'url': f"{settings.FRONTEND_URL}/listings/{listing.id}",
                'timestamp': str(timezone.now())
            }
            
            send_websocket_notification.delay(
                user.id,
                notification_data
            )
            
            if user.notification_preferences.email_notifications:
                queue_email_notification.delay(
                    user.id,
                    notification_data
                )
                
    except Listing.DoesNotExist:
        logger.error(f"Listing {listing_id} not found")
    except Exception as e:
        logger.error(f"Error in notify_listing_update: {str(e)}")

# ==============================================
# Message Processing Tasks
# ==============================================

@shared_task
def process_message(message_id):
    """
    Process new message with potential additional logic
    """
    try:
        message = Message.objects.get(id=message_id)
        
        # Check for virtual tour links
        if 'virtual tour' in message.content.lower():
            # Extract URL from message
            import re
            urls = re.findall(r'(https?://\S+)', message.content)
            if urls:
                VirtualTour.objects.create(
                    property=message.thread.property,
                    tour_url=urls[0],
                    created_by=message.sender
                )
                
        # Check for scheduling requests
        if 'schedule a tour' in message.content.lower():
            # Parse potential dates from message
            # This is simplified - you'd want more robust date parsing
            from dateparser import parse
            date_str = message.content.split('on')[-1].strip()
            tour_date = parse(date_str)
            
            if tour_date:
                LiveTourSchedule.objects.create(
                    property=message.thread.property,
                    agent=message.thread.property.agent,
                    scheduled_time=tour_date,
                    meeting_link=f"{settings.BASE_URL}/meeting/{message.thread.id}"
                )
                
        # Notify other thread participants
        participants = message.thread.participants.exclude(id=message.sender.id)
        for participant in participants:
            notification_data = {
                'type': 'new_message',
                'thread_id': str(message.thread.id),
                'sender': message.sender.get_full_name(),
                'preview': message.content[:50],
                'timestamp': str(message.timestamp)
            }
            
            send_websocket_notification.delay(
                participant.id,
                notification_data
            )
            
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found")
    except Exception as e:
        logger.error(f"Error processing message {message_id}: {str(e)}")

# ==============================================
# Scheduled Tasks
# ==============================================

@shared_task
def check_saved_searches():
    """
    Run saved searches and notify users of new matches
    """
    try:
        searches = SavedSearch.objects.filter(is_active=True)
        
        for search in searches:
            try:
                params = search.search_parameters
                query = Q()
                
                if 'min_price' in params:
                    query &= Q(price__gte=params['min_price'])
                if 'max_price' in params:
                    query &= Q(price__lte=params['max_price'])
                if 'property_types' in params:
                    query &= Q(listing_type__property_type__in=params['property_types'])
                if 'bedrooms' in params:
                    query &= Q(bedrooms__gte=params['bedrooms'])
                if 'location' in params:
                    query &= Q(address__city__iexact=params['location'])
                
                # Find listings created since last notification
                if search.last_notified:
                    new_listings = Listing.objects.filter(
                        query,
                        created__gt=search.last_notified
                    )
                else:
                    new_listings = Listing.objects.filter(query)
                
                if new_listings.exists():
                    notification_data = {
                        'type': 'saved_search',
                        'search_id': str(search.id),
                        'search_name': search.name,
                        'count': new_listings.count(),
                        'listings': [
                            {
                                'id': str(l.id),
                                'title': l.title,
                                'price': str(l.price),
                                'url': f"{settings.FRONTEND_URL}/listings/{l.id}"
                            } for l in new_listings[:5]  # Limit to 5 listings
                        ],
                        'timestamp': str(timezone.now())
                    }
                    
                    send_websocket_notification.delay(
                        search.user.id,
                        notification_data
                    )
                    
                    if search.user.notification_preferences.email_notifications:
                        queue_email_notification.delay(
                            search.user.id,
                            notification_data
                        )
                    
                    search.last_notified = timezone.now()
                    search.save()
                    
            except Exception as e:
                logger.error(f"Error processing saved search {search.id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in check_saved_searches: {str(e)}")

@shared_task
def send_tour_reminders():
    """
    Send reminders for upcoming virtual tours
    """
    try:
        now = timezone.now()
        upcoming_tours = LiveTourSchedule.objects.filter(
            scheduled_time__gt=now,
            scheduled_time__lte=now + timedelta(hours=24)
        )
        
        for tour in upcoming_tours:
            # Notify agent
            notification_data = {
                'type': 'tour_reminder',
                'tour_id': str(tour.id),
                'property_title': tour.property.title,
                'scheduled_time': str(tour.scheduled_time),
                'meeting_link': tour.meeting_link,
                'is_agent': True
            }
            
            send_websocket_notification.delay(
                tour.agent.user.id,
                notification_data
            )
            
            # Notify attendees
            for registration in tour.livetourregistration_set.all():
                attendee_notification = {
                    'type': 'tour_reminder',
                    'tour_id': str(tour.id),
                    'property_title': tour.property.title,
                    'scheduled_time': str(tour.scheduled_time),
                    'meeting_link': tour.meeting_link,
                    'is_agent': False
                }
                
                send_websocket_notification.delay(
                    registration.user.id,
                    attendee_notification
                )
                
                if registration.user.notification_preferences.email_notifications:
                    queue_email_notification.delay(
                        registration.user.id,
                        attendee_notification
                    )
                    
    except Exception as e:
        logger.error(f"Error in send_tour_reminders: {str(e)}")

# ==============================================
# Email/SMS Queue Processing
# ==============================================

@shared_task
def queue_email_notification(user_id, notification_data):
    """
    Add email notification to queue
    """
    try:
        user = UserProfile.objects.get(id=user_id)
        
        if notification_data['type'] == 'new_listing':
            subject = f"New Property: {notification_data['title']}"
            template = 'emails/new_property.html'
        elif notification_data['type'] == 'listing_update':
            subject = f"Property Update: {notification_data['title']}"
            template = 'emails/updated_property.html'
        elif notification_data['type'] == 'saved_search':
            subject = f"New matches for your saved search: {notification_data['search_name']}"
            template = 'emails/saved_search_results.html'
        elif notification_data['type'] == 'tour_reminder':
            subject = f"Reminder: Upcoming Property Tour"
            template = 'emails/tour_reminder.html'
        else:
            subject = "New Notification"
            template = 'emails/generic_notification.html'
        
        message = render_to_string(template, {
            'user': user,
            'notification': notification_data
        })
        
        NotificationQueue.objects.create(
            user=user,
            notification_type=notification_data['type'],
            subject=subject,
            message=message,
            channel='email',
            metadata=notification_data
        )
        
    except UserProfile.DoesNotExist:
        logger.error(f"User {user_id} not found")
    except Exception as e:
        logger.error(f"Failed to queue email for user {user_id}: {str(e)}")

@shared_task
def queue_sms_notification(phone_number, notification_data):
    """
    Add SMS notification to queue
    """
    try:
        user = UserProfile.objects.get(
            notification_preferences__phone_number=phone_number
        )
        
        if notification_data['type'] == 'new_listing':
            message = f"New property: {notification_data['title']}. {notification_data['url']}"
        elif notification_data['type'] == 'listing_update':
            changes = ", ".join(notification_data.get('changed_fields', {}).keys())
            message = f"Property updated: {notification_data['title']} ({changes}). {notification_data['url']}"
        elif notification_data['type'] == 'saved_search':
            message = f"{notification_data['count']} new matches for '{notification_data['search_name']}'. {settings.FRONTEND_URL}/saved-searches/{notification_data['search_id']}"
        elif notification_data['type'] == 'tour_reminder':
            message = f"Reminder: Tour for {notification_data['property_title']} at {notification_data['scheduled_time']}. Join: {notification_data['meeting_link']}"
        else:
            message = f"You have a new notification. {settings.FRONTEND_URL}/notifications"
        
        NotificationQueue.objects.create(
            user=user,
            notification_type=notification_data['type'],
            subject="Property Notification",
            message=message,
            channel='sms',
            metadata=notification_data
        )
        
    except UserProfile.DoesNotExist:
        logger.error(f"User with phone {phone_number} not found")
    except Exception as e:
        logger.error(f"Failed to queue SMS for {phone_number}: {str(e)}")

@shared_task
def process_notification_queue():
    """
    Process pending notifications in batches
    """
    try:
        # Process email notifications
        email_notifications = NotificationQueue.objects.filter(
            channel='email',
            status='pending'
        )[:50]  # Process in batches of 50
        
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
                logger.error(f"Failed to send email to {notification.user.email}: {str(e)}")
        
        # Process SMS notifications if Twilio is configured
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
                    logger.error(f"Failed to send SMS to {notification.user.notification_preferences.phone_number}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error in process_notification_queue: {str(e)}")

# ==============================================
# GraphQL Mutation Tasks
# ==============================================

@shared_task
def process_create_listing(listing_data, user_id):
    """
    Async processing after listing creation via GraphQL
    """
    try:
        from .mutations import notify_new_listing
        listing = Listing.objects.get(id=listing_data['id'])
        
        # Generate virtual tour if images exist
        if listing.images.exists():
            try:
                # This would integrate with your actual virtual tour service
                tour_url = generate_virtual_tour(listing)
                VirtualTour.objects.create(
                    property=listing,
                    tour_url=tour_url,
                    created_by_id=user_id
                )
            except Exception as e:
                logger.error(f"Failed to generate virtual tour for listing {listing.id}: {str(e)}")
        
        # Notify subscribers
        notify_new_listing.delay(listing.id)
        
        # Update search indexes
        update_search_index.delay(listing.id)
        
    except Listing.DoesNotExist:
        logger.error(f"Listing {listing_data['id']} not found")
    except Exception as e:
        logger.error(f"Error in process_create_listing: {str(e)}")

@shared_task
def process_update_listing(listing_id, changed_fields, user_id):
    """
    Async processing after listing update via GraphQL
    """
    try:
        listing = Listing.objects.get(id=listing_id)
        
        # Check if important fields changed that require notifications
        if 'price' in changed_fields or 'property_status' in changed_fields:
            notify_listing_update.delay(listing.id, changed_fields)
            
        # Update search indexes if relevant fields changed
        if any(field in changed_fields for field in ['price', 'bedrooms', 'square_feet']):
            update_search_index.delay(listing.id)
            
    except Listing.DoesNotExist:
        logger.error(f"Listing {listing_id} not found")
    except Exception as e:
        logger.error(f"Error in process_update_listing: {str(e)}")

@shared_task
def update_search_index(listing_id):
    """
    Update search index for a listing
    """
    try:
        listing = Listing.objects.get(id=listing_id)
        # This would integrate with your search backend (Elasticsearch, Algolia, etc.)
        # search_backend.update_listing(listing)
        logger.info(f"Search index updated for listing {listing_id}")
    except Listing.DoesNotExist:
        logger.error(f"Listing {listing_id} not found")
    except Exception as e:
        logger.error(f"Error updating search index for listing {listing_id}: {str(e)}")

# ==============================================
# Utility Functions
# ==============================================

def generate_virtual_tour(listing):
    """
    Mock function for virtual tour generation
    In a real implementation, this would call an external service
    """
    # This is a placeholder - implement with your actual virtual tour service
    return f"https://virtualtours.example.com/{listing.id}"

@shared_task
def send_websocket_notification(user_id, notification_data):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "property.notification",
                "notification": notification_data
            }
        )
    except Exception as e:
        logger.error(f"WebSocket notification failed for user {user_id}: {str(e)}")

@shared_task
def queue_email_notification(user_id, notification_data):
    from django.contrib.auth import get_user_model

    from .models import NotificationQueue
    
    try:
        user = get_user_model().objects.get(id=user_id)
        
        if notification_data['is_new_property']:
            subject = f"New Property: {notification_data['property_title']}"
            template = 'emails/new_property.html'
        else:
            subject = f"Updated Property: {notification_data['property_title']}"
            template = 'emails/updated_property.html'
        
        message = render_to_string(template, {
            'user': user,
            'notification': notification_data
        })
        
        NotificationQueue.objects.create(
            user=user,
            notification_type='property_update',
            subject=subject,
            message=message,
            channel='email',
            metadata=notification_data
        )
    except Exception as e:
        logger.error(f"Failed to queue email for user {user_id}: {str(e)}")

@shared_task
def queue_sms_notification(phone_number, notification_data):
    from django.contrib.auth import get_user_model

    from .models import NotificationQueue
    
    try:
        user = get_user_model().objects.get(
            notification_preferences__phone_number=phone_number
        )
        
        if notification_data['is_new_property']:
            message = f"New property: {notification_data['property_title']}. {notification_data['url']}"
        else:
            changes = ", ".join(notification_data['changed_fields'].keys())
            message = f"Property updated: {notification_data['property_title']} ({changes}). {notification_data['url']}"
        
        NotificationQueue.objects.create(
            user=user,
            notification_type='property_update',
            subject="Property Update",
            message=message,
            channel='sms',
            metadata=notification_data
        )
    except Exception as e:
        logger.error(f"Failed to queue SMS for {phone_number}: {str(e)}")

@shared_task
def process_notification_queue():
    """Process pending notifications in batches"""
    from django.core.mail import EmailMultiAlternatives
    from twilio.rest import Client

    # Process email notifications
    email_notifications = NotificationQueue.objects.filter(
        channel='email',
        status='pending'
    )[:50]  # Process in batches of 50
    
    for notification in email_notifications:
        try:
            email = EmailMultiAlternatives(
                notification.subject,
                notification.message,
                settings.DEFAULT_FROM_EMAIL,
                [notification.user.email]
            )
            email.attach_alternative(notification.message, "text/html")
            email.send()
            
            notification.status = 'sent'
            notification.sent_at = timezone.now()
            notification.save()
        except Exception as e:
            notification.status = 'failed'
            notification.save()
            logger.error(f"Failed to send email to {notification.user.email}: {str(e)}")
    
    # Process SMS notifications if Twilio is configured
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
                logger.error(f"Failed to send SMS to {notification.user.notification_preferences.phone_number}: {str(e)}")'''