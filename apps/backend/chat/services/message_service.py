"""
Chat message service.

Centralizes message creation, replies, read receipts, and
disappearing-message behavior.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from ..models import Message


class ChatMessageService:
    """Application service for Message operations."""

    # ============================================================
    # Creation
    # ============================================================

    @staticmethod
    @transaction.atomic
    def send_message(
        *,
        room,
        sender,
        text="",
        image=None,
        file=None,
        reply_to=None,
    ):
        """
        Create a message after validating sender membership.
        """

        ChatMessageService.require_sender_access(
            room=room,
            sender=sender,
        )

        text = text or ""

        if not text.strip() and image is None and file is None:
            raise ValidationError(
                "A message must contain text, an image, or a file."
            )

        if reply_to is not None:
            ChatMessageService.validate_reply(
                room=room,
                reply_to=reply_to,
            )

        message = Message.objects.create(
            chatroom=room,
            sender=sender,
            text=text,
            image=image,
            file=file,
            reply_to=reply_to,
        )

        # Keep room ordering/activity current.
        room.save(update_fields=["updated_at"])

        return message

    @staticmethod
    @transaction.atomic
    def send_text_message(
        *,
        room,
        sender,
        text,
        reply_to=None,
    ):
        """Send a text-only message."""

        if not text or not text.strip():
            raise ValidationError(
                "Message text cannot be empty."
            )

        return ChatMessageService.send_message(
            room=room,
            sender=sender,
            text=text,
            reply_to=reply_to,
        )

    @staticmethod
    @transaction.atomic
    def send_media_message(
        *,
        room,
        sender,
        image=None,
        file=None,
        text="",
        reply_to=None,
    ):
        """Send an image/file message."""

        if image is None and file is None:
            raise ValidationError(
                "An image or file is required."
            )

        return ChatMessageService.send_message(
            room=room,
            sender=sender,
            text=text,
            image=image,
            file=file,
            reply_to=reply_to,
        )

    # ============================================================
    # Authorization
    # ============================================================

    @staticmethod
    def require_sender_access(*, room, sender):
        if not sender or not sender.is_authenticated:
            raise PermissionDenied(
                "Authentication is required to send messages."
            )

        if not room.participants.filter(pk=sender.pk).exists():
            raise PermissionDenied(
                "You are not a participant in this chat."
            )

    # ============================================================
    # Replies
    # ============================================================

    @staticmethod
    def validate_reply(*, room, reply_to):
        """Ensure a reply belongs to the same room."""

        if reply_to.chatroom_id != room.pk:
            raise ValidationError(
                "A message can only reply to a message "
                "in the same chat."
            )

    @staticmethod
    def get_replies(message):
        """Return replies to a message."""

        return (
            Message.objects
            .filter(reply_to=message)
            .select_related("sender")
            .order_by("timestamp")
        )

    # ============================================================
    # Retrieval
    # ============================================================

    @staticmethod
    def get_room_messages(*, room, limit=None):
        """
        Return messages for a room.

        Messages are ordered oldest-first so the caller can directly
        construct a conversation timeline.
        """

        queryset = (
            Message.objects
            .filter(chatroom=room)
            .select_related("sender", "reply_to")
            .prefetch_related("read_by")
            .order_by("timestamp")
        )

        if limit is not None:
            if limit <= 0:
                raise ValidationError(
                    "Limit must be greater than zero."
                )

            queryset = queryset[:limit]

        return queryset

    @staticmethod
    def get_message(*, message_id):
        """Retrieve a message."""

        return (
            Message.objects
            .select_related(
                "chatroom",
                "sender",
                "reply_to",
            )
            .get(pk=message_id)
        )

    # ============================================================
    # Read receipts
    # ============================================================

    @staticmethod
    @transaction.atomic
    def mark_as_read(*, message, user):
        """
        Mark a message as read by a participant.
        """

        if not user or not user.is_authenticated:
            raise PermissionDenied(
                "Authentication is required."
            )

        if not message.chatroom.participants.filter(
            pk=user.pk
        ).exists():
            raise PermissionDenied(
                "Only chat participants can mark messages as read."
            )

        message.read_by.add(user)

        return message

    @staticmethod
    @transaction.atomic
    def mark_room_as_read(*, room, user):
        """
        Mark all currently unread room messages as read by the user.
        """

        if not user or not user.is_authenticated:
            raise PermissionDenied(
                "Authentication is required."
            )

        if not room.participants.filter(pk=user.pk).exists():
            raise PermissionDenied(
                "Only chat participants can mark messages as read."
            )

        messages = (
            Message.objects
            .filter(chatroom=room)
            .exclude(read_by=user)
        )

        for message in messages.iterator():
            message.read_by.add(user)

        return room

    # ============================================================
    # Deletion
    # ============================================================

    @staticmethod
    @transaction.atomic
    def delete_message(*, message, user):
        """
        Delete a message only when the user is its sender.
        """

        if message.sender_id != user.pk:
            raise PermissionDenied(
                "Only the sender can delete this message."
            )

        message.delete()

    # ============================================================
    # Disappearing messages
    # ============================================================

    @staticmethod
    def get_expired_messages():
        """
        Return messages whose disappearance time has passed.
        """

        from django.utils import timezone

        return Message.objects.filter(
            is_disappearing=True,
            disappear_at__isnull=False,
            disappear_at__lte=timezone.now(),
        )

    @staticmethod
    @transaction.atomic
    def delete_expired_messages():
        """
        Delete expired disappearing messages.

        Intended for a scheduled/Celery task.
        """

        queryset = ChatMessageService.get_expired_messages()

        count = queryset.count()

        queryset.delete()

        return count