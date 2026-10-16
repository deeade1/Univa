"""
Focused GraphQL tests for the canonical Payment boundary.

These tests verify that GraphQL:

    - exposes the canonical Payment node
    - resolves authenticated payments
    - does not expose unauthenticated payments
    - delegates creation to PaymentService
    - does not directly create Payment records
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from graphene.relay import Node
from graphene.test import Client

from accounts.models import User

from backend.schema import schema

from payment.canonical.models import Payment


def make_context(user):
    return SimpleNamespace(
        user=user,
    )


class CanonicalPaymentGraphQLTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="payment-graphql@example.com",
            password="TestPassword123!",
            is_active=True,
        )

        self.other_user = User.objects.create_user(
            email="other-payment-graphql@example.com",
            password="TestPassword123!",
            is_active=True,
        )

        self.client = Client(schema)


class PaymentQueryTests(CanonicalPaymentGraphQLTestCase):

    def create_payment(
        self,
        *,
        payer,
        beneficiary=None,
        reference="PAY-GRAPHQL-001",
        idempotency_key="idem-graphql-001",
    ):
        return Payment.objects.create(
            reference=reference,
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="test",
            source_id="source-001",
            payer=payer,
            beneficiary=beneficiary,
            amount=Decimal("100.00"),
            currency="NGN",
            status=Payment.Status.PENDING,
            idempotency_key=idempotency_key,
        )

    def test_payment_query_exposes_canonical_payment(self):
        payment = self.create_payment(
            payer=self.user,
        )

        global_id = Node.to_global_id(
            "PaymentNode",
            str(payment.pk),
        )

        result = self.client.execute(
            """
            query GetPaymentId($id: ID!) {
                payment(id: $id) {
                    id
                }
            }
            """,
            variables={
                "id": global_id,
            },
            context_value=make_context(self.user),
        )

        self.assertIsNone(
            result.get("errors"),
        )

        self.assertIsNotNone(
            result["data"]["payment"],
        )

        self.assertEqual(
            result["data"]["payment"]["id"],
            global_id,
        )

    def test_authenticated_user_can_query_own_payment(self):
        payment = self.create_payment(
            payer=self.user,
        )

        global_id = Node.to_global_id(
            "PaymentNode",
            str(payment.pk),
        )

        result = self.client.execute(
            """
            query GetPayment($id: ID!) {
                payment(id: $id) {
                    id
                    reference
                    direction
                    purpose
                    amount
                    currency
                    status
                }
            }
            """,
            variables={
                "id": global_id,
            },
            context_value=make_context(self.user),
        )

        self.assertNotIn(
            "errors",
            result,
        )

        data = result["data"]["payment"]

        self.assertEqual(
            data["id"],
            global_id,
        )

        self.assertEqual(
            data["reference"],
            payment.reference,
        )

        self.assertEqual(
            data["direction"],
            "RECEIVE",
        )

        self.assertEqual(
            data["purpose"],
            "CHECKOUT",
        )

        self.assertEqual(
            data["amount"],
            "100.00",
        )

        self.assertEqual(
            data["currency"],
            "NGN",
        )

        self.assertEqual(
            data["status"],
            "PENDING",
        )

    def test_authenticated_user_cannot_query_unrelated_payment(self):
        payment = self.create_payment(
            payer=self.other_user,
            reference="PAY-GRAPHQL-002",
            idempotency_key="idem-graphql-002",
        )

        global_id = Node.to_global_id(
            "PaymentNode",
            str(payment.pk),
        )

        result = self.client.execute(
            """
            query GetPayment($id: ID!) {
                payment(id: $id) {
                    id
                    reference
                }
            }
            """,
            variables={
                "id": global_id,
            },
            context_value=make_context(self.user),
        )

        self.assertNotIn(
            "errors",
            result,
        )

        self.assertIsNone(
            result["data"]["payment"],
        )


class CreatePaymentMutationTests(
    CanonicalPaymentGraphQLTestCase,
):

    @patch(
        "graphq.payment.canonical.mutations.PaymentService.create_payment"
    )
    def test_create_payment_delegates_to_payment_service(
        self,
        mock_create_payment,
    ):
        payment = Payment(
            reference="PAY-GRAPHQL-CREATE",
            direction=Payment.Direction.RECEIVE,
            purpose=Payment.Purpose.CHECKOUT,
            source_type="checkout",
            source_id="checkout-123",
            payer=self.user,
            amount=Decimal("250.00"),
            currency="NGN",
            status=Payment.Status.PENDING,
            idempotency_key="idem-create-001",
        )

        mock_create_payment.return_value = payment

        result = self.client.execute(
            """
            mutation CreatePayment(
                $input: CreatePaymentInput!
            ) {
                createPayment(input: $input) {
                    payment {
                        reference
                        direction
                        purpose
                        amount
                        currency
                        status
                    }
                }
            }
            """,
            variables={
                "input": {
                    "direction": "receive",
                    "purpose": "checkout",
                    "sourceType": "checkout",
                    "sourceId": "checkout-123",
                    "amount": "250.00",
                    "currency": "ngn",
                    "idempotencyKey": "idem-create-001",
                    "payerId": None,
                },
            },
            context_value=make_context(self.user),
        )

        self.assertNotIn(
            "errors",
            result,
        )

        mock_create_payment.assert_called_once()

        kwargs = mock_create_payment.call_args.kwargs

        self.assertEqual(
            kwargs["direction"],
            "receive",
        )

        self.assertEqual(
            kwargs["purpose"],
            "checkout",
        )

        self.assertEqual(
            kwargs["source_type"],
            "checkout",
        )

        self.assertEqual(
            kwargs["source_id"],
            "checkout-123",
        )

        self.assertEqual(
            kwargs["amount"],
            Decimal("250.00"),
        )

        self.assertEqual(
            kwargs["currency"],
            "ngn",
        )

        self.assertEqual(
            kwargs["idempotency_key"],
            "idem-create-001",
        )

    def test_create_payment_requires_authentication(self):
        result = self.client.execute(
            """
            mutation CreatePayment(
                $input: CreatePaymentInput!
            ) {
                createPayment(input: $input) {
                    payment {
                        reference
                    }
                }
            }
            """,
            variables={
                "input": {
                    "direction": "receive",
                    "purpose": "checkout",
                    "sourceType": "checkout",
                    "sourceId": "checkout-123",
                    "amount": "250.00",
                    "currency": "NGN",
                    "idempotencyKey": "idem-auth-001",
                },
            },
            context_value=make_context(
                SimpleNamespace(
                    is_authenticated=False,
                ),
            ),
        )

        self.assertIn(
            "errors",
            result,
        )