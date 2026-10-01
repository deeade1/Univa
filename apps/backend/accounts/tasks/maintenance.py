# apps/backend/accounts/tasks/maintenance.py

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from accounts.models import (
    Role,
    User,
    UserProfile,
    UserRole,
)

logger = logging.getLogger(__name__)


def notify_user_role_expired(role):
    """Notify a user that an account role has expired."""
    if not role.user.email:
        return

    subject = f"Role '{role.role.name}' expired"

    message = (
        f"Hi {role.user.first_name or 'user'},\n\n"
        f"Your role '{role.role.name}' in "
        f"'{role.role.app_name}' has expired "
        f"as of {role.expires_at.strftime('%Y-%m-%d %H:%M')}.\n\n"
        "If this is an error, please contact support."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [role.user.email],
        fail_silently=True,
    )


@shared_task(queue="default")
def deactivate_expired_roles():
    """Deactivate expired account roles."""
    now = timezone.now()

    expired_roles = UserRole.objects.filter(
        is_active=True,
        expires_at__isnull=False,
        expires_at__lt=now,
    )

    count = 0

    for role in expired_roles:
        role.is_active = False
        role.revoked_at = now
        role.notes = (
            f"{role.notes or ''}\n"
            "Auto-revoked due to expiration."
        ).strip()

        role.save(
            update_fields=[
                "is_active",
                "revoked_at",
                "notes",
            ]
        )

        try:
            notify_user_role_expired(role)
        except Exception:
            logger.exception(
                "Failed to notify user about expired role %s",
                role.pk,
            )

        count += 1

    logger.info(
        "Deactivated %s expired user roles",
        count,
    )

    return count


@shared_task(queue="default")
def assign_default_roles(user_id):
    """Assign default roles to a newly created user."""
    try:
        user = User.objects.get(pk=user_id)

        default_roles = Role.objects.filter(
            is_default=True,
        )

        for role in default_roles:
            UserRole.objects.get_or_create(
                user=user,
                role=role,
                defaults={
                    "created_by": user,
                },
            )

        logger.info(
            "Assigned default roles to user %s",
            user_id,
        )

    except Exception:
        logger.exception(
            "Failed to assign default roles to user %s",
            user_id,
        )


@shared_task(bind=True, queue="high_priority")
def process_role_change(
    self,
    user_id,
    role_id,
    action,
):
    """Add or remove a user role."""
    try:
        user = User.objects.get(pk=user_id)
        role = Role.objects.get(pk=role_id)

        if action == "add":
            UserRole.objects.get_or_create(
                user=user,
                role=role,
                defaults={
                    "created_by": user,
                },
            )

            logger.info(
                "Added role %s to user %s",
                role_id,
                user_id,
            )

        elif action == "remove":
            UserRole.objects.filter(
                user=user,
                role=role,
            ).delete()

            logger.info(
                "Removed role %s from user %s",
                role_id,
                user_id,
            )

        else:
            raise ValueError(
                f"Unsupported role action: {action}"
            )

    except Exception as exc:
        logger.exception(
            "Failed to %s role %s for user %s",
            action,
            role_id,
            user_id,
        )

        raise self.retry(
            exc=exc,
            countdown=60,
        )