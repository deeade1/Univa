# payment/canonical/tests/test_banking_evidence.py

"""
Tests for the Banking → ReconciliationEvidence adapter.

Architectural boundary
----------------------

Banking owns its financial transaction records.

Payment owns reconciliation semantics.

This adapter translates an existing Banking Transaction into
ReconciliationEvidence.

The adapter must NOT:

    - create Banking transactions
    - mutate Banking transactions
    - mutate PaymentExecution
    - mutate Payment
    - reconcile evidence
    - execute lifecycle transitions
    - synchronize Payment state
    - call providers
    - create reconciliation records

Canonical flow:

    Banking Transaction
            ↓
    BankingTransactionEvidenceAdapter
            ↓
    ReconciliationEvidence
            ↓
    ReconciliationService
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User

from banking.models.core import Account, Bank
from banking.models.payments import Transaction

from payment.canonical.models import (
    Payment,
    PaymentExecution,
)

from payment.canonical.services.banking_evidence import (
    BankingTransactionEvidenceAdapter,
)

from payment.canonical.services.reconciliation import (
    ReconciliationEvidence,
)

class BankingTransactionEvidenceAdapterMappingTests(TestCase):
    """Verify Banking transaction → reconciliation evidence mapping."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="banking-mapping@example.com",
        )

        self.bank = self._create_bank()

        self.account = self._create_account()

        self.payment = Payment.objects.create(
            reference="PAY-BANK-MAPPING-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.OTHER,
            source_type="test",
            source_id="source-002",
            source_reference="SOURCE-002",
            beneficiary=self.user,
            amount=Decimal("1000.00"),
            currency="NGN",
            idempotency_key="idem-bank-mapping-001",
        )

        self.execution = PaymentExecution.objects.create(
            payment=self.payment,
            reference="EXEC-BANK-MAPPING-001",
            attempt_number=1,
            idempotency_key="exec-idem-bank-mapping-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test-bank",
            status=PaymentExecution.Status.CREATED,
        )

        self.transaction = self._create_transaction(
            status=Transaction.SUCCESS,
        )

    def _create_bank(self):
        return Bank.objects.create(
            code="TESTBANK",
            name="Test Bank",
        )

    def _create_account(self):
        return Account.objects.create(
            user=self.user,
            bank=self.bank,
            phone_number="08000000002",
            nuban_number="1000000002",
            account_name="Banking Mapping Test",
        )

    def _create_transaction(
        self,
        *,
        status,
        amount=Decimal("1000.00"),
        provider_reference="BANK-PROVIDER-002",
        narration="Bank transfer",
        fee=Decimal("0.00"),
        balance_after=Decimal("9000.00"),
    ):
        return Transaction.objects.create(
            account=self.account,
            amount=amount,
            type=Transaction.TRANSFER,
            status=status,
            narration=narration,
            fee=fee,
            balance_after=balance_after,
            provider_reference=provider_reference,
        )

    def test_success_maps_to_completed(self):
        transaction = self._create_transaction(
            status=Transaction.SUCCESS,
        )

        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.status,
            PaymentExecution.Status.COMPLETED,
        )

    def test_failed_maps_to_failed(self):
        transaction = self._create_transaction(
            status=Transaction.FAILED,
        )

        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.status,
            PaymentExecution.Status.FAILED,
        )

    def test_pending_maps_to_pending(self):
        transaction = self._create_transaction(
            status=Transaction.PENDING,
        )

        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.status,
            PaymentExecution.Status.PENDING,
        )

    def test_reversed_is_rejected(self):
        transaction = self._create_transaction(
            status=Transaction.REVERSED,
        )

        with self.assertRaises(ValidationError):
            BankingTransactionEvidenceAdapter.to_evidence(
                transaction=transaction,
                execution=self.execution,
            )

    def test_source_is_banking(self):
        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=self.transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.source,
            "BANKING",
        )

    def test_amount_comes_from_transaction(self):
        transaction = self._create_transaction(
            status=Transaction.SUCCESS,
            amount=Decimal("750.00"),
        )

        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.amount,
            Decimal("750.00"),
        )

    def test_currency_comes_from_payment_execution(self):
        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=self.transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.currency,
            "NGN",
        )

    def test_reference_comes_from_transaction_reference(self):
        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=self.transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.reference,
            self.transaction.reference,
        )

    def test_provider_reference_becomes_external_event_id(self):
        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=self.transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.external_event_id,
            "BANK-PROVIDER-002",
        )

    def test_blank_provider_reference_produces_empty_external_event_id(self):
        transaction = self._create_transaction(
            status=Transaction.SUCCESS,
            provider_reference="",
        )

        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.external_event_id,
            "",
        )

    def test_metadata_contains_transaction_type(self):
        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=self.transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.metadata["transaction_type"],
            Transaction.TRANSFER,
        )

    def test_metadata_contains_narration(self):
        transaction = self._create_transaction(
            status=Transaction.SUCCESS,
            narration="Driver payout",
        )

        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.metadata["narration"],
            "Driver payout",
        )

    def test_metadata_contains_fee(self):
        transaction = self._create_transaction(
            status=Transaction.SUCCESS,
            fee=Decimal("50.00"),
        )

        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.metadata["fee"],
            "50.00",
        )

    def test_metadata_contains_balance_after(self):
        transaction = self._create_transaction(
            status=Transaction.SUCCESS,
            balance_after=Decimal("12345.67"),
        )

        evidence = BankingTransactionEvidenceAdapter.to_evidence(
            transaction=transaction,
            execution=self.execution,
        )

        self.assertEqual(
            evidence.metadata["balance_after"],
            "12345.67",
        )
