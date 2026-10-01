# apps/backend/notifications/tests/test_resolve_recipients.py

"""
Tests for the resolve_recipients function in notification_service.py.

These tests verify that recipient resolution works correctly for all
event types, with special focus on magic link events.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from notifications.events.constants import ACCOUNT_MAGIC_LINK_REQUESTED
from notifications.models.event import NotificationEvent
from notifications.services.notification_service import resolve_recipients


class ResolveRecipientsTestCase(TestCase):
    """Test cases for resolve_recipients function."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="test-password",
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="test-password",
        )
        self.user3 = User.objects.create_user(
            email="user3@example.com",
            password="test-password",
        )

    def create_event(self, **kwargs) -> NotificationEvent:
        """Helper to create a NotificationEvent."""
        defaults = {
            "event_type": "TEST.EVENT",
            "module": "test",
            "object_type": "Test",
            "object_id": "1",
            "payload": {},  # payload is required, cannot be None
        }
        defaults.update(kwargs)
        return NotificationEvent.objects.create(**defaults)

    # =========================================================================
    # MAGIC LINK TESTS
    # =========================================================================

    def test_magic_link_event_resolves_actor(self):
        """Magic link events should resolve to the actor."""
        event = self.create_event(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            actor=self.user1,
            payload={
                "token": "abc123",
                "channel": "email",
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_magic_link_event_with_payload_user_id_fallback(self):
        """Magic link events should use payload user_id if actor is missing."""
        event = self.create_event(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            actor=None,
            payload={
                "user_id": self.user2.pk,
                "token": "abc123",
                "channel": "email",
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user2.pk)

    def test_magic_link_event_with_payload_recipient_id_fallback(self):
        """Magic link events should use payload recipient_id if actor is missing."""
        event = self.create_event(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            actor=None,
            payload={
                "recipient_id": self.user3.pk,
                "token": "abc123",
                "channel": "email",
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user3.pk)

    def test_magic_link_event_actor_takes_precedence_over_payload(self):
        """Actor should take precedence over payload user_id for magic links."""
        event = self.create_event(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            actor=self.user1,
            payload={
                "user_id": self.user2.pk,
                "token": "abc123",
                "channel": "email",
            }
        )

        recipients = resolve_recipients(event)

        # Actor should be the only recipient (user1), not user2
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_magic_link_event_no_actor_no_payload_returns_empty(self):
        """Magic link event with no actor and no payload should return empty."""
        event = self.create_event(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            actor=None,
            payload={},
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 0)

    def test_magic_link_event_invalid_user_id_returns_empty(self):
        """Magic link event with invalid user_id should return empty."""
        event = self.create_event(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            actor=None,
            payload={
                "user_id": 999999,  # Non-existent user
                "token": "abc123",
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 0)

    # =========================================================================
    # GENERAL RECIPIENT RESOLUTION TESTS
    # =========================================================================

    def test_event_with_explicit_recipient(self):
        """
        Events with explicit recipient should resolve to that recipient.
        
        NOTE: NotificationEvent doesn't have a recipient field.
        Recipients are resolved from payload or actor.
        This test uses payload to specify the recipient.
        """
        event = self.create_event(
            payload={
                "recipient_id": self.user1.pk,
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_event_with_recipient_id(self):
        """
        Events with recipient_id in payload should resolve to that user.
        """
        event = self.create_event(
            payload={
                "recipient_id": self.user1.pk,
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_event_with_payload_user_id(self):
        """Events with payload user_id should resolve to that user."""
        event = self.create_event(
            payload={
                "user_id": self.user1.pk,
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_event_with_payload_recipient_id(self):
        """Events with payload recipient_id should resolve to that user."""
        event = self.create_event(
            payload={
                "recipient_id": self.user1.pk,
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_event_with_payload_user_ids(self):
        """Events with payload user_ids should resolve to multiple users."""
        event = self.create_event(
            payload={
                "user_ids": [self.user1.pk, self.user2.pk, self.user3.pk],
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 3)
        recipient_pks = {user.pk for user in recipients}
        self.assertEqual(
            recipient_pks,
            {self.user1.pk, self.user2.pk, self.user3.pk}
        )

    def test_event_with_payload_recipient_ids(self):
        """Events with payload recipient_ids should resolve to multiple users."""
        event = self.create_event(
            payload={
                "recipient_ids": [self.user1.pk, self.user2.pk],
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 2)
        recipient_pks = {user.pk for user in recipients}
        self.assertEqual(
            recipient_pks,
            {self.user1.pk, self.user2.pk}
        )

    def test_event_with_actor_fallback(self):
        """Events should fall back to actor if no other recipient is found."""
        event = self.create_event(
            actor=self.user1,
            payload={},
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_event_with_actor_and_recipient_prefers_recipient(self):
        """
        Events should prefer explicit recipient (in payload) over actor.
        """
        event = self.create_event(
            actor=self.user2,
            payload={
                "recipient_id": self.user1.pk,
            }
        )

        recipients = resolve_recipients(event)

        # Explicit recipient in payload takes precedence
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_event_deduplicates_recipients(self):
        """Events should deduplicate recipients by user ID."""
        event = self.create_event(
            actor=self.user1,
            payload={
                "user_id": self.user1.pk,
                "user_ids": [self.user1.pk, self.user2.pk],
                "recipient_id": self.user1.pk,
                "recipient_ids": [self.user1.pk, self.user2.pk],
            }
        )

        recipients = resolve_recipients(event)

        # Should have user1 and user2, no duplicates
        self.assertEqual(len(recipients), 2)
        recipient_pks = {user.pk for user in recipients}
        self.assertEqual(
            recipient_pks,
            {self.user1.pk, self.user2.pk}
        )

    def test_event_with_no_recipient_sources_returns_empty(self):
        """Events with no recipient sources should return empty list."""
        event = self.create_event(
            actor=None,
            payload={},
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 0)

    def test_event_with_missing_user_id_ignored(self):
        """Events with missing user_id should be ignored."""
        event = self.create_event(
            payload={
                "user_id": None,
                "recipient_id": self.user1.pk,
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_event_with_invalid_user_id_ignored(self):
        """Events with invalid user_id should be ignored."""
        event = self.create_event(
            payload={
                "user_id": 999999,  # Non-existent
                "recipient_id": self.user1.pk,
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    # =========================================================================
    # EDGE CASES
    # =========================================================================

    def test_event_with_empty_payload(self):
        """Events with empty payload should work."""
        event = self.create_event(
            actor=self.user1,
            payload={},
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_event_with_none_payload(self):
        """
        Events with None payload should work.
        
        NOTE: Since payload is NOT NULL in the database,
        we use an empty dict instead of None.
        """
        event = self.create_event(
            actor=self.user1,
            payload={},  # Empty dict instead of None
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_invalid_event_type_raises_error(self):
        """Non-NotificationEvent should raise ValueError."""
        with self.assertRaises(ValueError) as exc:
            resolve_recipients(None)  # type: ignore

        self.assertEqual(
            str(exc.exception),
            "resolve_recipients requires a NotificationEvent."
        )

    def test_event_with_mixed_payload_sources(self):
        """Events with mixed payload sources should resolve correctly."""
        event = self.create_event(
            payload={
                "user_id": self.user1.pk,
                "recipient_ids": [self.user2.pk, self.user3.pk],
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 3)
        recipient_pks = {user.pk for user in recipients}
        self.assertEqual(
            recipient_pks,
            {self.user1.pk, self.user2.pk, self.user3.pk}
        )

    def test_event_with_string_user_ids(self):
        """Events should handle string user IDs (converted to int)."""
        event = self.create_event(
            payload={
                "user_ids": [str(self.user1.pk), str(self.user2.pk)],
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 2)
        recipient_pks = {user.pk for user in recipients}
        self.assertEqual(
            recipient_pks,
            {self.user1.pk, self.user2.pk}
        )

    # =========================================================================
    # PERFORMANCE / INTEGRATION TESTS
    # =========================================================================

    def test_magic_link_event_priority_over_general_actor_fallback(self):
        """
        Magic link events should use the actor even if payload has other IDs.
        This tests that the magic link specific handling doesn't interfere
        with the general actor fallback.
        """
        event = self.create_event(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            actor=self.user1,
            payload={
                "user_id": self.user2.pk,
                "recipient_ids": [self.user3.pk],
            }
        )

        recipients = resolve_recipients(event)

        # Magic link should return ONLY the actor
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)

    def test_non_magic_link_event_with_actor_and_recipient_ids(self):
        """Non-magic-link events should use standard resolution logic."""
        event = self.create_event(
            event_type="ORDER.CREATED",
            actor=self.user1,
            payload={
                "user_id": self.user2.pk,
                "recipient_ids": [self.user3.pk],
            }
        )

        recipients = resolve_recipients(event)

        # Non-magic-link should use standard resolution (payload over actor)
        self.assertEqual(len(recipients), 2)
        recipient_pks = {user.pk for user in recipients}
        self.assertEqual(
            recipient_pks,
            {self.user2.pk, self.user3.pk}
        )

    def test_magic_link_event_with_actor_but_no_valid_payload(self):
        """Magic link events should resolve actor even when payload is invalid."""
        event = self.create_event(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            actor=self.user1,
            payload={
                "user_id": 999999,  # Invalid
                "recipient_id": None,
            }
        )

        recipients = resolve_recipients(event)

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].pk, self.user1.pk)