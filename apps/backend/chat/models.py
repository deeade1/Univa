"""
Chat models for Univa.

Architecture
------------

Chat is a reusable communication domain.

Transport may provide context for a chat, but Transport does not
depend on Chat.

The canonical transport relationship is:

    ChatRoom -> ServiceRequest

Trip and Delivery are proxy models over ServiceRequest, so ChatRoom
must not maintain separate foreign keys to Trip and Delivery.
"""

import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import BTreeIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ChatRoomType(models.TextChoices):
    DIRECT = "direct", "Direct"
    GROUP = "group", "Group"
    SERVICE_REQUEST = "service_request", "Service Request"
    TRIP = "trip", "Trip"
    DELIVERY = "delivery", "Delivery"


class ChatRoom(models.Model):
    """
    A conversation between two or more users.

    A ChatRoom may optionally be associated with a Transport
    ServiceRequest.

    IMPORTANT:

    Trip and Delivery are proxy models over ServiceRequest.
    Therefore ServiceRequest is the canonical persisted context.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=255,
        db_index=True,
    )

    room_type = models.CharField(
        max_length=32,
        choices=ChatRoomType.choices,
        default=ChatRoomType.DIRECT,
        db_index=True,
    )

    participants = models.ManyToManyField(
        User,
        related_name="chat_rooms",
        blank=True,
    )

    group_photo = models.ImageField(
        upload_to="group_photos/",
        null=True,
        blank=True,
    )

    # Canonical Transport context.
    service_request = models.ForeignKey(
        "transport.ServiceRequest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_rooms",
        db_index=True,
    )

    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_of_chat_rooms",
        db_index=True,
    )

    disappearing_messages_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Duration in seconds for disappearing messages. "
            "None means disappearing messages are disabled."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-updated_at"]

        indexes = [
            BTreeIndex(
                fields=["name"],
                name="chatroom_name_idx",
            ),
            BTreeIndex(
                fields=["room_type", "created_at"],
                name="chatroom_type_created_idx",
            ),
            BTreeIndex(
                fields=["admin", "room_type"],
                name="chatroom_admin_type_idx",
            ),
            BTreeIndex(
                fields=["service_request"],
                name="chatroom_service_request_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        room_type__in=[
                            ChatRoomType.DIRECT,
                            ChatRoomType.GROUP,
                        ],
                        service_request__isnull=True,
                    )
                    |
                    Q(
                        room_type__in=[
                            ChatRoomType.SERVICE_REQUEST,
                            ChatRoomType.TRIP,
                            ChatRoomType.DELIVERY,
                        ],
                        service_request__isnull=False,
                    )
                ),
                name="chatroom_context_matches_type",
            ),
        ]

    def __str__(self):
        if self.name:
            return self.name

        return f"{self.get_room_type_display()} Chat {self.pk}"

    # ============================================================
    # Context helpers
    # ============================================================

    @property
    def is_group(self):
        """
        Whether this room represents a multi-user conversation.

        Kept as a property for application compatibility while
        room_type becomes the canonical source of truth.
        """
        return self.room_type in {
            ChatRoomType.GROUP,
            ChatRoomType.TRIP,
            ChatRoomType.DELIVERY,
        }

    @property
    def is_transport_chat(self):
        return self.service_request_id is not None

    @property
    def is_trip_chat(self):
        return self.room_type == ChatRoomType.TRIP

    @property
    def is_delivery_chat(self):
        return self.room_type == ChatRoomType.DELIVERY

    @property
    def is_service_request_chat(self):
        return self.room_type == ChatRoomType.SERVICE_REQUEST

    @property
    def transport_service_type(self):
        if not self.service_request:
            return None

        return self.service_request.service_type

    # ============================================================
    # Validation
    # ============================================================

    def clean(self):
        super().clean()

        contextual_types = {
            ChatRoomType.SERVICE_REQUEST,
            ChatRoomType.TRIP,
            ChatRoomType.DELIVERY,
        }

        if (
            self.room_type in contextual_types
            and self.service_request_id is None
        ):
            raise ValidationError(
                {
                    "service_request": (
                        "A transport chat must be associated "
                        "with a ServiceRequest."
                    )
                }
            )

        if (
            self.room_type in {
                ChatRoomType.DIRECT,
                ChatRoomType.GROUP,
            }
            and self.service_request_id is not None
        ):
            raise ValidationError(
                {
                    "service_request": (
                        "Direct and generic group chats cannot "
                        "have a ServiceRequest context."
                    )
                }
            )

        if self.room_type == ChatRoomType.TRIP:
            if self.service_request and not self.service_request.is_trip:
                raise ValidationError(
                    {
                        "service_request": (
                            "A trip chat must reference a trip "
                            "ServiceRequest."
                        )
                    }
                )

        if self.room_type == ChatRoomType.DELIVERY:
            if self.service_request and not self.service_request.is_delivery:
                raise ValidationError(
                    {
                        "service_request": (
                            "A delivery chat must reference a "
                            "delivery ServiceRequest."
                        )
                    }
                )

    # ============================================================
    # Participant helpers
    # ============================================================

    def add_participant(self, user):
        self.participants.add(user)

    def remove_participant(self, user):
        self.participants.remove(user)

    def has_participant(self, user):
        if not user or not user.is_authenticated:
            return False

        return self.participants.filter(pk=user.pk).exists()

    # ============================================================
    # Transport participant helpers
    # ============================================================

    def get_transport_customer(self):
        if not self.service_request:
            return None

        return self.service_request.customer

    def get_transport_provider(self):
        if not self.service_request:
            return None

        return self.service_request.provider

    def get_expected_transport_users(self):
        """
        Return users directly identifiable from ServiceRequest.

        Passenger/booking-specific users for shared/interstate
        services should be added by the appropriate Transport
        service rather than Chat querying Transport internals here.
        """
        if not self.service_request:
            return User.objects.none()

        user_ids = []

        if self.service_request.customer_id:
            user_ids.append(self.service_request.customer_id)

        if self.service_request.provider_id:
            provider = self.service_request.provider

            if provider and hasattr(provider, "user_id"):
                user_ids.append(provider.user_id)

        return User.objects.filter(pk__in=user_ids).distinct()


class Message(models.Model):
    """
    Message belonging to a ChatRoom.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    chatroom = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True,
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        db_index=True,
    )

    text = models.TextField(
        blank=True,
    )

    image = models.ImageField(
        upload_to="chat/images/",
        null=True,
        blank=True,
    )

    file = models.FileField(
        upload_to="chat/files/",
        null=True,
        blank=True,
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    read_by = models.ManyToManyField(
        User,
        related_name="read_messages",
        blank=True,
    )

    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )

    is_disappearing = models.BooleanField(
        default=False,
        db_index=True,
    )

    disappear_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        ordering = ["timestamp"]

        indexes = [
            BTreeIndex(
                fields=["chatroom", "timestamp"],
                name="message_room_time_idx",
            ),
            BTreeIndex(
                fields=["sender", "timestamp"],
                name="message_sender_time_idx",
            ),
            BTreeIndex(
                fields=["reply_to", "timestamp"],
                name="message_reply_time_idx",
            ),
            BTreeIndex(
                fields=["disappear_at"],
                name="message_disappear_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        duration = self.chatroom.disappearing_messages_duration

        if duration:
            self.is_disappearing = True

            if not self.disappear_at:
                self.disappear_at = timezone.now() + timedelta(seconds=duration)

        else:
            self.is_disappearing = False
            self.disappear_at = None

        super().save(*args, **kwargs)


class MessageReaction(models.Model):
    class Reaction(models.TextChoices):
        LIKE = "like", "Like"
        LOVE = "love", "Love"
        LAUGH = "laugh", "Laugh"
        SURPRISED = "surprised", "Surprised"
        SAD = "sad", "Sad"
        ANGRY = "angry", "Angry"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="reactions",
        db_index=True,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="message_reactions",
        db_index=True,
    )

    reaction = models.CharField(
        max_length=20,
        choices=Reaction.choices,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user"],
                name="unique_message_user_reaction",
            ),
        ]

        indexes = [
            BTreeIndex(
                fields=["message", "reaction"],
                name="reaction_message_type_idx",
            ),
            BTreeIndex(
                fields=["user", "reaction"],
                name="reaction_user_type_idx",
            ),
        ]


class UserStatus(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="chat_status",
    )

    online = models.BooleanField(
        default=False,
        db_index=True,
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    typing = models.BooleanField(
        default=False,
    )

    typing_in = models.ForeignKey(
        ChatRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="typing_users",
    )

    class Meta:
        indexes = [
            BTreeIndex(
                fields=["online", "last_seen"],
                name="userstatus_online_seen_idx",
            ),
        ]


class StatusUpdate(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="status_updates",
    )

    text = models.TextField(
        blank=True,
    )

    image = models.ImageField(
        upload_to="chat/status/",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    expires_at = models.DateTimeField(
        db_index=True,
    )


class StatusView(models.Model):
    status = models.ForeignKey(
        StatusUpdate,
        on_delete=models.CASCADE,
        related_name="views",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="viewed_statuses",
    )

    viewed_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["status", "user"],
                name="unique_status_viewer",
            ),
        ]


class Call(models.Model):
    class CallType(models.TextChoices):
        VOICE = "voice", "Voice"
        VIDEO = "video", "Video"

    class Status(models.TextChoices):
        RINGING = "ringing", "Ringing"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        MISSED = "missed", "Missed"
        ENDED = "ended", "Ended"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    caller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="outgoing_calls",
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="incoming_calls",
    )

    call_type = models.CharField(
        max_length=10,
        choices=CallType.choices,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.RINGING,
        db_index=True,
    )

    sdp_offer = models.JSONField(
        null=True,
        blank=True,
    )

    sdp_answer = models.JSONField(
        null=True,
        blank=True,
    )

    ice_candidates = models.JSONField(
        default=list,
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        indexes = [
            BTreeIndex(
                fields=["caller", "created_at"],
                name="call_caller_created_idx",
            ),
            BTreeIndex(
                fields=["recipient", "created_at"],
                name="call_recipient_created_idx",
            ),
            BTreeIndex(
                fields=["status", "created_at"],
                name="call_status_created_idx",
            ),
        ]