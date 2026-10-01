from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from chat.models import ChatRoom, ChatRoomType
from chat.services.participant_service import ChatParticipantService
from transport.models import ServiceRequest, ServiceProviderProfile, StopPoint
from decimal import Decimal



User = get_user_model()


class ChatParticipantServiceTestCase(TestCase):
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
    ):
        room = ChatRoom.objects.create(
            name="Test Room",
            room_type=room_type,
            admin=admin,
            service_request=service_request,
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
    # Membership detection
    # ============================================================

    def test_is_participant_returns_true_for_room_member(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        self.assertTrue(
            ChatParticipantService.is_participant(
                room=room,
                user=user,
            )
        )

    def test_is_participant_returns_false_for_non_member(self):
        member = self.make_user("member@example.com")
        other_user = self.make_user("other@example.com")

        room = self.make_room(participants=[member])

        self.assertFalse(
            ChatParticipantService.is_participant(
                room=room,
                user=other_user,
            )
        )

    def test_is_participant_returns_false_for_unauthenticated_user(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        class AnonymousUser:
            is_authenticated = False

        self.assertFalse(
            ChatParticipantService.is_participant(
                room=room,
                user=AnonymousUser(),
            )
        )

    def test_require_participant_accepts_room_member(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        self.assertTrue(
            ChatParticipantService.require_participant(
                room=room,
                user=user,
            )
        )

    def test_require_participant_rejects_non_member(self):
        member = self.make_user("member@example.com")
        other_user = self.make_user("other@example.com")

        room = self.make_room(participants=[member])

        with self.assertRaises(PermissionDenied):
            ChatParticipantService.require_participant(
                room=room,
                user=other_user,
            )

    # ============================================================
    # Adding participants
    # ============================================================

    def test_add_participant_adds_user(self):
        user = self.make_user("user@example.com")
        room = self.make_room()

        ChatParticipantService.add_participant(
            room=room,
            user=user,
        )

        self.assertTrue(
            room.participants.filter(pk=user.pk).exists()
        )

    def test_add_participant_rejects_none(self):
        room = self.make_room()

        with self.assertRaises(ValidationError):
            ChatParticipantService.add_participant(
                room=room,
                user=None,
            )

    def test_add_participant_rejects_third_user_in_direct_chat(self):
        user1 = self.make_user("user1@example.com")
        user2 = self.make_user("user2@example.com")
        user3 = self.make_user("user3@example.com")

        room = self.make_room(
            room_type=ChatRoomType.DIRECT,
            participants=[user1, user2],
        )

        with self.assertRaises(ValidationError):
            ChatParticipantService.add_participant(
                room=room,
                user=user3,
            )

        self.assertEqual(room.participants.count(), 2)

    def test_add_participants_adds_multiple_users(self):
        user1 = self.make_user("user1@example.com")
        user2 = self.make_user("user2@example.com")
        user3 = self.make_user("user3@example.com")

        room = self.make_room()

        ChatParticipantService.add_participants(
            room=room,
            users=[user1, user2, user3],
        )

        self.assertEqual(room.participants.count(), 3)

    def test_add_participants_with_empty_users_does_nothing(self):
        room = self.make_room()

        result = ChatParticipantService.add_participants(
            room=room,
            users=[],
        )

        self.assertEqual(result.pk, room.pk)
        self.assertEqual(room.participants.count(), 0)

    def test_add_participants_rejects_more_than_two_users_in_direct_chat(self):
        user1 = self.make_user("user1@example.com")
        user2 = self.make_user("user2@example.com")
        user3 = self.make_user("user3@example.com")

        room = self.make_room(
            room_type=ChatRoomType.DIRECT,
            participants=[user1],
        )

        with self.assertRaises(ValidationError):
            ChatParticipantService.add_participants(
                room=room,
                users=[user2, user3],
            )

        self.assertEqual(room.participants.count(), 1)

    # ============================================================
    # Removing participants
    # ============================================================

    def test_remove_participant_removes_group_member(self):
        user = self.make_user("user@example.com")
        room = self.make_room(participants=[user])

        ChatParticipantService.remove_participant(
            room=room,
            user=user,
        )

        self.assertFalse(
            room.participants.filter(pk=user.pk).exists()
        )

    def test_remove_participant_does_nothing_for_non_member(self):
        user = self.make_user("user@example.com")
        other_user = self.make_user("other@example.com")

        room = self.make_room(participants=[user])

        result = ChatParticipantService.remove_participant(
            room=room,
            user=other_user,
        )

        self.assertEqual(result.pk, room.pk)
        self.assertEqual(room.participants.count(), 1)

    def test_remove_participant_rejects_direct_chat_member(self):
        user1 = self.make_user("user1@example.com")
        user2 = self.make_user("user2@example.com")

        room = self.make_room(
            room_type=ChatRoomType.DIRECT,
            participants=[user1, user2],
        )

        with self.assertRaises(ValidationError):
            ChatParticipantService.remove_participant(
                room=room,
                user=user1,
            )

        self.assertEqual(room.participants.count(), 2)

    def test_remove_participant_rejects_group_admin(self):
        admin = self.make_user("admin@example.com")
        member = self.make_user("member@example.com")

        room = self.make_room(
            room_type=ChatRoomType.GROUP,
            participants=[admin, member],
            admin=admin,
        )

        with self.assertRaises(ValidationError):
            ChatParticipantService.remove_participant(
                room=room,
                user=admin,
            )

        self.assertTrue(
            room.participants.filter(pk=admin.pk).exists()
        )

    # ============================================================
    # Administration
    # ============================================================

    def test_set_admin_requires_participant(self):
        current_admin = self.make_user("admin@example.com")
        member = self.make_user("member@example.com")

        room = self.make_room(
            participants=[current_admin, member],
            admin=current_admin,
        )

        ChatParticipantService.set_admin(
            room=room,
            user=member,
        )

        room.refresh_from_db()

        self.assertEqual(room.admin_id, member.pk)

    def test_set_admin_rejects_non_participant(self):
        admin = self.make_user("admin@example.com")
        other_user = self.make_user("other@example.com")

        room = self.make_room(
            participants=[admin],
            admin=admin,
        )

        with self.assertRaises(ValidationError):
            ChatParticipantService.set_admin(
                room=room,
                user=other_user,
            )

        room.refresh_from_db()

        self.assertEqual(room.admin_id, admin.pk)

    def test_require_admin_accepts_room_admin(self):
        admin = self.make_user("admin@example.com")

        room = self.make_room(
            participants=[admin],
            admin=admin,
        )

        self.assertTrue(
            ChatParticipantService.require_admin(
                room=room,
                user=admin,
            )
        )

    def test_require_admin_rejects_non_admin(self):
        admin = self.make_user("admin@example.com")
        member = self.make_user("member@example.com")

        room = self.make_room(
            participants=[admin, member],
            admin=admin,
        )

        with self.assertRaises(PermissionDenied):
            ChatParticipantService.require_admin(
                room=room,
                user=member,
            )

    # ============================================================
    # ServiceRequest eligibility
    # ============================================================

    def test_get_expected_service_request_users_returns_customer(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        users = ChatParticipantService.get_expected_service_request_users(
            service_request
        )

        self.assertEqual(
            {user.pk for user in users},
            {customer.pk},
        )

    def test_get_expected_service_request_users_returns_customer_and_provider(self):
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

        users = ChatParticipantService.get_expected_service_request_users(
            service_request
        )

        self.assertEqual(
            {user.pk for user in users},
            {customer.pk, provider_user.pk},
        )

    def test_can_join_service_request_chat_accepts_customer(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        self.assertTrue(
            ChatParticipantService.can_join_service_request_chat(
                service_request=service_request,
                user=customer,
            )
        )

    def test_can_join_service_request_chat_rejects_unrelated_user(self):
        customer = self.make_user("customer@example.com")
        other_user = self.make_user("other@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        self.assertFalse(
            ChatParticipantService.can_join_service_request_chat(
                service_request=service_request,
                user=other_user,
            )
        )

    def test_require_service_request_chat_access_accepts_customer(self):
        customer = self.make_user("customer@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        self.assertTrue(
            ChatParticipantService.require_service_request_chat_access(
                service_request=service_request,
                user=customer,
            )
        )

    def test_require_service_request_chat_access_rejects_unrelated_user(self):
        customer = self.make_user("customer@example.com")
        other_user = self.make_user("other@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        with self.assertRaises(PermissionDenied):
            ChatParticipantService.require_service_request_chat_access(
                service_request=service_request,
                user=other_user,
            )

    # ============================================================
    # ServiceRequest participant synchronization
    # ============================================================

    def test_sync_service_request_participants_adds_customer_and_provider(self):
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
            room_type=ChatRoomType.TRIP,
            service_request=service_request,
        )

        ChatParticipantService.sync_service_request_participants(
            room=room,
        )

        self.assertEqual(
            set(room.participants.values_list("pk", flat=True)),
            {customer.pk, provider_user.pk},
        )

    def test_sync_service_request_participants_includes_additional_users(self):
        customer = self.make_user("customer@example.com")
        additional_user = self.make_user("additional@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        room = self.make_room(
            room_type=ChatRoomType.TRIP,
            service_request=service_request,
        )

        ChatParticipantService.sync_service_request_participants(
            room=room,
            additional_users=[additional_user],
        )

        self.assertEqual(
            set(room.participants.values_list("pk", flat=True)),
            {customer.pk, additional_user.pk},
        )

    def test_sync_service_request_participants_is_additive(self):
        customer = self.make_user("customer@example.com")
        existing_user = self.make_user("existing@example.com")

        service_request = self.make_service_request(
            customer=customer,
            service_type=ServiceRequest.ServiceType.TAXI,
        )

        room = self.make_room(
            room_type=ChatRoomType.TRIP,
            participants=[existing_user],
            service_request=service_request,
        )

        ChatParticipantService.sync_service_request_participants(
            room=room,
        )

        self.assertEqual(
            set(room.participants.values_list("pk", flat=True)),
            {customer.pk, existing_user.pk},
        )

    def test_sync_service_request_participants_rejects_room_without_service_request(self):
        user = self.make_user("user@example.com")
        room = self.make_room(
            room_type=ChatRoomType.GROUP,
            participants=[user],
        )

        with self.assertRaises(ValidationError):
            ChatParticipantService.sync_service_request_participants(
                room=room,
            )