# apps/backend/banking/tests/test_account_service.py

from decimal import Decimal

from django.core.exceptions import ValidationError

from banking.models.core import Account
from banking.models.security import BankingSecurity
from banking.services.account_service import AccountService
from banking.tests.base import BankingServiceTestBase


class AccountServiceTests(BankingServiceTestBase):

    def test_create_account_derives_nuban_from_phone(self):
        # Staff user has no account yet
        account = AccountService.create_account(
            user=self.staff, created_by=self.staff,
        )
        # staff.phone_number = "08099998888"
        self.assertEqual(account.phone_number, "08099998888")
        self.assertEqual(account.nuban_number, "8099998888")
        self.assertEqual(account.status, "ACTIVE")
        self.assertFalse(account.is_system_account)

    def test_create_account_creates_banking_security(self):
        self.assertFalse(
            BankingSecurity.objects.filter(user=self.staff).exists()
        )
        AccountService.create_account(user=self.staff)
        self.assertTrue(
            BankingSecurity.objects.filter(user=self.staff).exists()
        )

    def test_create_account_rejects_duplicate_user(self):
        with self.assertRaises(ValidationError):
            AccountService.create_account(user=self.customer)