# apps/backend/banking/tests/test_qr_service.py

from decimal import Decimal

from django.core.exceptions import ValidationError

from banking.models.qr_payments import QRCode, QRTransaction
from banking.services.qr_service import QRService
from banking.tests.base import BankingServiceTestBase


class QRServiceTests(BankingServiceTestBase):

    def setUp(self):
        self.fund_account(self.customer_account, "100000.00")
        self.fund_account(self.other_customer_account, "100000.00")

        self.qr_code = QRCode.objects.create(
            qr_id="QR-TEST-001",
            qr_type="STATIC",
            creator=self.other_customer,
            fixed_amount=Decimal("500.00"),
            reference="QRREF-TEST-001",
            max_uses=1,
            max_amount_per_use=Decimal("500.00"),
            is_active=True,
        )

    def test_pay_static_qr_posts_balanced_journal(self):
        self.snapshot(
            self.customer_account, self.other_customer_account
        )
        txn = QRService.pay_via_qr(
            scanner_user=self.customer,
            qr_code=self.qr_code,
            payer_account=self.customer_account,
        )
        self.assert_journal_balanced(txn.journal)
        self.assert_account_moved_by(self.customer_account, "-500.00")
        self.assert_account_moved_by(
            self.other_customer_account, "+500.00"
        )
        self.assert_ledger_sums_to_zero()

    def test_pay_qr_rejects_self_payment(self):
        with self.assertRaises(ValidationError):
            QRService.pay_via_qr(
                scanner_user=self.other_customer,
                qr_code=self.qr_code,
                payer_account=self.other_customer_account,
            )
        self.assert_ledger_sums_to_zero()

    def test_used_up_qr_is_rejected(self):
        QRService.pay_via_qr(
            scanner_user=self.customer,
            qr_code=self.qr_code,
            payer_account=self.customer_account,
        )
        self.qr_code.refresh_from_db()
        with self.assertRaises(ValidationError):
            QRService.pay_via_qr(
                scanner_user=self.customer,
                qr_code=self.qr_code,
                payer_account=self.customer_account,
            )