import os
import tempfile

import cv2
from graphql import GraphQLError
from PIL import Image


def get_user_roles(user, app_name=None):
    """
    Get active roles for a user, optionally filtered by application
    """
    if not user.is_authenticated:
        return []
    
    qs = user.app_roles.filter(is_active=True)
    if app_name:
        qs = qs.filter(app_name=app_name)
    return qs

def has_app_role(user, app_name, role_name=None):
    """
    Check if user has a specific role in an application
    """
    roles = get_user_roles(user, app_name)
    if role_name:
        return roles.filter(role__name=role_name).exists()
    return roles.exists()

def validate_app_role(info, app_name, role_name=None):
    """
    GraphQL resolver helper for role validation
    """
    user = info.context.user
    if not has_app_role(user, app_name, role_name):
        raise GraphQLError(f"Permission denied - requires {role_name or 'any'} role in {app_name}")
    return user

# Backward compatibility helpers
def is_driver(user):
    return has_app_role(user, 'taxi', 'driver')

def is_rider(user):
    return has_app_role(user, 'taxi', 'rider')




def extract_video_frame(video_path, frame_time=0):
    """Extract a frame from video at specified time"""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, frame_time * 1000)
    success, frame = cap.read()
    cap.release()
    
    if not success:
        raise ValueError("Could not extract frame from video")
    
    temp_frame = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    cv2.imwrite(temp_frame.name, frame)
    return temp_frame.name

def send_magic_link_email(user, token):
    """Send magic link email with enhanced security info"""
    subject = "Your Secure Login Link"
    login_url = token.get_absolute_url()
    device_info = token.device_info
    
    message = f"""
    Hi {user.first_name or 'there'},
    
    Click the link below to log in:
    {login_url}
    
    This link will expire in {settings.MAGIC_LINK_EXPIRY_MINUTES} minutes.
    
    Request details:
    - Time: {timezone.now().strftime('%Y-%m-%d %H:%M %Z')}
    - Device: {device_info.get('user_agent', 'Unknown')}
    - Location: {device_info.get('ip_address', 'Unknown')}
    
    If you didn't request this, please secure your account.
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False
    )

def send_magic_link_sms(user, token):
    """Send magic link via SMS"""
    from twilio.rest import Client  # Example using Twilio
    
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    message = client.messages.create(
        body=f"Your login link: {token.get_absolute_url()} (expires in {settings.MAGIC_LINK_EXPIRY_MINUTES} mins)",
        from_=settings.TWILIO_PHONE_NUMBER,
        to=str(user.phone_number)
    )
    
    return message.sid


STATE_MAP = {
    "NG": [  # Nigeria
        {"code": "NG-LA", "name": "Lagos"},
        {"code": "NG-AB", "name": "Abia"},
        {"code": "NG-KD", "name": "Kaduna"},
        # ... add the rest of Nigeria's states
    ],
    "US": [  # United States
        {"code": "NY", "name": "New York"},
        {"code": "CA", "name": "California"},
        {"code": "TX", "name": "Texas"},
        # ... add other US states
    ],
    # Add more countries as needed
}