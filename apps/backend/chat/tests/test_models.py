from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from chat.models import (
    Call,
    ChatRoom,
    ChatRoomType,
    Message,
    MessageReaction,
    StatusUpdate,
    StatusView,
    UserStatus,
)
from transport.models import ServiceRequest, ServiceProviderProfile, StopPoint


User = get_user_model()


class ChatModelTestCase(TestCase):
    def make_user(self, email):
        return User.objects.create_user(
            email=email,
            password="StrongTestPassword123!",
        )

    def make_room(
        self,
        *,
        room_type=ChatRoomType.GROUP,
        participants=None,
        admin=None,
        service_request=None,
        disappearing_messages_duration=None,
    ):
        room = ChatRoom.objects.create(
            name="Test Room",
            room_type=room_type,
            admin=admin,
            service_request=service_request,
            disappearing_messages_duration=(
                disappearing_messages_duration
            ),
        )

        if participants:
            room.participants.add(*participants)

        return room

    def make_service_request(
        self,
        *,
        customer,
        service_type,
        provider=None,
    ):
        pickup_stop = StopPoint.objects.create(
            name="Test Pickup",
            location="Test Pickup",
            latitude=Decimal("9.057900"),
            longitude=Decimal("7.495100"),
        )

        return ServiceRequest.objects.create(
            service_type=service_type,
            customer=customer,
            provider=provider,
            pickup_location=pickup_stop,
        )

    # ============================================================
    # ChatRoom creation and identity
    # ============================================================

    def test_chat_room_uses_uuid_primary_key(self):
        room = self.make_room()

        self.assertIsNotNone(room.pk)
        self.assertEqual(room.pk.version, 4)

    def test_chat_room_string_returns_name(self):
        room = self.make_room()

        self.assertEqual(str(room), "Test Room")

    def test_chat_room_string_falls_back_to_type_and_id(self):
        room = self.make_room()
        room.name = ""
        room.save(update_fields=["name"])

        self.assertIn(
            room.get_room_type_display(),
            str(room),
        )
        self.assertIn(str(room.pk), str(room))

    # ============================================================
    # ChatRoom type/context validation
    # ============================================================

    def test_direct_room_without_service_request_is_valid(self):
        room = self.make_room(
            room_type=ChatRoomType.DIRECT,
        )

        room.full_clean()

    def test_group_room_without_service_request_is_valid(self):
        room = self.make_room(
            room_type=ChatRoomType.GROUP,
        )

        room.full_clean()

    def test_service_request_room_requires_service_request(self):
        room = ChatRoom(
            name="Transport Chat",
            room_type=ChatRoomType.SERVICE_REQUEST,
        )

        with self.assertRaises(ValidationError):
            room.full_clean()

    def test_trip_room_requires_service_request(self):
        room = ChatRoom(
            name="Trip Chat",
            room_type=ChatRoomType.TRIP,
        )

        with self.assertRaises(ValidationError):
            room.full_clean()

    def test_delivery_room_requires_service_request(self):
        room = ChatRoom(
            name="Delivery Chat",
            room_type=ChatRoomType.DELIVERY,
        )

        with self.assertRaises(ValidationError):
            room.full_clean()

    def test_direct_room_rejects_service_request_context(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        room = ChatRoom(
            name="Invalid Direct",
            room_type=ChatRoomType.DIRECT,
            service_request=service_request,
        )

        with self.assertRaises(ValidationError):
            room.full_clean()

    def test_group_room_rejects_service_request_context(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        room = ChatRoom(
            name="Invalid Group",
            room_type=ChatRoomType.GROUP,
            service_request=service_request,
        )

        with self.assertRaises(ValidationError):
            room.full_clean()

    def test_trip_room_accepts_trip_service_request(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.INTERSTATE,
        )

        self.assertTrue(service_request.is_trip)

        room = ChatRoom(
            name="Trip Chat",
            room_type=ChatRoomType.TRIP,
            service_request=service_request,
        )

        room.full_clean()

    def test_delivery_room_accepts_delivery_service_request(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.DELIVERY,
        )

        self.assertTrue(service_request.is_delivery)

        room = ChatRoom(
            name="Delivery Chat",
            room_type=ChatRoomType.DELIVERY,
            service_request=service_request,
        )

        room.full_clean()
    
    def test_trip_room_rejects_non_trip_service_request(self):
        customer = self.make_user("customer@example.com")
        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.DELIVERY,
        )

        room = self.make_room(
            room_type=ChatRoomType.TRIP,
            service_request=service_request,
        )

        with self.assertRaises(ValidationError):
            room.clean()


    def test_delivery_room_rejects_non_delivery_service_request(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        room = ChatRoom(
            name="Invalid Delivery Chat",
            room_type=ChatRoomType.DELIVERY,
            service_request=service_request,
        )

        with self.assertRaises(ValidationError):
            room.full_clean()

    # ============================================================
    # ChatRoom properties
    # ============================================================

    def test_direct_room_is_not_group(self):
        room = self.make_room(
            room_type=ChatRoomType.DIRECT,
        )

        self.assertFalse(room.is_group)

    def test_generic_group_room_is_group(self):
        room = self.make_room(
            room_type=ChatRoomType.GROUP,
        )

        self.assertTrue(room.is_group)

    def test_trip_room_is_group(self):
        room = self.make_room(
            room_type=ChatRoomType.TRIP,
        )

        self.assertTrue(room.is_group)

    def test_delivery_room_is_group(self):
        room = self.make_room(
            room_type=ChatRoomType.DELIVERY,
        )

        self.assertTrue(room.is_group)

    def test_transport_chat_property(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        room = self.make_room(
            room_type=ChatRoomType.SERVICE_REQUEST,
            service_request=service_request,
        )

        self.assertTrue(room.is_transport_chat)

    def test_non_transport_chat_property(self):
        room = self.make_room()

        self.assertFalse(room.is_transport_chat)

    def test_room_type_properties(self):
        service_request = self.make_service_request(
            customer=self.make_user("customer@example.com"),
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        service_room = self.make_room(
            room_type=ChatRoomType.SERVICE_REQUEST,
            service_request=service_request,
        )

        self.assertTrue(service_room.is_service_request_chat)
        self.assertFalse(service_room.is_trip_chat)
        self.assertFalse(service_room.is_delivery_chat)

    def test_trip_room_property(self):
        service_request = self.make_service_request(
            customer=self.make_user("customer@example.com"),
            service_type=ServiceRequest.ServiceType.INTERSTATE,
        )

        room = self.make_room(
            room_type=ChatRoomType.TRIP,
            service_request=service_request,
        )

        self.assertTrue(room.is_trip_chat)
        self.assertFalse(room.is_delivery_chat)

    def test_delivery_room_property(self):
        service_request = self.make_service_request(
            customer=self.make_user("customer@example.com"),
            service_type=ServiceRequest.ServiceType.DELIVERY,
        )

        room = self.make_room(
            room_type=ChatRoomType.DELIVERY,
            service_request=service_request,
        )

        self.assertTrue(room.is_delivery_chat)
        self.assertFalse(room.is_trip_chat)

    def test_transport_service_type_returns_service_request_type(self):
        service_request = self.make_service_request(
            customer=self.make_user("customer@example.com"),
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        room = self.make_room(
            room_type=ChatRoomType.SERVICE_REQUEST,
            service_request=service_request,
        )

        self.assertEqual(
            room.transport_service_type,
            service_request.service_type,
        )

    def test_transport_service_type_returns_none_without_context(self):
        room = self.make_room()

        self.assertIsNone(room.transport_service_type)

    # ============================================================
    # ChatRoom participant helpers
    # ============================================================

    def test_add_participant(self):
        user = self.make_user("user@example.com")
        room = self.make_room()

        room.add_participant(user)

        self.assertTrue(room.has_participant(user))

    def test_remove_participant(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        room.remove_participant(user)

        self.assertFalse(room.has_participant(user))

    def test_has_participant_returns_false_for_unrelated_user(self):
        member = self.make_user("member@example.com")
        other = self.make_user("other@example.com")

        room = self.make_room(participants=[member])

        self.assertFalse(room.has_participant(other))

    def test_has_participant_returns_false_for_unauthenticated_user(self):
        room = self.make_room()

        class AnonymousUser:
            is_authenticated = False

        self.assertFalse(
            room.has_participant(AnonymousUser())
        )

    # ============================================================
    # Transport helpers
    # ============================================================

    def test_get_transport_customer(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        room = self.make_room(
            room_type=ChatRoomType.SERVICE_REQUEST,
            service_request=service_request,
        )

        self.assertEqual(
            room.get_transport_customer(),
            customer,
        )

    def test_get_transport_provider(self):
        customer = self.make_user("customer@example.com")
        provider_user = self.make_user("provider@example.com")

        provider = ServiceProviderProfile.objects.create(
            user=provider_user,
            provider_type="driver",
        )

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
            provider=provider,
        )

        room = self.make_room(
            room_type=ChatRoomType.SERVICE_REQUEST,
            service_request=service_request,
        )

        self.assertEqual(
            room.get_transport_provider(),
            provider,
        )

    def test_get_transport_customer_returns_none_without_context(self):
        room = self.make_room()

        self.assertIsNone(room.get_transport_customer())

    def test_get_transport_provider_returns_none_without_context(self):
        room = self.make_room()

        self.assertIsNone(room.get_transport_provider())

    def test_get_expected_transport_users(self):
        customer = self.make_user("customer@example.com")
        provider_user = self.make_user("provider@example.com")

        provider = ServiceProviderProfile.objects.create(
            user=provider_user,
            provider_type="driver",
        )

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
            provider=provider,
        )

        room = self.make_room(
            room_type=ChatRoomType.SERVICE_REQUEST,
            service_request=service_request,
        )

        users = room.get_expected_transport_users()

        self.assertEqual(
            set(users.values_list("pk", flat=True)),
            {customer.pk, provider_user.pk},
        )

    def test_get_expected_transport_users_without_context_is_empty(self):
        room = self.make_room()

        self.assertEqual(
            room.get_expected_transport_users().count(),
            0,
        )

    # ============================================================
    # Message disappearing behavior
    # ============================================================

    def test_message_without_duration_is_not_disappearing(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = Message.objects.create(
            chatroom=room,
            sender=sender,
            text="Permanent",
        )

        self.assertFalse(message.is_disappearing)
        self.assertIsNone(message.disappear_at)

    def test_message_uses_room_disappearing_duration(self):
        sender = self.make_user("sender@example.com")

        duration = 3600
        duration_delta = timedelta(seconds=duration)

        room = self.make_room(
            participants=[sender],
            disappearing_messages_duration=duration,
        )

        before = timezone.now()

        message = Message.objects.create(
            chatroom=room,
            sender=sender,
            text="Temporary",
        )

        after = timezone.now()

        self.assertTrue(message.is_disappearing)
        self.assertIsNotNone(message.disappear_at)

        self.assertGreaterEqual(
            message.disappear_at,
            before + duration_delta,
        )
        self.assertLessEqual(
            message.disappear_at,
            after + duration_delta,
        )

    def test_message_preserves_existing_disappear_at(self):
        sender = self.make_user("sender@example.com")

        duration = 3600

        room = self.make_room(
            participants=[sender],
            disappearing_messages_duration=duration,
        )

        existing_expiry = timezone.now() + timedelta(hours=2)

        message = Message(
            chatroom=room,
            sender=sender,
            text="Temporary",
            disappear_at=existing_expiry,
        )

        message.save()

        self.assertEqual(
            message.disappear_at,
            existing_expiry,
        )

    # ============================================================
    # MessageReaction
    # ============================================================

    def test_message_reaction_can_be_created(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        message = Message.objects.create(
            chatroom=room,
            sender=user,
            text="Hello",
        )

        reaction = MessageReaction.objects.create(
            message=message,
            user=user,
            reaction=MessageReaction.Reaction.LIKE,
        )

        self.assertEqual(
            reaction.reaction,
            MessageReaction.Reaction.LIKE,
        )

    def test_message_reaction_is_unique_per_user_and_message(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        message = Message.objects.create(
            chatroom=room,
            sender=user,
            text="Hello",
        )

        MessageReaction.objects.create(
            message=message,
            user=user,
            reaction=MessageReaction.Reaction.LIKE,
        )

        with self.assertRaises(Exception):
            MessageReaction.objects.create(
                message=message,
                user=user,
                reaction=MessageReaction.Reaction.LOVE,
            )

    def test_different_users_can_react_to_same_message(self):
        user1 = self.make_user("user1@example.com")
        user2 = self.make_user("user2@example.com")

        room = self.make_room(
            participants=[user1, user2],
        )

        message = Message.objects.create(
            chatroom=room,
            sender=user1,
            text="Hello",
        )

        MessageReaction.objects.create(
            message=message,
            user=user1,
            reaction=MessageReaction.Reaction.LIKE,
        )

        MessageReaction.objects.create(
            message=message,
            user=user2,
            reaction=MessageReaction.Reaction.LOVE,
        )

        self.assertEqual(message.reactions.count(), 2)

    # ============================================================
    # UserStatus
    # ============================================================

    def test_user_status_defaults(self):
        user = self.make_user("user@example.com")

        status = UserStatus.objects.create(user=user)

        self.assertFalse(status.online)
        self.assertFalse(status.typing)
        self.assertIsNone(status.last_seen)
        self.assertIsNone(status.typing_in)

    def test_user_status_can_reference_typing_room(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        status = UserStatus.objects.create(
            user=user,
            typing=True,
            typing_in=room,
        )

        self.assertTrue(status.typing)
        self.assertEqual(status.typing_in_id, room.pk)

    # ============================================================
    # StatusUpdate / StatusView
    # ============================================================

    def test_status_update_can_be_created(self):
        user = self.make_user("user@example.com")

        status = StatusUpdate.objects.create(
            user=user,
            text="Available",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        self.assertEqual(status.user_id, user.pk)
        self.assertEqual(status.text, "Available")

    def test_status_view_can_be_created(self):
        owner = self.make_user("owner@example.com")
        viewer = self.make_user("viewer@example.com")

        status = StatusUpdate.objects.create(
            user=owner,
            text="Hello",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        status_view = StatusView.objects.create(
            status=status,
            user=viewer,
        )

        self.assertEqual(status_view.status_id, status.pk)
        self.assertEqual(status_view.user_id, viewer.pk)

    def test_status_view_is_unique_per_status_and_user(self):
        owner = self.make_user("owner@example.com")
        viewer = self.make_user("viewer@example.com")

        status = StatusUpdate.objects.create(
            user=owner,
            text="Hello",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        StatusView.objects.create(
            status=status,
            user=viewer,
        )

        with self.assertRaises(Exception):
            StatusView.objects.create(
                status=status,
                user=viewer,
            )

    # ============================================================
    # Call
    # ============================================================

    def test_call_defaults_to_ringing(self):
        caller = self.make_user("caller@example.com")
        recipient = self.make_user("recipient@example.com")

        call = Call.objects.create(
            caller=caller,
            recipient=recipient,
            call_type=Call.CallType.VOICE,
        )

        self.assertEqual(
            call.status,
            Call.Status.RINGING,
        )

    def test_call_stores_sdp_and_ice_data(self):
        caller = self.make_user("caller@example.com")
        recipient = self.make_user("recipient@example.com")

        call = Call.objects.create(
            caller=caller,
            recipient=recipient,
            call_type=Call.CallType.VIDEO,
            sdp_offer={"type": "offer"},
            sdp_answer={"type": "answer"},
            ice_candidates=[
                {"candidate": "candidate:test"},
            ],
        )

        self.assertEqual(
            call.sdp_offer,
            {"type": "offer"},
        )
        self.assertEqual(
            call.sdp_answer,
            {"type": "answer"},
        )
        self.assertEqual(
            call.ice_candidates,
            [{"candidate": "candidate:test"}],
        )

    def test_call_can_store_start_and_end_times(self):
        caller = self.make_user("caller@example.com")
        recipient = self.make_user("recipient@example.com")

        started = timezone.now()
        ended = started + timedelta(minutes=5)

        call = Call.objects.create(
            caller=caller,
            recipient=recipient,
            call_type=Call.CallType.VOICE,
            status=Call.Status.ENDED,
            started_at=started,
            ended_at=ended,
        )

        self.assertEqual(call.started_at, started)
        self.assertEqual(call.ended_at, ended)

    # ============================================================
    # Cascade / SET_NULL behavior
    # ============================================================

    def test_message_is_deleted_when_chatroom_is_deleted(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        message = Message.objects.create(
            chatroom=room,
            sender=user,
            text="Hello",
        )

        message_id = message.pk

        room.delete()

        self.assertFalse(
            Message.objects.filter(pk=message_id).exists()
        )

    def test_reply_is_set_null_when_parent_message_is_deleted(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        parent = Message.objects.create(
            chatroom=room,
            sender=user,
            text="Parent",
        )

        reply = Message.objects.create(
            chatroom=room,
            sender=user,
            text="Reply",
            reply_to=parent,
        )

        parent.delete()

        reply.refresh_from_db()

        self.assertIsNone(reply.reply_to_id)

    def test_typing_room_is_set_null_when_room_is_deleted(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        status = UserStatus.objects.create(
            user=user,
            typing=True,
            typing_in=room,
        )

        room.delete()

        status.refresh_from_db()

        self.assertIsNone(status.typing_in_id)