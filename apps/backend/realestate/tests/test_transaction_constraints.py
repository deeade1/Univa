# apps/backend/realestate/tests/test_transaction_constraints.py

"""
Tests for real estate transaction constraints and locking.

Focus:
    - the corrected CheckConstraints reject CLOSED with NULL
      agreed_price or NULL close_date
    - unique_active_transaction_per_property prevents two active
      transactions on the same property
    - TransactionService.close_transaction is idempotent
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from django.core.exceptions import ValidationError
from realestate.constants import TransactionStatus
from realestate.models import (
    Client,
    Listing,
    ListingType,
    Transaction,
)
from realestate.services.transaction_service import TransactionService


User = get_user_model()


def _make_test_image_file(name="test.jpg"):
    """Return a real 1x1 JPEG as an uploaded file."""
    buf = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(
        name,
        buf.read(),
        content_type="image/jpeg",
    )


class TransactionConstraintFixture(TestCase):
    """Shared fixture for transaction constraint tests."""

    def setUp(self):
        uid = uuid.uuid4().hex[:8]

        self.seller = User.objects.create_user(
            email=f"seller-{uid}@example.com",
        )
        self.buyer_user = User.objects.create_user(
            email=f"buyer-{uid}@example.com",
        )
        self.client = Client.objects.create(
            user=self.buyer_user,
        )

        # Fixture uses a ListingType that requires neither land
        # nor building details, so Listing.clean() does not demand
        # square_feet or land_size. This keeps the fixture focused
        # on transaction constraints.
        self.listing_type = ListingType.objects.create(
            property_type="house",
            requires_land_details=False,
            requires_building_details=False,
        )

        self.property = Listing.objects.create(
            title="Test Property",
            slug=f"property-{uid}",
            listing_type=self.listing_type,
            property_area="R",
            property_for="S",
            price=Decimal("1000000.00"),
            currency="NGN",
            image=_make_test_image_file(),
        )

    def _make_transaction(self, **kwargs):
        defaults = {
            "property": self.property,
            "buyer": self.client,
            "seller": self.seller,
            "offer_price": Decimal("1000000.00"),
            "target_close_date": (
                timezone.now().date() + timedelta(days=30)
            ),
        }
        defaults.update(kwargs)
        return Transaction.objects.create(**defaults)


class TransactionClosedConstraintTests(TransactionConstraintFixture):

    def test_closed_without_agreed_price_is_rejected(self):
        """
        Regression: the inverted constraint permitted CLOSED with
        agreed_price=NULL.
        """
        txn = self._make_transaction(
            status=TransactionStatus.CLOSING,
            agreed_price=Decimal("1000000.00"),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Transaction.objects.filter(pk=txn.pk).update(
                    status=TransactionStatus.CLOSED,
                    agreed_price=None,
                    actual_close_date=timezone.now().date(),
                )

    def test_closed_without_close_date_is_rejected(self):
        txn = self._make_transaction(
            status=TransactionStatus.CLOSING,
            agreed_price=Decimal("1000000.00"),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Transaction.objects.filter(pk=txn.pk).update(
                    status=TransactionStatus.CLOSED,
                    agreed_price=Decimal("1000000.00"),
                    actual_close_date=None,
                )


class UniqueActiveTransactionTests(TransactionConstraintFixture):

    def test_second_active_transaction_is_rejected(self):
        """
        Regression: at most one active transaction per property.

        With `full_clean()` no longer called from save(), the
        DB constraint raises IntegrityError. The inner
        `transaction.atomic()` creates a savepoint so the
        aborted transaction is rolled back cleanly.
        """
        self._make_transaction(
            status=TransactionStatus.UNDER_CONTRACT,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make_transaction(
                    status=TransactionStatus.OFFER_PENDING,
                )

    def test_two_closed_transactions_are_allowed(self):
        self._make_transaction(
            status=TransactionStatus.CLOSED,
            agreed_price=Decimal("1000000.00"),
            actual_close_date=timezone.now().date(),
        )
        self._make_transaction(
            status=TransactionStatus.CLOSED,
            agreed_price=Decimal("950000.00"),
            actual_close_date=timezone.now().date(),
        )

        self.assertEqual(
            Transaction.objects.filter(
                property=self.property,
            ).count(),
            2,
        )


class CloseTransactionIdempotencyTests(TransactionConstraintFixture):

    def test_closing_twice_is_idempotent(self):
        txn = self._make_transaction(
            status=TransactionStatus.CLOSING,
            agreed_price=Decimal("1000000.00"),
        )
        txn.milestones.update(
            is_completed=True,
            completed_date=timezone.now().date(),
        )

        closed = TransactionService.close_transaction(
            txn.id,
            agreed_price=Decimal("1000000.00"),
        )
        closed_again = TransactionService.close_transaction(
            txn.id,
            agreed_price=Decimal("1000000.00"),
        )

        self.assertEqual(closed.pk, closed_again.pk)
        self.assertEqual(closed.status, TransactionStatus.CLOSED)