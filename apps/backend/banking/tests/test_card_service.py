# apps/backend/banking/tests/test_card_service.py

from decimal import Decimal

from django.core.exceptions import ValidationError

from banking.models.cards import CardBrand, VirtualCard
from banking.services.card_service import CardService
from banking.tests.base import BankingServiceTestBase


class CardServiceTests(BankingServiceTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.brand = CardBrand.objects.create(
            name="Visa", code="VISA", is_active=True,
        )

    def setUp(self):
        self.fund_account(self.customer_account, "50000.00")

    def test_issue_card_encrypts_and_decrypts(self):
        card = CardService.issue_virtual_card(
            user=self.customer,
            account=self.customer_account,
            card_type="VISA",
        )
        self.assertEqual(card.status, "ACTIVE")
        number = CardService.decrypt_field(card.card_number)
        self.assertEqual(len(number), 16)
        self.assertEqual(number[-4:], card.last_four)
        self.assertEqual(card.daily_usage, Decimal("0.00"))

    def test_authorize_posts_hold_journal(self):
        card = CardService.issue_virtual_card(
            user=self.customer,
            account=self.customer_account,
            card_type="VISA",
        )
        self.snapshot(self.customer_account)
        auth = CardService.authorize_transaction(
            card=card,
            account=self.customer_account,
            amount=Decimal("5000.00"),
            merchant_name="Test Merchant",
            merchant_category_code="5411",
        )
        self.assert_journal_balanced(auth.journal)
        self.assertEqual(auth.status, "AUTHORIZED")
        self.assert_account_moved_by(self.customer_account, "-5000.00")
        self.assert_ledger_sums_to_zero()

    def test_settle_moves_suspense_to_settlement(self):
        card = CardService.issue_virtual_card(
            user=self.customer,
            account=self.customer_account,
            card_type="VISA",
        )
        auth = CardService.authorize_transaction(
            card=card,
            account=self.customer_account,
            amount=Decimal("5000.00"),
            merchant_name="Test Merchant",
            merchant_category_code="5411",
        )
        self.snapshot(self.customer_account)
        settled = CardService.settle_transaction(auth_code=auth.auth_code)
        self.assertEqual(settled.status, "SETTLED")
        self.assert_journal_balanced(settled.journal)
        # Customer's balance is unchanged by settlement
        self.assert_account_moved_by(self.customer_account, "0.00")
        self.assert_ledger_sums_to_zero()

    def test_reverse_releases_hold(self):
        card = CardService.issue_virtual_card(
            user=self.customer,
            account=self.customer_account,
            card_type="VISA",
        )
        auth = CardService.authorize_transaction(
            card=card,
            account=self.customer_account,
            amount=Decimal("5000.00"),
            merchant_name="Test Merchant",
            merchant_category_code="5411",
        )
        self.snapshot(self.customer_account)
        reversed_txn = CardService.reverse_authorization(
            auth_code=auth.auth_code,
            account=self.customer_account,
        )
        self.assertEqual(reversed_txn.status, "REVERSED")
        self.assert_journal_balanced(reversed_txn.journal)
        # Reversal credits the customer back
        self.assert_account_moved_by(self.customer_account, "+5000.00")
        self.assert_ledger_sums_to_zero()

    def test_authorize_rejects_amount_over_per_transaction_limit(self):
        card = CardService.issue_virtual_card(
            user=self.customer,
            account=self.customer_account,
            card_type="VISA",
            per_transaction_limit=Decimal("1000.00"),
        )
        with self.assertRaises(ValidationError):
            CardService.authorize_transaction(
                card=card,
                account=self.customer_account,
                amount=Decimal("100000.00"),
                merchant_name="Test Merchant",
                merchant_category_code="5411",
            )
        self.assert_ledger_sums_to_zero()