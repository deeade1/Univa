from datetime import timedelta


from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from chat.models import ChatRoom, ChatRoomType, Message
from chat.services.message_service import ChatMessageService


User = get_user_model()


class ChatMessageServiceTestCase(TestCase):
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
        disappearing_messages_duration=None,
    ):
        room = ChatRoom.objects.create(
            name="Test Room",
            room_type=room_type,
            admin=admin,
            disappearing_messages_duration=(
                disappearing_messages_duration
            ),
        )

        if participants:
            room.participants.add(*participants)

        return room

    def make_image(self, name="test.jpg"):
        return SimpleUploadedFile(
            name,
            b"fake-image-content",
            content_type="image/jpeg",
        )

    def make_file(self, name="test.txt"):
        return SimpleUploadedFile(
            name,
            b"test-file-content",
            content_type="text/plain",
        )

    # ============================================================
    # send_message
    # ============================================================

    def test_send_message_creates_text_message(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_message(
            room=room,
            sender=sender,
            text="Hello world",
        )

        self.assertEqual(message.chatroom_id, room.pk)
        self.assertEqual(message.sender_id, sender.pk)
        self.assertEqual(message.text, "Hello world")

    def test_send_message_creates_image_message(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])
        image = self.make_image()

        message = ChatMessageService.send_message(
            room=room,
            sender=sender,
            image=image,
        )

        self.assertTrue(bool(message.image))
        self.assertEqual(message.sender_id, sender.pk)

    def test_send_message_creates_file_message(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])
        uploaded_file = self.make_file()

        message = ChatMessageService.send_message(
            room=room,
            sender=sender,
            file=uploaded_file,
        )

        self.assertTrue(bool(message.file))
        self.assertEqual(message.sender_id, sender.pk)

    def test_send_message_rejects_empty_message(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        with self.assertRaises(ValidationError):
            ChatMessageService.send_message(
                room=room,
                sender=sender,
                text="   ",
            )

        self.assertEqual(Message.objects.count(), 0)

    def test_send_message_rejects_non_participant(self):
        sender = self.make_user("sender@example.com")
        other_user = self.make_user("other@example.com")
        room = self.make_room(participants=[other_user])

        with self.assertRaises(PermissionDenied):
            ChatMessageService.send_message(
                room=room,
                sender=sender,
                text="Hello",
            )

        self.assertEqual(Message.objects.count(), 0)

    def test_send_message_rejects_unauthenticated_sender(self):
        room = self.make_room()

        class AnonymousUser:
            is_authenticated = False

        with self.assertRaises(PermissionDenied):
            ChatMessageService.send_message(
                room=room,
                sender=AnonymousUser(),
                text="Hello",
            )

        self.assertEqual(Message.objects.count(), 0)

    # ============================================================
    # send_text_message
    # ============================================================

    def test_send_text_message_creates_message(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Hello",
        )

        self.assertEqual(message.text, "Hello")
        self.assertEqual(message.sender_id, sender.pk)

    def test_send_text_message_rejects_empty_text(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        with self.assertRaises(ValidationError):
            ChatMessageService.send_text_message(
                room=room,
                sender=sender,
                text="",
            )

        self.assertEqual(Message.objects.count(), 0)

    def test_send_text_message_rejects_whitespace_text(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        with self.assertRaises(ValidationError):
            ChatMessageService.send_text_message(
                room=room,
                sender=sender,
                text="   ",
            )

        self.assertEqual(Message.objects.count(), 0)

    # ============================================================
    # send_media_message
    # ============================================================

    def test_send_media_message_accepts_image(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_media_message(
            room=room,
            sender=sender,
            image=self.make_image(),
        )

        self.assertTrue(bool(message.image))

    def test_send_media_message_accepts_file(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_media_message(
            room=room,
            sender=sender,
            file=self.make_file(),
        )

        self.assertTrue(bool(message.file))

    def test_send_media_message_accepts_media_with_text(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_media_message(
            room=room,
            sender=sender,
            image=self.make_image(),
            text="Here is the image",
        )

        self.assertEqual(message.text, "Here is the image")
        self.assertTrue(bool(message.image))

    def test_send_media_message_rejects_missing_media(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        with self.assertRaises(ValidationError):
            ChatMessageService.send_media_message(
                room=room,
                sender=sender,
            )

        self.assertEqual(Message.objects.count(), 0)

    # ============================================================
    # Authorization
    # ============================================================

    def test_require_sender_access_accepts_participant(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        result = ChatMessageService.require_sender_access(
            room=room,
            sender=sender,
        )

        self.assertIsNone(result)

    def test_require_sender_access_rejects_non_participant(self):
        sender = self.make_user("sender@example.com")
        member = self.make_user("member@example.com")
        room = self.make_room(participants=[member])

        with self.assertRaises(PermissionDenied):
            ChatMessageService.require_sender_access(
                room=room,
                sender=sender,
            )

    def test_require_sender_access_rejects_unauthenticated_user(self):
        room = self.make_room()

        class AnonymousUser:
            is_authenticated = False

        with self.assertRaises(PermissionDenied):
            ChatMessageService.require_sender_access(
                room=room,
                sender=AnonymousUser(),
            )

    def test_require_sender_access_rejects_none(self):
        room = self.make_room()

        with self.assertRaises(PermissionDenied):
            ChatMessageService.require_sender_access(
                room=room,
                sender=None,
            )

    # ============================================================
    # Replies
    # ============================================================

    def test_send_message_can_reply_to_message_in_same_room(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        original = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Original",
        )

        reply = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Reply",
            reply_to=original,
        )

        self.assertEqual(reply.reply_to_id, original.pk)

    def test_send_message_rejects_reply_from_different_room(self):
        sender = self.make_user("sender@example.com")
        room1 = self.make_room(participants=[sender])
        room2 = self.make_room(participants=[sender])

        original = ChatMessageService.send_text_message(
            room=room1,
            sender=sender,
            text="Original",
        )

        with self.assertRaises(ValidationError):
            ChatMessageService.send_text_message(
                room=room2,
                sender=sender,
                text="Invalid reply",
                reply_to=original,
            )

    def test_validate_reply_accepts_message_in_same_room(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Message",
        )

        result = ChatMessageService.validate_reply(
            room=room,
            reply_to=message,
        )

        self.assertIsNone(result)

    def test_validate_reply_rejects_message_from_different_room(self):
        sender = self.make_user("sender@example.com")
        room1 = self.make_room(participants=[sender])
        room2 = self.make_room(participants=[sender])

        message = ChatMessageService.send_text_message(
            room=room1,
            sender=sender,
            text="Message",
        )

        with self.assertRaises(ValidationError):
            ChatMessageService.validate_reply(
                room=room2,
                reply_to=message,
            )

    def test_get_replies_returns_replies_in_timestamp_order(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        original = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Original",
        )

        first = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="First reply",
            reply_to=original,
        )

        second = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Second reply",
            reply_to=original,
        )

        replies = list(
            ChatMessageService.get_replies(original)
        )

        self.assertEqual(
            [message.pk for message in replies],
            [first.pk, second.pk],
        )

    # ============================================================
    # Retrieval
    # ============================================================

    def test_get_room_messages_returns_oldest_first(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        first = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="First",
        )

        second = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Second",
        )

        messages = list(
            ChatMessageService.get_room_messages(room=room)
        )

        self.assertEqual(
            [message.pk for message in messages],
            [first.pk, second.pk],
        )

    def test_get_room_messages_limit_returns_requested_number(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="First",
        )
        ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Second",
        )
        ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Third",
        )

        messages = list(
            ChatMessageService.get_room_messages(
                room=room,
                limit=2,
            )
        )

        self.assertEqual(len(messages), 2)

    def test_get_room_messages_rejects_non_positive_limit(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        for limit in (0, -1):
            with self.assertRaises(ValidationError):
                ChatMessageService.get_room_messages(
                    room=room,
                    limit=limit,
                )

    def test_get_room_messages_without_limit_returns_all_messages(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        for index in range(3):
            ChatMessageService.send_text_message(
                room=room,
                sender=sender,
                text=f"Message {index}",
            )

        messages = list(
            ChatMessageService.get_room_messages(room=room)
        )

        self.assertEqual(len(messages), 3)

    def test_get_message_returns_requested_message(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Hello",
        )

        result = ChatMessageService.get_message(
            message_id=message.pk,
        )

        self.assertEqual(result.pk, message.pk)
        self.assertEqual(result.text, "Hello")

    def test_get_message_raises_for_unknown_message(self):
        from uuid import uuid4

        with self.assertRaises(Message.DoesNotExist):
            ChatMessageService.get_message(
                message_id=uuid4(),
            )

    # ============================================================
    # Read receipts
    # ============================================================

    def test_mark_as_read_adds_user_to_read_by(self):
        sender = self.make_user("sender@example.com")
        reader = self.make_user("reader@example.com")

        room = self.make_room(
            participants=[sender, reader],
        )

        message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Hello",
        )

        ChatMessageService.mark_as_read(
            message=message,
            user=reader,
        )

        self.assertTrue(
            message.read_by.filter(pk=reader.pk).exists()
        )

    def test_mark_as_read_rejects_unauthenticated_user(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Hello",
        )

        class AnonymousUser:
            is_authenticated = False

        with self.assertRaises(PermissionDenied):
            ChatMessageService.mark_as_read(
                message=message,
                user=AnonymousUser(),
            )

    def test_mark_as_read_rejects_non_participant(self):
        sender = self.make_user("sender@example.com")
        other_user = self.make_user("other@example.com")

        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Hello",
        )

        with self.assertRaises(PermissionDenied):
            ChatMessageService.mark_as_read(
                message=message,
                user=other_user,
            )

    def test_mark_room_as_read_marks_all_messages(self):
        sender = self.make_user("sender@example.com")
        reader = self.make_user("reader@example.com")

        room = self.make_room(
            participants=[sender, reader],
        )

        first = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="First",
        )

        second = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Second",
        )

        ChatMessageService.mark_room_as_read(
            room=room,
            user=reader,
        )

        self.assertTrue(
            first.read_by.filter(pk=reader.pk).exists()
        )
        self.assertTrue(
            second.read_by.filter(pk=reader.pk).exists()
        )

    def test_mark_room_as_read_rejects_non_participant(self):
        sender = self.make_user("sender@example.com")
        other_user = self.make_user("other@example.com")

        room = self.make_room(participants=[sender])

        ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Hello",
        )

        with self.assertRaises(PermissionDenied):
            ChatMessageService.mark_room_as_read(
                room=room,
                user=other_user,
            )

    # ============================================================
    # Deletion
    # ============================================================

    def test_delete_message_allows_sender(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Delete me",
        )

        ChatMessageService.delete_message(
            message=message,
            user=sender,
        )

        self.assertFalse(
            Message.objects.filter(pk=message.pk).exists()
        )

    def test_delete_message_rejects_non_sender(self):
        sender = self.make_user("sender@example.com")
        other_user = self.make_user("other@example.com")

        room = self.make_room(
            participants=[sender, other_user],
        )

        message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Do not delete",
        )

        with self.assertRaises(PermissionDenied):
            ChatMessageService.delete_message(
                message=message,
                user=other_user,
            )

        self.assertTrue(
            Message.objects.filter(pk=message.pk).exists()
        )

    # ============================================================
    # Disappearing messages
    # ============================================================

    def test_send_message_uses_room_disappearing_duration(self):
        sender = self.make_user("sender@example.com")

        duration = 3600
        duration_delta = timedelta(seconds=duration)

        room = self.make_room(
            participants=[sender],
            disappearing_messages_duration=duration,
        )

        before = timezone.now()

        message = ChatMessageService.send_text_message(
            room=room,
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


    def test_get_expired_messages_returns_expired_messages(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Expired",
        )

        Message.objects.filter(pk=message.pk).update(
            is_disappearing=True,
            disappear_at=timezone.now() - timedelta(minutes=1),
        )

        expired = ChatMessageService.get_expired_messages()

        self.assertTrue(
            expired.filter(pk=message.pk).exists()
        )

    def test_get_expired_messages_excludes_future_messages(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Not expired",
        )

        Message.objects.filter(pk=message.pk).update(
            is_disappearing=True,
            disappear_at=timezone.now() + timedelta(hours=1),
        )

        expired = ChatMessageService.get_expired_messages()

        self.assertFalse(
            expired.filter(pk=message.pk).exists()
        )

    def test_delete_expired_messages_deletes_only_expired_messages(self):
        sender = self.make_user("sender@example.com")
        room = self.make_room(participants=[sender])

        expired_message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Expired",
        )

        future_message = ChatMessageService.send_text_message(
            room=room,
            sender=sender,
            text="Future",
        )

        Message.objects.filter(pk=expired_message.pk).update(
            is_disappearing=True,
            disappear_at=timezone.now() - timedelta(minutes=1),
        )

        Message.objects.filter(pk=future_message.pk).update(
            is_disappearing=True,
            disappear_at=timezone.now() + timedelta(hours=1),
        )

        count = ChatMessageService.delete_expired_messages()

        self.assertEqual(count, 1)

        self.assertFalse(
            Message.objects.filter(pk=expired_message.pk).exists()
        )
        self.assertTrue(
            Message.objects.filter(pk=future_message.pk).exists()
        )

    def test_delete_expired_messages_returns_zero_when_none_expired(self):
        count = ChatMessageService.delete_expired_messages()

        self.assertEqual(count, 0)