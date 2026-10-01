"""
Chat participant service.

Responsible for participant membership and authorization.

The Chat application owns membership in ChatRoom, while Transport
remains the source of truth for who should be eligible for a
ServiceRequest conversation.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from ..models import ChatRoom


class ChatParticipantService:
    """Application service for ChatRoom participants."""

    # ============================================================
    # Membership
    # ============================================================

    @staticmethod
    def is_participant(*, room, user):
        if not user or not user.is_authenticated:
            return False

        return room.participants.filter(pk=user.pk).exists()

    @staticmethod
    def require_participant(*, room, user):
        """
        Require the user to belong to the room.
        """

        if not ChatParticipantService.is_participant(
            room=room,
            user=user,
        ):
            raise PermissionDenied(
                "You are not a participant in this chat."
            )

        return True

    @staticmethod
    @transaction.atomic
    def add_participant(*, room, user, actor=None):
        """
        Add a participant to a room.

        actor is optional here because higher-level authorization
        can be applied by GraphQL/API services.
        """

        if user is None:
            raise ValidationError("A user is required.")

        if room.room_type == "direct":
            if room.participants.count() >= 2:
                raise ValidationError(
                    "A direct chat cannot have more than two participants."
                )

        room.participants.add(user)

        return room

    @staticmethod
    @transaction.atomic
    def add_participants(*, room, users, actor=None):
        """Add multiple participants."""

        users = [user for user in (users or []) if user is not None]

        if not users:
            return room

        if room.room_type == "direct":
            current_count = room.participants.count()

            new_users = [
                user
                for user in users
                if not room.participants.filter(pk=user.pk).exists()
            ]

            if current_count + len(new_users) > 2:
                raise ValidationError(
                    "A direct chat cannot have more than two participants."
                )

        room.participants.add(*users)

        return room

    @staticmethod
    @transaction.atomic
    def remove_participant(*, room, user, actor=None):
        """Remove a participant from a room."""

        if not room.participants.filter(pk=user.pk).exists():
            return room

        if room.room_type == "direct":
            raise ValidationError(
                "Participants cannot be removed from a direct chat."
            )

        if room.admin_id == user.pk:
            raise ValidationError(
                "The room administrator cannot be removed. "
                "Transfer administration first."
            )

        room.participants.remove(user)

        return room

    # ============================================================
    # Administration
    # ============================================================

    @staticmethod
    @transaction.atomic
    def set_admin(*, room, user, actor=None):
        """Set a room administrator."""

        if not room.participants.filter(pk=user.pk).exists():
            raise ValidationError(
                "The administrator must be a room participant."
            )

        room.admin = user
        room.save(update_fields=["admin", "updated_at"])

        return room

    @staticmethod
    def require_admin(*, room, user):
        """Require the user to be the room administrator."""

        if not user or not user.is_authenticated:
            raise PermissionDenied(
                "Authentication is required."
            )

        if room.admin_id != user.pk:
            raise PermissionDenied(
                "Only the room administrator can perform this action."
            )

        return True

    # ============================================================
    # Transport eligibility
    # ============================================================

    @staticmethod
    def get_expected_service_request_users(service_request):
        """
        Return users directly associated with a ServiceRequest.

        This intentionally handles only relationships that are
        definitely present on the current ServiceRequest model:

            customer
            provider -> user

        Booking/passenger membership should be supplied by the
        Transport booking layer when required.
        """

        users = []

        if service_request.customer_id:
            users.append(service_request.customer)

        if service_request.provider_id:
            provider = service_request.provider

            if provider is not None:
                provider_user = getattr(provider, "user", None)

                if provider_user is not None:
                    users.append(provider_user)

        return users

    @staticmethod
    def can_join_service_request_chat(
        *,
        service_request,
        user,
    ):
        """
        Determine whether a user is directly eligible for a
        ServiceRequest chat.
        """

        if not user or not user.is_authenticated:
            return False

        expected_users = (
            ChatParticipantService
            .get_expected_service_request_users(service_request)
        )

        return any(
            expected_user.pk == user.pk
            for expected_user in expected_users
        )

    @staticmethod
    def require_service_request_chat_access(
        *,
        service_request,
        user,
    ):
        """
        Require direct ServiceRequest participation.

        Passenger/booking eligibility can be extended by Transport
        without changing ChatRoom itself.
        """

        if not ChatParticipantService.can_join_service_request_chat(
            service_request=service_request,
            user=user,
        ):
            raise PermissionDenied(
                "You are not authorized to access this ServiceRequest chat."
            )

        return True

    @staticmethod
    @transaction.atomic
    def sync_service_request_participants(
        *,
        room,
        additional_users=None,
    ):
        """
        Synchronize obvious ServiceRequest participants into a room.

        Does not remove existing participants.

        This is intentionally additive because removing users may
        have business and audit implications.
        """

        if not room.service_request_id:
            raise ValidationError(
                "This room is not associated with a ServiceRequest."
            )

        users = ChatParticipantService.get_expected_service_request_users(
            room.service_request
        )

        users.extend(additional_users or [])

        unique_users = {
            user.pk: user
            for user in users
            if user is not None
        }

        if unique_users:
            room.participants.add(*unique_users.values())

        return room