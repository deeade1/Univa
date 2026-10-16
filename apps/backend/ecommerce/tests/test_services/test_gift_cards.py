# ecommerce/tests/test_services/test_gift_cards.py

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.checkout import CheckoutGiftCard
from ecommerce.models.giftcard import GiftCard
from ecommerce.models.product import (
    Product,
    ProductChannelListing,
    ProductType,
    ProductVariant,
    ProductVariantChannelListing,
)
from ecommerce.models.warehouse import Warehouse
from ecommerce.services.checkout import (
    add_variant_to_checkout,
    apply_gift_card,
    create_checkout,
    remove_gift_card,
)


User = get_user_model()


class GiftCardTestFixture(TestCase):
    """Shared fixture for gift card application tests."""

    def setUp(self):
        from accounts.models import Address

        uid = uuid.uuid4().hex[:8]

        self.user = User.objects.create_user(
            email=f"giftcard-{uid}@example.com",
        )
        self.channel = Channel.objects.create(
            name="Test Channel",
            slug=f"giftcard-{uid}",
            currency_code="NGN",
            default_country="NG",
        )
        address = Address.objects.create(
            user=self.user,
            first_name="Test",
            last_name="User",
            street_address_1="123 Test St",
            city="Lagos",
            postal_code="100001",
            country="NG",
        )
        warehouse = Warehouse.objects.create(
            name="Main",
            slug=f"wh-{uid}",
            address=address,
        )
        warehouse.channels.add(self.channel)

        product_type = ProductType.objects.create(
            name=f"Physical {uid}",
            slug=f"physical-{uid}",
            kind="normal",
            has_variants=True,
            is_shipping_required=True,
        )
        product = Product.objects.create(
            name="Test Product",
            slug=f"test-{uid}",
            product_type=product_type,
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            sku=f"SKU-{uid}",
            name="Default",
            track_inventory=False,
        )
        ProductVariantChannelListing.objects.create(
            variant=self.variant,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("1000.00"),
        )
        ProductChannelListing.objects.create(
            product=product,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("1000.00"),
            visible_in_listings=True,
        )


class ApplyGiftCardTests(GiftCardTestFixture):

    def test_apply_card_capped_at_total(self):
        card = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("5000.00"),
            currency="NGN",
        )
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("1"))

        checkout = apply_gift_card(checkout, card.code)

        application = CheckoutGiftCard.objects.get(checkout=checkout)
        # Total is 1000, card is 5000, so application caps at 1000.
        self.assertEqual(application.amount_applied, Decimal("1000.00"))
        checkout.refresh_from_db()
        self.assertEqual(checkout.total_gross_amount, Decimal("0.00"))

    def test_apply_card_partial(self):
        card = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("300.00"),
            currency="NGN",
        )
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("1"))

        apply_gift_card(checkout, card.code)

        application = CheckoutGiftCard.objects.get(checkout=checkout)
        self.assertEqual(application.amount_applied, Decimal("300.00"))
        checkout.refresh_from_db()
        self.assertEqual(checkout.total_gross_amount, Decimal("700.00"))

    def test_multiple_cards_stack(self):
        card_a = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("300.00"),
            currency="NGN",
        )
        card_b = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("200.00"),
            currency="NGN",
        )
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("1"))

        apply_gift_card(checkout, card_a.code)
        apply_gift_card(checkout, card_b.code)

        self.assertEqual(
            CheckoutGiftCard.objects.filter(checkout=checkout).count(),
            2,
        )
        checkout.refresh_from_db()
        self.assertEqual(checkout.total_gross_amount, Decimal("500.00"))

    def test_remove_gift_card(self):
        card = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("300.00"),
            currency="NGN",
        )
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("1"))
        apply_gift_card(checkout, card.code)

        remove_gift_card(checkout, card)

        self.assertFalse(
            CheckoutGiftCard.objects.filter(checkout=checkout).exists()
        )
        checkout.refresh_from_db()
        self.assertEqual(checkout.total_gross_amount, Decimal("1000.00"))

    def test_unknown_code_raises(self):
        from ecommerce.services.checkout import GiftCardNotFound

        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("1"))

        with self.assertRaises(GiftCardNotFound):
            apply_gift_card(checkout, "DOESNOTEXIST")

    def test_expired_card_rejected(self):
        from datetime import timedelta

        from django.utils import timezone
        from ecommerce.models.enums import GiftCardStatus
        from ecommerce.services.checkout import GiftCardNotUsable

        card = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("500.00"),
            currency="NGN",
        )
        # Force the card into EXPIRED state.
        card.expiry_date = timezone.now().date() - timedelta(days=1)
        card.status = GiftCardStatus.EXPIRED
        card.save(update_fields=["expiry_date", "status"])

        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("1"))

        with self.assertRaises(GiftCardNotUsable):
            apply_gift_card(checkout, card.code)

    def test_reapplying_same_card_updates_amount(self):
        card = GiftCard.objects.create_gift_card(
            initial_balance=Decimal("500.00"),
            currency="NGN",
        )
        checkout = create_checkout(self.channel, user=self.user)
        add_variant_to_checkout(checkout, self.variant, Decimal("1"))

        apply_gift_card(checkout, card.code)
        apply_gift_card(checkout, card.code)

        # Still exactly one application row.
        self.assertEqual(
            CheckoutGiftCard.objects.filter(checkout=checkout).count(),
            1,
        )