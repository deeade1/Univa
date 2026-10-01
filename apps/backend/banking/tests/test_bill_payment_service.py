# apps/backend/banking/tests/test_bill_payment_service.py

from decimal import Decimal

from django.core.exceptions import ValidationError

from banking.models.bill_payments import BillPayment, Biller, BillCategory
from banking.services.bill_payment_service import BillPaymentService
from banking.tests.base import BankingServiceTestBase


class BillPaymentServiceTests(BankingServiceTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        category = BillCategory.objects.create(
            name="Electricity", slug="electricity",
        )
        cls.biller = Biller.objects.create(
            name="Ikeja Electric",
            slug="ikeja-electric",
            category=category,
            code="IKEDC",
            fee_percentage=Decimal("1.00"),
            fee_fixed=Decimal("0.00"),
            min_amount=Decimal("100.00"),
            max_amount=Decimal("500000.00"),
            is_active=True,
        )

    def setUp(self):
        self.fund_account(self.customer_account, "100000.00")
        self.snapshot(self.customer_account)

    def test_pay_bill_posts_balanced_journals(self):
        service = BillPaymentService()
        payment = service.pay_bill(
            user=self.customer,
            source_account=self.customer_account,
            biller=self.biller,
            amount=Decimal("10000.00"),
            customer_id="METER-12345",
            bill_type="electricity",
        )

        # Business record
        self.assertEqual(payment.status, BillPayment.SUCCESS)
        self.assertEqual(payment.amount, Decimal("10000.00"))
        self.assertEqual(payment.fee, Decimal("100.00"))

        # Journals
        self.assert_journal_balanced(payment.journal)
        self.assert_journal_balanced(payment.fee_journal)

        # Ledger movement
        self.assert_account_moved_by(
            self.customer_account,
            "-10100.00",
        )
        self.assert_ledger_sums_to_zero()

    def test_pay_bill_rejects_insufficient_funds(self):
        service = BillPaymentService()
        with self.assertRaises(ValidationError):
            service.pay_bill(
                user=self.customer,
                source_account=self.customer_account,
                biller=self.biller,
                amount=Decimal("1000000.00"),
                customer_id="METER-12345",
                bill_type="electricity",
            )
        self.assert_ledger_sums_to_zero()

    def test_pay_bill_rejects_other_users_account(self):
        service = BillPaymentService()
        with self.assertRaises(ValidationError):
            service.pay_bill(
                user=self.customer,
                source_account=self.other_customer_account,
                biller=self.biller,
                amount=Decimal("1000.00"),
                customer_id="METER-12345",
                bill_type="electricity",
            )
        self.assert_ledger_sums_to_zero()