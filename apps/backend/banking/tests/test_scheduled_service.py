# apps/backend/banking/tests/test_scheduled_service.py

from decimal import Decimal

from banking.models.scheduled import InternationalTransfer, RemittanceProvider
from banking.services.international_transfer_service import (
    InternationalTransferService,
)
from banking.tests.base import BankingServiceTestBase


class InternationalTransferServiceTests(BankingServiceTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.provider = RemittanceProvider.objects.create(
            name="Western Union",
            provider_code="WESTERN_UNION",
            supported_countries=["US"],
            supported_currencies=["USD"],
            transfer_methods=["BANK_DEPOSIT"],
            min_amount=Decimal("10.00"),
            max_amount=Decimal("1000000.00"),
            daily_limit=Decimal("5000000.00"),
            is_active=True,
        )

    def setUp(self):
        self.fund_account(self.customer_account, "100000.00")
        self.snapshot(self.customer_account)

    def test_initiate_posts_principal_and_fee_journals(self):
        transfer = InternationalTransferService.initiate_transfer(
            sender=self.customer,
            source_account=self.customer_account,
            provider=self.provider,
            transfer_type="SEND",
            source_amount=Decimal("10000.00"),
            source_currency="NGN",
            target_currency="USD",
            exchange_rate=Decimal("0.000667"),
            payout_method="BANK_DEPOSIT",
            recipient_name="John Doe",
            recipient_phone="08033334444",
            provider_fee=Decimal("5.00"),
            platform_fee=Decimal("100.00"),
        )
        self.assert_journal_balanced(transfer.journal)
        self.assert_journal_balanced(transfer.fee_journal)
        self.assertEqual(transfer.status, "PENDING")
        self.assert_account_moved_by(self.customer_account, "-10100.00")
        self.assert_ledger_sums_to_zero()