# apps/backend/banking/tests/test_insurance_service.py

from decimal import Decimal

from django.core.exceptions import ValidationError

from banking.models.insurance import (
    InsuranceClaim,
    InsurancePolicy,
    InsuranceProduct,
    InsuranceProvider,
)
from banking.services.insurance_service import InsuranceService
from banking.tests.base import BankingServiceTestBase


class InsuranceServiceTests(BankingServiceTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.provider = InsuranceProvider.objects.create(
            name="Test Insurer", code="TESTINS", is_active=True,
        )
        cls.product = InsuranceProduct.objects.create(
            provider=cls.provider,
            name="Motor Basic",
            slug="motor-basic-test",
            insurance_type="MOTOR",
            description="Test product",
            coverage_amount_min=Decimal("100000.00"),
            coverage_amount_max=Decimal("5000000.00"),
            premium_min=Decimal("5000.00"),
            premium_max=Decimal("250000.00"),
            payment_frequency="ONE_TIME",
            min_tenure_months=6,
            max_tenure_months=36,
            default_tenure_months=12,
        )

    def setUp(self):
        self.fund_account(self.customer_account, "100000.00")

    def test_purchase_posts_balanced_journal(self):
        self.snapshot(self.customer_account)
        policy = InsuranceService.purchase_policy(
            user=self.customer,
            product=self.product,
            source_account=self.customer_account,
            coverage_amount=Decimal("500000.00"),
            tenure_months=12,
        )
        self.assert_journal_balanced(policy.journal)
        self.assertEqual(policy.premium_amount, Decimal("25000.00"))
        self.assert_account_moved_by(self.customer_account, "-25000.00")
        self.assert_ledger_sums_to_zero()

    def test_claim_payout_posts_balanced_journal(self):
        policy = InsuranceService.purchase_policy(
            user=self.customer,
            product=self.product,
            source_account=self.customer_account,
            coverage_amount=Decimal("500000.00"),
            tenure_months=12,
        )

        claim = InsuranceClaim.objects.create(
            policy=policy,
            user=self.customer,
            claim_number="CLM-TEST-001",
            claim_amount=Decimal("100000.00"),
            incident_date=policy.start_date,
            incident_description="Test",
            status="APPROVED",
            approved_amount=Decimal("100000.00"),
        )

        self.snapshot(self.customer_account)
        claim = InsuranceService.pay_claim(
            claim=claim,
            destination_account=self.customer_account,
        )
        self.assert_journal_balanced(claim.journal)
        self.assertEqual(claim.paid_amount, Decimal("100000.00"))
        self.assert_account_moved_by(self.customer_account, "+100000.00")
        self.assert_ledger_sums_to_zero()

    def test_policy_totals_are_computed(self):
        policy = InsuranceService.purchase_policy(
            user=self.customer,
            product=self.product,
            source_account=self.customer_account,
            coverage_amount=Decimal("500000.00"),
            tenure_months=12,
        )
        self.assertEqual(policy.total_claimed, Decimal("0.00"))
        self.assertEqual(policy.total_paid, Decimal("0.00"))

        InsuranceClaim.objects.create(
            policy=policy,
            user=self.customer,
            claim_number="CLM-COMP-001",
            claim_amount=Decimal("50000.00"),
            incident_date=policy.start_date,
            incident_description="Test",
            status="APPROVED",
            approved_amount=Decimal("50000.00"),
        )
        self.assertEqual(policy.total_claimed, Decimal("50000.00"))