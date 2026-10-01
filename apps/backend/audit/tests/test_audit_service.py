# apps/backend/audit/tests/test_audit_service.py

from django.contrib.auth import get_user_model
from django.test import TestCase

from audit.constants import AuditAction
from audit.models import AuditLog
from audit.services import audit, record_audit


User = get_user_model()


class AuditServiceTestCase(TestCase):

    def setUp(self):
        self.actor = User.objects.create_user(
            email="actor@example.com",
            password="test-password",
        )

        self.target = User.objects.create_user(
            email="target@example.com",
            password="test-password",
        )

    def test_record_audit_creates_audit_log(self):
        log = record_audit(
            action=AuditAction.ACCOUNT_LOGIN,
            actor=self.actor,
            target_user=self.target,
        )

        self.assertIsInstance(log, AuditLog)
        self.assertEqual(log.action, AuditAction.ACCOUNT_LOGIN)
        self.assertEqual(log.actor, self.actor)
        self.assertEqual(log.target_user, self.target)

    def test_record_audit_persists_data(self):
        log = record_audit(
            action=AuditAction.ACCOUNT_UPDATED,
            actor=self.actor,
            target_user=self.target,
            data={
                "field": "email",
                "old_value": "old@example.com",
                "new_value": "new@example.com",
            },
        )

        self.assertEqual(
            log.data,
            {
                "field": "email",
                "old_value": "old@example.com",
                "new_value": "new@example.com",
            },
        )

    def test_record_audit_accepts_none_actor(self):
        log = record_audit(
            action=AuditAction.ADMIN_ACTION,
            actor=None,
        )

        self.assertIsNone(log.actor)
        self.assertEqual(log.action, AuditAction.ADMIN_ACTION)

    def test_record_audit_accepts_none_target_user(self):
        log = record_audit(
            action=AuditAction.ADMIN_ACTION,
            actor=self.actor,
            target_user=None,
        )

        self.assertEqual(log.actor, self.actor)
        self.assertIsNone(log.target_user)

    def test_record_audit_rejects_missing_action(self):
        with self.assertRaises(ValueError):
            record_audit(
                action="",
                actor=self.actor,
            )

    def test_record_audit_rejects_unknown_action(self):
        with self.assertRaises(ValueError):
            record_audit(
                action="SOME.RANDOM.ACTION",
                actor=self.actor,
            )

    def test_record_audit_rejects_non_mapping_data(self):
        with self.assertRaises(TypeError):
            record_audit(
                action=AuditAction.ACCOUNT_UPDATED,
                actor=self.actor,
                data="invalid",
            )

    def test_record_audit_copies_mapping_data(self):
        original_data = {
            "field": "email",
        }

        log = record_audit(
            action=AuditAction.ACCOUNT_UPDATED,
            actor=self.actor,
            data=original_data,
        )

        original_data["field"] = "phone"

        self.assertEqual(
            log.data,
            {
                "field": "email",
            },
        )

    def test_audit_convenience_api(self):
        log = audit(
            action=AuditAction.ACCOUNT_UPDATED,
            actor=self.actor,
            target_user=self.target,
            field="email",
            old_value="old@example.com",
            new_value="new@example.com",
        )

        self.assertEqual(log.action, AuditAction.ACCOUNT_UPDATED)
        self.assertEqual(log.actor, self.actor)
        self.assertEqual(log.target_user, self.target)

        self.assertEqual(
            log.data,
            {
                "field": "email",
                "old_value": "old@example.com",
                "new_value": "new@example.com",
            },
        )

    def test_timestamp_is_created(self):
        log = audit(
            action=AuditAction.ACCOUNT_LOGIN,
            actor=self.actor,
        )

        self.assertIsNotNone(log.timestamp)