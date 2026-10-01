# apps/backend/banking/tests/test_merchant_service.py

from decimal import Decimal

from django.utils import timezone

from banking.models.merchant import Merchant
from banking.services.merchant_service import MerchantService
from banking.tests.base import BankingServiceTestBase


class MerchantServiceTests(BankingServiceTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.merchant = Merchant.objects.create(
            user=cls.other_customer,
            business_name="Test Shop",
            business_type="SMALL_BUSINESS",
            business_email="shop@test.univa",
            business_phone="08033334444",
            business_address="1 Test St",
            business_state="Lagos",
            business_city="Ikeja",
            settlement_account=cls.other_customer_account,
            settlement_bank=cls.bank,
            transaction_fee_percentage=Decimal("1.50"),
            daily_transaction_limit=Decimal("1000000.00"),
            monthly_transaction_limit=Decimal("5000000.00"),
            verification_status="VERIFIED",
            is_active=True,
        )

    def setUp(self):
        self.fund_account(self.customer_account, "10000.00")
        self.snapshot(
            self.customer_account, self.other_customer_account
        )

    def test_sale_posts_principal_and_fee_journals(self):
        mt = MerchantService.record_sale(
            merchant=self.merchant,
            customer=self.customer,
            customer_account=self.customer_account,
            amount=Decimal("1000.00"),
        )
        self.assert_journal_balanced(mt.journal)
        self.assertEqual(mt.fee, Decimal("15.00"))
        self.assertEqual(mt.net_amount, Decimal("985.00"))
        self.assert_account_moved_by(self.customer_account, "-1000.00")
        self.assert_ledger_sums_to_zero()

    def test_settlement_moves_suspense_to_merchant(self):
        mt = MerchantService.record_sale(
            merchant=self.merchant,
            customer=self.customer,
            customer_account=self.customer_account,
            amount=Decimal("1000.00"),
        )
        self.snapshot(
            self.customer_account, self.other_customer_account
        )
        result = MerchantService.process_settlements(
            merchant=self.merchant
        )
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["total_amount"], Decimal("985.00"))
        mt.refresh_from_db()
        self.assertTrue(mt.is_settled)
        self.assert_journal_balanced(mt.settled_journal)
        self.assert_account_moved_by(
            self.other_customer_account, "+985.00"
        )
        self.assert_ledger_sums_to_zero()

    def test_merchant_total_volume_is_computed(self):
        self.assertEqual(self.merchant.total_volume, Decimal("0.00"))
        MerchantService.record_sale(
            merchant=self.merchant,
            customer=self.customer,
            customer_account=self.customer_account,
            amount=Decimal("500.00"),
        )
        self.assertEqual(self.merchant.total_volume, Decimal("500.00"))
        self.assertEqual(self.merchant.total_transactions, 1)
        self.assertEqual(self.merchant.successful_transactions, 1)