# apps/backend/ecommerce/tests/test_models/test_giftcard.py

"""
Tests for GiftCard mutation methods.

Focus:

    - use_balance decrements the balance, marks PARTIALLY_USED or
      USED as appropriate
    - use_balance rejects non-positive amounts, non-usable cards,
      and overdrafts
    - add_balance increments the balance and reactivates USED and
      PARTIALLY_USED cards
    - add_balance rejects EXPIRED and REFUNDED cards
    - extend_expiry reactivates an expired card when given a
      future date
    - extend-and-add is the correct two-step pattern for topping
      up an expired card
    - deactivate/activate transitions
    - create_gift_card generates unique codes
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction 
from django.test import TestCase
from django.utils import timezone

from ecommerce.models.giftcard import GiftCard
from ecommerce.models.constants import GiftCardStatus


class GiftCardFixture(TestCase):
    """Shared fixture for gift card mutation tests."""

    def make_card(
        self,
        *,
        code="TESTCARD00000001",
        initial=Decimal("500.00"),
        current=None,
        status=GiftCardStatus.ACTIVE,
        expiry_date=None,
        is_active=True,
    ):
        return GiftCard.objects.create(
            code=code,
            initial_balance_amount=initial,
            current_balance_amount=(
                current if current is not None else initial
            ),
            currency="NGN",
            status=status,
            expiry_date=expiry_date,
            is_active=is_active,
        )


# ----------------------------------------------------------------------
# use_balance
# ----------------------------------------------------------------------


class GiftCardUseBalanceTests(GiftCardFixture):

    def test_partial_use_marks_partially_used(self):
        card = self.make_card(initial=Decimal("500.00"))

        card.use_balance(Decimal("100.00"))

        card.refresh_from_db()
        self.assertEqual(card.current_balance_amount, Decimal("400.00"))
        self.assertEqual(card.status, GiftCardStatus.PARTIALLY_USED)

    def test_full_use_marks_used(self):
        card = self.make_card(initial=Decimal("500.00"))

        card.use_balance(Decimal("500.00"))

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.USED)
        self.assertEqual(card.current_balance_amount, Decimal("0"))

    def test_second_partial_use_keeps_partially_used(self):
        card = self.make_card(initial=Decimal("500.00"))
        card.use_balance(Decimal("100.00"))

        card.use_balance(Decimal("50.00"))

        card.refresh_from_db()
        self.assertEqual(card.current_balance_amount, Decimal("350.00"))
        self.assertEqual(card.status, GiftCardStatus.PARTIALLY_USED)

    def test_second_use_can_reach_used(self):
        card = self.make_card(initial=Decimal("500.00"))
        card.use_balance(Decimal("300.00"))

        card.use_balance(Decimal("200.00"))

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.USED)

    def test_records_last_used_on(self):
        card = self.make_card()
        before = timezone.now()

        card.use_balance(Decimal("10.00"))

        card.refresh_from_db()
        self.assertIsNotNone(card.last_used_on)
        self.assertGreaterEqual(card.last_used_on, before)

    def test_rejects_zero_amount(self):
        card = self.make_card()

        with self.assertRaises(ValidationError):
            card.use_balance(Decimal("0"))

    def test_rejects_negative_amount(self):
        card = self.make_card()

        with self.assertRaises(ValidationError):
            card.use_balance(Decimal("-10"))

    def test_rejects_overdraft(self):
        card = self.make_card(initial=Decimal("500.00"))

        with self.assertRaises(ValidationError):
            card.use_balance(Decimal("600.00"))

        card.refresh_from_db()
        self.assertEqual(card.current_balance_amount, Decimal("500.00"))
        self.assertEqual(card.status, GiftCardStatus.ACTIVE)

    def test_rejects_expired_card(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        card = self.make_card(
            status=GiftCardStatus.EXPIRED,
            expiry_date=yesterday,
        )

        with self.assertRaises(ValidationError):
            card.use_balance(Decimal("10.00"))

    def test_rejects_inactive_card(self):
        card = self.make_card(
            status=GiftCardStatus.INACTIVE,
            is_active=False,
        )

        with self.assertRaises(ValidationError):
            card.use_balance(Decimal("10.00"))

    def test_rejects_refunded_card(self):
        card = self.make_card(status=GiftCardStatus.REFUNDED)

        with self.assertRaises(ValidationError):
            card.use_balance(Decimal("10.00"))


# ----------------------------------------------------------------------
# add_balance
# ----------------------------------------------------------------------

class GiftCardAddBalanceTests(GiftCardFixture):

    def test_increments_balance(self):
        card = self.make_card(initial=Decimal("500.00"))

        card.add_balance(Decimal("100.00"))

        card.refresh_from_db()
        self.assertEqual(card.current_balance_amount, Decimal("600.00"))
        self.assertEqual(card.status, GiftCardStatus.ACTIVE)

    def test_reactivates_used_card(self):
        card = self.make_card(
            initial=Decimal("500.00"),
            current=Decimal("0"),
            status=GiftCardStatus.USED,
        )

        card.add_balance(Decimal("100.00"))

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.ACTIVE)
        self.assertEqual(card.current_balance_amount, Decimal("100.00"))

    def test_reactivates_partially_used_card(self):
        card = self.make_card(
            initial=Decimal("500.00"),
            current=Decimal("200.00"),
            status=GiftCardStatus.PARTIALLY_USED,
        )

        card.add_balance(Decimal("50.00"))

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.ACTIVE)
        self.assertEqual(card.current_balance_amount, Decimal("250.00"))

    def test_rejects_zero_amount(self):
        card = self.make_card()

        with self.assertRaises(ValidationError):
            card.add_balance(Decimal("0"))

    def test_rejects_negative_amount(self):
        card = self.make_card()

        with self.assertRaises(ValidationError):
            card.add_balance(Decimal("-10"))

    def test_rejects_expired_card(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        card = self.make_card(
            status=GiftCardStatus.EXPIRED,
            expiry_date=yesterday,
        )

        with self.assertRaises(ValidationError):
            card.add_balance(Decimal("100.00"))

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.EXPIRED)
        self.assertEqual(card.current_balance_amount, Decimal("500.00"))

    def test_rejects_refunded_card(self):
        card = self.make_card(status=GiftCardStatus.REFUNDED)

        with self.assertRaises(ValidationError):
            card.add_balance(Decimal("100.00"))

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.REFUNDED)

    def test_does_not_reactivate_inactive_card(self):
        card = self.make_card(
            status=GiftCardStatus.INACTIVE,
            is_active=False,
        )

        card.add_balance(Decimal("100.00"))

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.INACTIVE)
        self.assertEqual(card.current_balance_amount, Decimal("600.00"))

    def test_cannot_have_more_balance_than_total_loaded(self):
        """
        The giftcard_balance_consistency constraint enforces
        initial_balance_amount >= current_balance_amount. This is
        the guard against a bug that inflates `current` without
        a matching load.

        The `.update()` call bypasses `save()` and goes straight
        to SQL, so it's the fastest way to exercise the constraint
        without any model-level interference.
        """
        card = self.make_card(initial=Decimal("500.00"))

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GiftCard.objects.filter(pk=card.pk).update(
                    current_balance_amount=Decimal("1000.00")
                )

# ----------------------------------------------------------------------
# extend_expiry
# ----------------------------------------------------------------------


class GiftCardExtendExpiryTests(GiftCardFixture):

    def test_extends_active_card(self):
        card = self.make_card(
            expiry_date=timezone.now().date() + timedelta(days=30),
        )
        new_date = timezone.now().date() + timedelta(days=365)

        card.extend_expiry(new_date=new_date)

        card.refresh_from_db()
        self.assertEqual(card.expiry_date, new_date)
        self.assertEqual(card.status, GiftCardStatus.ACTIVE)

    def test_reactivates_expired_card_with_future_date(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        card = self.make_card(
            status=GiftCardStatus.EXPIRED,
            expiry_date=yesterday,
        )
        new_date = timezone.now().date() + timedelta(days=365)

        card.extend_expiry(new_date=new_date)

        card.refresh_from_db()
        self.assertEqual(card.expiry_date, new_date)
        self.assertEqual(card.status, GiftCardStatus.ACTIVE)

    def test_does_not_reactivate_with_past_date(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        card = self.make_card(
            status=GiftCardStatus.EXPIRED,
            expiry_date=yesterday,
        )
        even_older = yesterday - timedelta(days=30)

        card.extend_expiry(new_date=even_older)

        card.refresh_from_db()
        self.assertEqual(card.expiry_date, even_older)
        self.assertEqual(card.status, GiftCardStatus.EXPIRED)

    def test_rejects_none_date(self):
        card = self.make_card()

        with self.assertRaises(ValidationError):
            card.extend_expiry(new_date=None)


# ----------------------------------------------------------------------
# extend + add — the intended two-step pattern
# ----------------------------------------------------------------------


class GiftCardExtendAndAddTests(GiftCardFixture):

    def test_extend_then_add_topup_pattern(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        card = self.make_card(
            initial=Decimal("500.00"),
            current=Decimal("100.00"),
            status=GiftCardStatus.EXPIRED,
            expiry_date=yesterday,
        )

        card.extend_expiry(
            new_date=timezone.now().date() + timedelta(days=365)
        )

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.ACTIVE)

        card.add_balance(Decimal("400.00"))

        card.refresh_from_db()
        self.assertEqual(card.current_balance_amount, Decimal("500.00"))
        self.assertEqual(card.status, GiftCardStatus.ACTIVE)


# ----------------------------------------------------------------------
# activate / deactivate
# ----------------------------------------------------------------------


class GiftCardActivateTests(GiftCardFixture):

    def test_deactivate_active_card(self):
        card = self.make_card()

        card.deactivate()

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.INACTIVE)
        self.assertFalse(card.is_active)

    def test_deactivate_partially_used_card(self):
        card = self.make_card(
            status=GiftCardStatus.PARTIALLY_USED,
            current=Decimal("200.00"),
        )

        card.deactivate()

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.INACTIVE)

    def test_deactivate_is_noop_for_used(self):
        card = self.make_card(
            status=GiftCardStatus.USED,
            current=Decimal("0"),
        )

        card.deactivate()

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.USED)

    def test_activate_inactive_card(self):
        card = self.make_card(
            status=GiftCardStatus.INACTIVE,
            is_active=False,
        )

        card.activate()

        card.refresh_from_db()
        self.assertEqual(card.status, GiftCardStatus.ACTIVE)
        self.assertTrue(card.is_active)
        self.assertIsNotNone(card.activated_at)

    def test_activate_rejects_already_active(self):
        card = self.make_card()

        with self.assertRaises(ValidationError):
            card.activate()


# ----------------------------------------------------------------------
# manager
# ----------------------------------------------------------------------


class GiftCardManagerTests(GiftCardFixture):

    def test_create_gift_card_generates_unique_code(self):
        card_a = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("100.00"),
            currency="NGN",
        )
        card_b = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("100.00"),
            currency="NGN",
        )

        self.assertNotEqual(card_a.code, card_b.code)
        self.assertEqual(len(card_a.code), 16)

    def test_create_gift_card_accepts_explicit_code(self):
        card = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("100.00"),
            currency="NGN",
            code="EXPLICITCODE0001",
        )

        self.assertEqual(card.code, "EXPLICITCODE0001")

    def test_create_gift_card_sets_initial_and_current(self):
        card = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("100.00"),
            currency="NGN",
        )

        self.assertEqual(card.initial_balance_amount, Decimal("100.00"))
        self.assertEqual(card.current_balance_amount, Decimal("100.00"))