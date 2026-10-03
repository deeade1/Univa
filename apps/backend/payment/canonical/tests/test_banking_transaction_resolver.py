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


class BankingTransactionResolverTests(TestCase):
    """
    Contract tests for BankingTransactionResolver.

    The resolver is responsible only for resolving an existing
    Banking Transaction from the explicit Banking transaction
    reference stored on a PaymentExecution.

    It must NOT:

        - create Banking transactions
        - mutate Banking transactions
        - mutate PaymentExecution
        - mutate Payment
        - reconcile evidence
        - create reconciliation evidence
        - match by amount
        - match by account
        - match by status
        - match by narration
        - call external providers
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="banking-resolver@example.com",
        )

        self.bank = Bank.objects.create(
            name="Resolver Test Bank",
            code="RTB001",
        )

        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            phone_number="08000000001",
            nuban_number="0000000001",
            account_name="Resolver Test User",
        )

        self.payment = Payment.objects.create(
            reference="PAY-RESOLVER-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-resolver-001",
            source_reference="EARNING-RESOLVER-001",
            beneficiary=self.user,
            amount=Decimal("1000.00"),
            currency="NGN",
            idempotency_key="resolver-payment-001",
        )

        self.execution = PaymentExecution.objects.create(
            reference="EXEC-RESOLVER-001",
            payment=self.payment,
            attempt_number=1,
            idempotency_key="resolver-execution-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            status=PaymentExecution.Status.PROCESSING,
            banking_transaction_reference="BANK-TXN-RESOLVER-001",
        )

        self.transaction = Transaction.objects.create(
            reference="BANK-TXN-RESOLVER-001",
            account=self.account,
            amount=Decimal("1000.00"),
            type=Transaction.TRANSFER,
            status=Transaction.SUCCESS,
            narration="Resolver test transaction",
            provider_reference="PROVIDER-RESOLVER-001",
        )

    def test_resolves_transaction_by_exact_banking_reference(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        result = BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.assertEqual(
            result,
            self.transaction,
        )

    def test_resolution_uses_transaction_reference_not_provider_reference(
        self,
    ):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        self.execution.banking_transaction_reference = (
            "BANK-TXN-RESOLVER-001"
        )
        self.execution.save(
            update_fields=["banking_transaction_reference"]
        )

        result = BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.assertEqual(
            result.reference,
            "BANK-TXN-RESOLVER-001",
        )

    def test_missing_banking_transaction_is_rejected(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        self.execution.banking_transaction_reference = (
            "BANK-TXN-DOES-NOT-EXIST"
        )
        self.execution.save(
            update_fields=["banking_transaction_reference"]
        )

        with self.assertRaises(ValidationError):
            BankingTransactionResolver.resolve(
                execution=self.execution,
            )

    def test_blank_banking_transaction_reference_is_rejected(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        self.execution.banking_transaction_reference = ""
        self.execution.save(
            update_fields=["banking_transaction_reference"]
        )

        with self.assertRaises(ValidationError):
            BankingTransactionResolver.resolve(
                execution=self.execution,
            )

    def test_none_banking_transaction_reference_is_rejected(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        self.execution.banking_transaction_reference = None
        self.execution.save(
            update_fields=["banking_transaction_reference"]
        )

        with self.assertRaises(ValidationError):
            BankingTransactionResolver.resolve(
                execution=self.execution,
            )

    def test_non_execution_is_rejected(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        with self.assertRaises(ValidationError):
            BankingTransactionResolver.resolve(
                execution=object(),
            )

    def test_none_execution_is_rejected(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        with self.assertRaises(ValidationError):
            BankingTransactionResolver.resolve(
                execution=None,
            )

    def test_unsaved_execution_is_rejected(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        execution = PaymentExecution(
            payment=self.payment,
            attempt_number=2,
            idempotency_key="resolver-unsaved-execution-001",
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="test_provider",
            status=PaymentExecution.Status.PROCESSING,
            banking_transaction_reference=(
                "BANK-TXN-RESOLVER-001"
            ),
        )

        with self.assertRaises(ValidationError):
            BankingTransactionResolver.resolve(
                execution=execution,
            )

    def test_amount_is_not_used_as_identity(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        self.transaction.amount = Decimal("500.00")
        self.transaction.save(
            update_fields=["amount"]
        )

        result = BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.assertEqual(
            result,
            self.transaction,
        )

    def test_status_is_not_used_as_identity(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        self.transaction.status = Transaction.FAILED
        self.transaction.save(
            update_fields=["status"]
        )

        result = BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.assertEqual(
            result,
            self.transaction,
        )

    def test_account_is_not_used_as_identity(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        other_user = User.objects.create_user(
            email="banking-resolver-other@example.com",
        )

        other_account = Account.objects.create(
            user=other_user,
            bank=self.bank,
            phone_number="08000000002",
            nuban_number="0000000002",
            account_name="Other Resolver User",
        )

        self.transaction.account = other_account
        self.transaction.save(
            update_fields=["account"]
        )

        result = BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.assertEqual(
            result,
            self.transaction,
        )

    def test_narration_is_not_used_as_identity(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        self.transaction.narration = "Completely different narration"
        self.transaction.save(
            update_fields=["narration"]
        )

        result = BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.assertEqual(
            result,
            self.transaction,
        )

    def test_provider_reference_is_not_used_as_identity(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        self.execution.banking_transaction_reference = (
            "BANK-TXN-RESOLVER-001"
        )
        self.execution.save(
            update_fields=["banking_transaction_reference"]
        )

        self.transaction.provider_reference = (
            "COMPLETELY-DIFFERENT-PROVIDER-REFERENCE"
        )
        self.transaction.save(
            update_fields=["provider_reference"]
        )

        result = BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.assertEqual(
            result,
            self.transaction,
        )

    def test_resolver_does_not_mutate_execution(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        before_reference = (
            self.execution.banking_transaction_reference
        )
        before_status = self.execution.status

        BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.execution.refresh_from_db()

        self.assertEqual(
            self.execution.banking_transaction_reference,
            before_reference,
        )
        self.assertEqual(
            self.execution.status,
            before_status,
        )

    def test_resolver_does_not_mutate_transaction(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        before_status = self.transaction.status
        before_amount = self.transaction.amount
        before_reference = self.transaction.reference

        BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.transaction.refresh_from_db()

        self.assertEqual(
            self.transaction.status,
            before_status,
        )
        self.assertEqual(
            self.transaction.amount,
            before_amount,
        )
        self.assertEqual(
            self.transaction.reference,
            before_reference,
        )

    def test_resolver_does_not_create_transaction(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        before_count = Transaction.objects.count()

        BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.assertEqual(
            Transaction.objects.count(),
            before_count,
        )

    def test_resolver_returns_existing_transaction_instance(self):
        from payment.canonical.services.banking_transaction_resolver import (
            BankingTransactionResolver,
        )

        result = BankingTransactionResolver.resolve(
            execution=self.execution,
        )

        self.assertEqual(
            result.pk,
            self.transaction.pk,
        )

        self.assertIsInstance(
            result,
            Transaction,
        )
