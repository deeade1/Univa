from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.test import TestCase

from chat.models import ChatRoom, ChatRoomType
from chat.services.room_service import ChatRoomService
from transport.models import ServiceRequest, ServiceProviderProfile


User = get_user_model()


class ChatRoomServiceTestCase(TestCase):
    def make_user(self, email):
        return User.objects.create_user(
            email=email,
            password="StrongTestPassword123!",
        )

    def make_service_request(self, customer, service_type, provider=None):
        return ServiceRequest.objects.create(
            service_type=service_type,
            customer=customer,
            provider=provider,
            pickup_location=Point(7.4951, 9.0579),
        )

    # ============================================================
    # Direct chats
    # ============================================================

    def test_create_direct_chat(self):
        user = self.make_user("user1@example.com")
        other_user = self.make_user("user2@example.com")

        room = ChatRoomService.create_direct_chat(
            user=user,
            other_user=other_user,
        )

        self.assertEqual(room.room_type, ChatRoomType.DIRECT)
        self.assertIsNone(room.service_request_id)
        self.assertEqual(
            set(room.participants.values_list("pk", flat=True)),
            {user.pk, other_user.pk},
        )

    def test_create_direct_chat_reuses_existing_room(self):
        user = self.make_user("user1@example.com")
        other_user = self.make_user("user2@example.com")

        first = ChatRoomService.create_direct_chat(
            user=user,
            other_user=other_user,
        )

        second = ChatRoomService.create_direct_chat(
            user=other_user,
            other_user=user,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ChatRoom.objects.count(), 1)

    def test_create_direct_chat_rejects_self_chat(self):
        user = self.make_user("user1@example.com")

        with self.assertRaises(ValidationError):
            ChatRoomService.create_direct_chat(
                user=user,
                other_user=user,
            )

    # ============================================================
    # Generic groups
    # ============================================================

    def test_create_group_chat(self):
        creator = self.make_user("creator@example.com")
        user2 = self.make_user("user2@example.com")
        user3 = self.make_user("user3@example.com")

        room = ChatRoomService.create_group_chat(
            creator=creator,
            participants=[user2, user3],
            name="Test Group",
        )

        self.assertEqual(room.room_type, ChatRoomType.GROUP)
        self.assertEqual(room.name, "Test Group")
        self.assertEqual(room.admin_id, creator.pk)
        self.assertEqual(room.participants.count(), 3)

    # ============================================================
    # ServiceRequest chats
    # ============================================================

    def test_create_service_request_chat_for_trip(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        room = ChatRoomService.create_for_service_request(
            service_request=service_request,
        )

        self.assertEqual(room.room_type, ChatRoomType.TRIP)
        self.assertEqual(
            room.service_request_id,
            service_request.pk,
        )
        self.assertTrue(
            room.participants.filter(pk=customer.pk).exists()
        )

    def test_create_service_request_chat_for_delivery(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.DELIVERY,
        )

        room = ChatRoomService.create_for_service_request(
            service_request=service_request,
        )

        self.assertEqual(room.room_type, ChatRoomType.DELIVERY)
        self.assertEqual(
            room.service_request_id,
            service_request.pk,
        )

    def test_service_request_chat_is_reused(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        first = ChatRoomService.create_for_service_request(
            service_request=service_request,
        )

        second = ChatRoomService.create_for_service_request(
            service_request=service_request,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            ChatRoom.objects.filter(
                service_request=service_request
            ).count(),
            1,
        )

    # ============================================================
    # Provider membership
    # ============================================================

    def test_service_request_chat_includes_provider_user(self):
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

        room = ChatRoomService.create_for_service_request(
            service_request=service_request,
        )

        participant_ids = set(
            room.participants.values_list("pk", flat=True)
        )

        self.assertEqual(
            participant_ids,
            {customer.pk, provider_user.pk},
        )

    # ============================================================
    # Room type validation
    # ============================================================

    def test_trip_room_requires_trip_service_request(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.DELIVERY,
        )

        with self.assertRaises(ValidationError):
            ChatRoomService.create_for_service_request(
                service_request=service_request,
                room_type=ChatRoomType.TRIP,
            )

    def test_delivery_room_requires_delivery_service_request(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        with self.assertRaises(ValidationError):
            ChatRoomService.create_for_service_request(
                service_request=service_request,
                room_type=ChatRoomType.DELIVERY,
            )

    def test_service_request_chat_rejects_direct_room_type(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        with self.assertRaises(ValidationError):
            ChatRoomService.create_for_service_request(
                service_request=service_request,
                room_type=ChatRoomType.DIRECT,
            )