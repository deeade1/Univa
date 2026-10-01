"""
Chat room service.

Responsible for creating, retrieving, and managing ChatRoom instances.

Architecture
------------

Transport context is represented through:

    ChatRoom.service_request

Trip and Delivery are proxy models over ServiceRequest, so this
service never creates separate Trip/Delivery relationships.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import ChatRoom, ChatRoomType


class ChatRoomService:
    """Application service for ChatRoom operations."""

    # ============================================================
    # Creation
    # ============================================================

    @staticmethod
    @transaction.atomic
    def create_direct_chat(*, user, other_user, name=None):
        """
        Create or return a direct conversation between two users.

        A direct chat cannot have a Transport ServiceRequest context.
        """

        if not user or not user.is_authenticated:
            raise ValidationError("A valid authenticated user is required.")

        if not other_user:
            raise ValidationError("The other user is required.")

        if user.pk == other_user.pk:
            raise ValidationError(
                "A direct chat requires two different users."
            )

        existing = (
            ChatRoom.objects
            .filter(
                room_type=ChatRoomType.DIRECT,
                service_request__isnull=True,
                participants=user,
            )
            .filter(participants=other_user)
            .distinct()
            .first()
        )

        if existing:
            return existing

        room = ChatRoom.objects.create(
            name=name or "",
            room_type=ChatRoomType.DIRECT,
        )

        room.participants.add(user, other_user)

        return room

    @staticmethod
    @transaction.atomic
    def create_group_chat(
        *,
        creator,
        participants,
        name,
        group_photo=None,
    ):
        """
        Create a generic group chat.

        Transport-specific group chats should use
        create_for_service_request().
        """

        if not creator or not creator.is_authenticated:
            raise ValidationError(
                "A valid authenticated creator is required."
            )

        if not name or not name.strip():
            raise ValidationError(
                "A group chat name is required."
            )

        participants = list(participants or [])

        users = {
            user.pk: user
            for user in participants
            if user is not None
        }

        users[creator.pk] = creator

        room = ChatRoom.objects.create(
            name=name.strip(),
            room_type=ChatRoomType.GROUP,
            admin=creator,
            group_photo=group_photo,
        )

        room.participants.add(*users.values())

        return room

    @staticmethod
    @transaction.atomic
    def create_for_service_request(
        *,
        service_request,
        participants=None,
        creator=None,
        room_type=None,
        name=None,
    ):
        """
        Create or return the chat associated with a ServiceRequest.

        The ServiceRequest is the canonical Transport context.

        room_type may be explicitly supplied. Otherwise it is inferred
        from the ServiceRequest service_type.
        """

        if service_request is None:
            raise ValidationError(
                "A ServiceRequest is required."
            )

        if room_type is None:
            room_type = ChatRoomService.room_type_for_service_request(
                service_request
            )

        ChatRoomService.validate_service_request_room_type(
            service_request=service_request,
            room_type=room_type,
        )

        existing = (
            ChatRoom.objects
            .filter(
                service_request=service_request,
                room_type=room_type,
            )
            .first()
        )

        if existing:
            if participants:
                existing.participants.add(*participants)

            if creator and not existing.admin_id:
                existing.admin = creator
                existing.save(update_fields=["admin"])

            return existing

        if name is None:
            name = ChatRoomService.default_service_request_name(
                service_request
            )

        room = ChatRoom.objects.create(
            name=name,
            room_type=room_type,
            service_request=service_request,
            admin=creator,
        )

        users = set(participants or [])

        if creator:
            users.add(creator)

        # Add the obvious ServiceRequest participants.
        if service_request.customer_id:
            users.add(service_request.customer)

        if service_request.provider_id:
            provider = service_request.provider

            if provider is not None and hasattr(provider, "user_id"):
                provider_user = getattr(provider, "user", None)

                if provider_user is not None:
                    users.add(provider_user)

        users = [user for user in users if user is not None]

        if users:
            room.participants.add(*users)

        return room

    # ============================================================
    # Retrieval
    # ============================================================

    @staticmethod
    def get_room(room_id):
        """Return a ChatRoom by primary key."""

        return (
            ChatRoom.objects
            .prefetch_related("participants")
            .select_related("service_request", "admin")
            .get(pk=room_id)
        )

    @staticmethod
    def get_user_rooms(user):
        """Return rooms in which the user participates."""

        return (
            ChatRoom.objects
            .filter(participants=user)
            .select_related("service_request", "admin")
            .prefetch_related("participants")
            .distinct()
            .order_by("-updated_at")
        )

    @staticmethod
    def get_service_request_room(service_request):
        """
        Return the existing room associated with a ServiceRequest.

        Returns None when no room exists.
        """

        return (
            ChatRoom.objects
            .filter(service_request=service_request)
            .first()
        )

    # ============================================================
    # Room type handling
    # ============================================================

    @staticmethod
    def room_type_for_service_request(service_request):
        """
        Determine the ChatRoom type from ServiceRequest.service_type.
        """

        service_type = service_request.service_type

        if service_type == "delivery":
            return ChatRoomType.DELIVERY

        if service_type in {
            "taxi",
            "shared",
            "interstate",
        }:
            return ChatRoomType.TRIP

        return ChatRoomType.SERVICE_REQUEST

    @staticmethod
    def default_service_request_name(service_request):
        """Generate a useful default room name."""

        service_label = service_request.get_service_type_display()

        return f"{service_label} #{service_request.pk}"

    @staticmethod
    def validate_service_request_room_type(
        *,
        service_request,
        room_type,
    ):
        """Validate room type against ServiceRequest semantics."""

        contextual_types = {
            ChatRoomType.SERVICE_REQUEST,
            ChatRoomType.TRIP,
            ChatRoomType.DELIVERY,
        }

        if room_type not in contextual_types:
            raise ValidationError(
                "A ServiceRequest chat must use a contextual room type."
            )

        if room_type == ChatRoomType.TRIP:
            if not service_request.is_trip:
                raise ValidationError(
                    "TRIP chat requires a trip ServiceRequest."
                )

        if room_type == ChatRoomType.DELIVERY:
            if not service_request.is_delivery:
                raise ValidationError(
                    "DELIVERY chat requires a delivery ServiceRequest."
                )

    # ============================================================
    # Room management
    # ============================================================

    @staticmethod
    @transaction.atomic
    def rename_room(*, room, name):
        """Rename a chat room."""

        if not name or not name.strip():
            raise ValidationError(
                "Room name cannot be empty."
            )

        room.name = name.strip()
        room.save(update_fields=["name", "updated_at"])

        return room

    @staticmethod
    @transaction.atomic
    def set_disappearing_messages_duration(
        *,
        room,
        duration,
    ):
        """
        Enable or disable disappearing messages.

        duration=None disables the feature.
        """

        if duration is not None and duration <= 0:
            raise ValidationError(
                "Duration must be greater than zero."
            )

        room.disappearing_messages_duration = duration

        room.save(
            update_fields=[
                "disappearing_messages_duration",
                "updated_at",
            ]
        )

        return room

    @staticmethod
    @transaction.atomic
    def delete_room(room):
        """Delete a room and its dependent messages."""

        room.delete()