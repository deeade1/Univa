# invoice/tests/test_smoke.py

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from invoice.enums import InvoiceStatus
from invoice.models import (
    Invoice,
    InvoiceParty,
    InvoicePayment,
)
from invoice.services import (
    LineItemSpec,
    SourceSpec,
    apply_payment,
    generate_invoice,
)


User = get_user_model()


class InvoiceSmokeTest(TestCase):
    def test_generate_and_pay(self):
        user = User.objects.create_user(email="customer@example.com")
        issuer, _ = InvoiceParty.objects.get_or_create(
            name="Univa",
            is_organization=True,
        )
        recipient = InvoiceParty.objects.create(
            user=user,
            name="Customer",
            email=user.email,
        )

        invoice = generate_invoice(
            issuer=issuer,
            recipient=recipient,
            currency="NGN",
            line_items=[
                LineItemSpec(
                    description="Test item",
                    quantity=Decimal("2"),
                    unit_price=Decimal("1000.00"),
                ),
            ],
            sources=[
                SourceSpec(source_type="order", source_id="abc-123"),
            ],
        )

        self.assertEqual(invoice.subtotal_amount, Decimal("2000.00"))
        self.assertEqual(invoice.total_amount, Decimal("2000.00"))
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)

        payment, created = apply_payment(
            invoice_id=invoice.pk,
            idempotency_key="test-key-1",
            payment_type="payment_execution",
            amount=Decimal("2000.00"),
            currency="NGN",
        )
        self.assertTrue(created)

        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("2000.00"))
        self.assertEqual(invoice.balance_due, Decimal("0.00"))
        self.assertEqual(invoice.status, InvoiceStatus.PAID)

        # Idempotent replay.
        payment2, created2 = apply_payment(
            invoice_id=invoice.pk,
            idempotency_key="test-key-1",
            payment_type="payment_execution",
            amount=Decimal("2000.00"),
            currency="NGN",
        )
        self.assertFalse(created2)
        self.assertEqual(payment2.pk, payment.pk)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("2000.00"))

    def test_share_requires_recipient(self):
        from invoice.services import create_share

        user = User.objects.create_user(email="owner@example.com")
        other = User.objects.create_user(email="other@example.com")
        issuer, _ = InvoiceParty.objects.get_or_create(
            name="Univa", is_organization=True,
        )
        recipient = InvoiceParty.objects.create(
            user=user, name="Owner", email=user.email,
        )

        invoice = generate_invoice(
            issuer=issuer,
            recipient=recipient,
            currency="NGN",
            line_items=[
                LineItemSpec(
                    description="Item",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100.00"),
                ),
            ],
        )

        with self.assertRaises(Exception):
            create_share(
                invoice_id=invoice.pk,
                created_by=other,
            )

        share = create_share(
            invoice_id=invoice.pk,
            created_by=user,
        )
        self.assertTrue(share.is_active)