# apps/backend/banking/tests/test_atm_service.py

from decimal import Decimal

from django.core.exceptions import ValidationError

from banking.services.compliance_service import ATMService
from banking.tests.base import BankingServiceTestBase


class ATMServiceTests(BankingServiceTestBase):

    def setUp(self):
        self.fund_account(self.customer_account, "10000.00")

    def test_withdrawal_posts_account_to_settlement(self):
        self.snapshot(self.customer_account)
        txn = ATMService.process_withdrawal(
            account=self.customer_account,
            amount=Decimal("500.00"),
            user=self.customer,
        )
        self.assertEqual(txn.status, "completed")
        self.assert_journal_balanced(txn.journal)
        self.assert_account_moved_by(self.customer_account, "-500.00")
        self.assert_ledger_sums_to_zero()

    def test_deposit_posts_settlement_to_account(self):
        self.snapshot(self.customer_account)
        txn = ATMService.process_deposit(
            account=self.customer_account,
            amount=Decimal("2000.00"),
            user=self.customer,
        )
        self.assertEqual(txn.status, "completed")
        self.assert_journal_balanced(txn.journal)
        self.assert_account_moved_by(self.customer_account, "+2000.00")
        self.assert_ledger_sums_to_zero()

    def test_withdrawal_rejects_insufficient_funds(self):
        with self.assertRaises(ValidationError):
            ATMService.process_withdrawal(
                account=self.customer_account,
                amount=Decimal("1000000.00"),
                user=self.customer,
            )
        self.assert_ledger_sums_to_zero()