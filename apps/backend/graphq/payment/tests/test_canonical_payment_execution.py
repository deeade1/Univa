from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from graphene.relay import Node

from backend.schema import schema

from payment.canonical.models import (
    Payment,
    PaymentExecution,
)

from payment.canonical.services.execution import PaymentExecutionService


User = get_user_model()


class CanonicalPaymentExecutionGraphQLTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="payer@example.com",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="test-password",
        )

        self.payment = Payment.objects.create(
            reference="PAY-GQL-001",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-001",
            source_reference="EARN-001",
            beneficiary=self.user,
            amount=Decimal("15000.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-001",
        )

        self.payment_global_id = Node.to_global_id(
            "PaymentNode",
            str(self.payment.id),
        )

        self.other_payment = Payment.objects.create(
            reference="PAY-GQL-002",
            direction=Payment.Direction.DISBURSE,
            purpose=Payment.Purpose.EARNING,
            source_type="earning",
            source_id="earning-002",
            source_reference="EARN-002",
            beneficiary=self.other_user,
            amount=Decimal("20000.00"),
            currency="NGN",
            idempotency_key="payment-idempotency-002",
        )

        self.other_payment_global_id = Node.to_global_id(
            "PaymentNode",
            str(self.other_payment.id),
        )

    def graphql_context(self, user):
        request = type(
            "Request",
            (),
            {
                "user": user,
            },
        )()

        return request

    def test_create_payment_execution_requires_authentication(self):
        mutation = """
            mutation CreatePaymentExecution(
                $input: CreatePaymentExecutionInput!
            ) {
                createPaymentExecution(input: $input) {
                    clientMutationId
                    paymentExecution {
                        id
                        reference
                        routeType
                        provider
                        status
                    }
                }
            }
        """

        variables = {
            "input": {
                "paymentId": self.payment_global_id,
                "routeType": "BANK_TRANSFER",
                "provider": "flutterwave",
                "idempotencyKey": "execution-gql-001",
                "clientMutationId": "client-001",
            }
        }

        result = schema.execute(
            mutation,
            variable_values=variables,
            context_value=self.graphql_context(None),
        )

        self.assertIsNotNone(result.errors)

        self.assertIn(
            "Authentication required",
            str(result.errors),
        )

    @patch(
        "graphq.payment.canonical.mutations.PaymentExecutionService.create_execution"
    )
    def test_create_payment_execution_delegates_to_service(
        self,
        mock_create_execution,
    ):
        execution = PaymentExecution(
            payment=self.payment,
            reference="PEX-GQL-001",
            attempt_number=1,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="flutterwave",
            status=PaymentExecution.Status.CREATED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.NOT_REQUIRED
            ),
            idempotency_key="execution-gql-001",
        )

        mock_create_execution.return_value = execution

        mutation = """
            mutation CreatePaymentExecution(
                $input: CreatePaymentExecutionInput!
            ) {
                createPaymentExecution(input: $input) {
                    clientMutationId
                    paymentExecution {
                        id
                        reference
                        routeType
                        provider
                        status
                    }
                }
            }
        """

        variables = {
            "input": {
                "paymentId": self.payment_global_id,
                "routeType": "BANK_TRANSFER",
                "provider": "flutterwave",
                "idempotencyKey": "execution-gql-001",
                "clientMutationId": "client-001",
            }
        }

        result = schema.execute(
            mutation,
            variable_values=variables,
            context_value=self.graphql_context(self.user),
        )

        self.assertIsNone(result.errors, result.errors)

        data = result.data["createPaymentExecution"]

        self.assertEqual(
            data["clientMutationId"],
            "client-001",
        )

        self.assertEqual(
            data["paymentExecution"]["reference"],
            "PEX-GQL-001",
        )

        self.assertEqual(
            data["paymentExecution"]["routeType"],
            "BANK_TRANSFER",
        )

        self.assertEqual(
            data["paymentExecution"]["provider"],
            "flutterwave",
        )

        self.assertEqual(
            data["paymentExecution"]["status"],
            "CREATED",
        )

        mock_create_execution.assert_called_once()

        call_kwargs = mock_create_execution.call_args.kwargs

        self.assertEqual(
            call_kwargs["payment"],
            self.payment,
        )

        self.assertEqual(
            call_kwargs["route_type"],
            "BANK_TRANSFER",
        )

        self.assertEqual(
            call_kwargs["provider"],
            "flutterwave",
        )

        self.assertEqual(
            call_kwargs["idempotency_key"],
            "execution-gql-001",
        )

    def test_authenticated_user_cannot_create_execution_for_unrelated_payment(
        self,
    ):
        mutation = """
            mutation CreatePaymentExecution(
                $input: CreatePaymentExecutionInput!
            ) {
                createPaymentExecution(input: $input) {
                    clientMutationId
                    paymentExecution {
                        id
                        reference
                    }
                }
            }
        """

        variables = {
            "input": {
                "paymentId": self.other_payment_global_id,
                "routeType": "BANK_TRANSFER",
                "provider": "flutterwave",
                "idempotencyKey": "execution-gql-002",
                "clientMutationId": "client-002",
            }
        }

        result = schema.execute(
            mutation,
            variable_values=variables,
            context_value=self.graphql_context(self.user),
        )

        self.assertIsNotNone(result.errors)

        self.assertIn(
            "You do not have access to this payment.",
            str(result.errors),
        )

        self.assertFalse(
            PaymentExecution.objects.filter(
                idempotency_key="execution-gql-002"
            ).exists()
        )

    @patch(
        "graphq.payment.canonical.mutations.PaymentExecutionService.create_execution"
    )
    def test_create_payment_execution_with_payment_instrument(
        self,
        mock_create_execution,
    ):
        from payment.canonical.models import PaymentInstrument

        instrument = PaymentInstrument.objects.create(
            reference="PI-GQL-001",
            owner=self.user,
            instrument_type=PaymentInstrument.InstrumentType.BANK_ACCOUNT,
            institution="Test Bank",
            secure_reference="secure-bank-account-001",
            display_reference="****1234",
            verification_status=(
                PaymentInstrument.VerificationStatus.VERIFIED
            ),
            verified_at=self.payment.created_at,
            status=PaymentInstrument.Status.ACTIVE,
            activated_at=self.payment.created_at,
            can_fund=False,
            can_receive=True,
        )

        instrument_global_id = Node.to_global_id(
            "PaymentInstrumentNode",
            str(instrument.id),
        )

        execution = PaymentExecution(
            payment=self.payment,
            reference="PEX-GQL-002",
            attempt_number=1,
            route_type=PaymentExecution.RouteType.BANK_TRANSFER,
            provider="flutterwave",
            payment_instrument=instrument,
            status=PaymentExecution.Status.CREATED,
            reconciliation_state=(
                PaymentExecution.ReconciliationState.NOT_REQUIRED
            ),
            idempotency_key="execution-gql-003",
        )

        mock_create_execution.return_value = execution

        mutation = """
            mutation CreatePaymentExecution(
                $input: CreatePaymentExecutionInput!
            ) {
                createPaymentExecution(input: $input) {
                    clientMutationId
                    paymentExecution {
                        id
                        reference
                        routeType
                        provider
                    }
                }
            }
        """

        variables = {
            "input": {
                "paymentId": self.payment_global_id,
                "routeType": "BANK_TRANSFER",
                "provider": "flutterwave",
                "paymentInstrumentId": instrument_global_id,
                "idempotencyKey": "execution-gql-003",
                "clientMutationId": "client-003",
            }
        }

        result = schema.execute(
            mutation,
            variable_values=variables,
            context_value=self.graphql_context(self.user),
        )

        self.assertIsNone(result.errors, result.errors)

        mock_create_execution.assert_called_once()

        call_kwargs = mock_create_execution.call_args.kwargs

        self.assertEqual(
            call_kwargs["payment_instrument"],
            instrument,
        )

    def test_invalid_payment_id_returns_error(self):
        mutation = """
            mutation CreatePaymentExecution(
                $input: CreatePaymentExecutionInput!
            ) {
                createPaymentExecution(input: $input) {
                    clientMutationId
                    paymentExecution {
                        id
                    }
                }
            }
        """

        variables = {
            "input": {
                "paymentId": Node.to_global_id(
                    "PaymentNode",
                    "00000000-0000-0000-0000-000000000000",
                ),
                "routeType": "BANK_TRANSFER",
                "provider": "flutterwave",
                "idempotencyKey": "execution-gql-004",
                "clientMutationId": "client-004",
            }
        }

        result = schema.execute(
            mutation,
            variable_values=variables,
            context_value=self.graphql_context(self.user),
        )

        self.assertIsNotNone(result.errors)

        self.assertIn(
            "Payment not found",
            str(result.errors),
        )