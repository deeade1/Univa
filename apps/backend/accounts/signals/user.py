"""
Accounts user signals.

Signals in this module are intentionally limited to the accounts domain.

Cross-domain initialization such as biometrics, transport, and real-estate
profiles must be handled by their respective application services rather
than by the accounts application.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create the core UserProfile when a User is created.

    This signal deliberately does NOT create domain-specific records such as:

    - FaceVerification
    - DriverProfile
    - AgentProfile
    - Agent
    - transport records
    - realestate records
    """
    if not created:
        return

    UserProfile.objects.get_or_create(
        user=instance,
    )