# apps/backend/ecommerce/tests/test_models/test_product.py

"""
Tests for Product model invariants.

Focus:

    - Product.clean() rejects a default_variant belonging to a
      different product
    - ProductChannelListing and ProductVariantChannelListing enforce
      discounted_price <= price
    - ProductReview.helpful_count is incremented atomically
    - DigitalContentUrl.token is generated even on bulk_create
    - ProductVariant.preorder_global_threshold is non-negative
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from ecommerce.models.channel import Channel
from ecommerce.models.product import (
    DigitalContent,
    DigitalContentUrl,
    Product,
    ProductChannelListing,
    ProductReview,
    ProductType,
    ProductVariant,
    ProductVariantChannelListing,
)


class ProductTestFixture(TestCase):
    """
    Shared fixture. Not a test class itself.
    """

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.user = User.objects.create_user(
            email="product-fixture@example.com",
            password="test-password",
        )

        cls.channel = Channel.objects.create(
            name="Test Channel",
            slug="test-channel",
            currency_code="NGN",
            default_country="NG",
            is_active=True,
        )

        cls.product_type = ProductType.objects.create(
            name="Test Type",
            slug="test-type",
            has_variants=True,
            is_shipping_required=True,
            is_digital=False,
        )

    def make_product(self, *, slug, name=None, **kwargs):
        return Product.objects.create(
            product_type=self.product_type,
            name=name or slug.title(),
            slug=slug,
            **kwargs,
        )

    def make_variant(self, *, product, name="Default", sku=None, **kwargs):
        return ProductVariant.objects.create(
            product=product,
            name=name,
            sku=sku,
            **kwargs,
        )


# ----------------------------------------------------------------------
# Product.clean() — default_variant ownership
# ----------------------------------------------------------------------


class ProductDefaultVariantTests(ProductTestFixture):

    def test_clean_accepts_variant_of_same_product(self):
        product = self.make_product(slug="matching")
        variant = self.make_variant(product=product)

        product.default_variant = variant
        # Should not raise.
        product.clean()

    def test_clean_rejects_variant_of_different_product(self):
        product_a = self.make_product(slug="product-a")
        product_b = self.make_product(slug="product-b")
        variant_of_b = self.make_variant(product=product_b)

        product_a.default_variant = variant_of_b

        with self.assertRaises(ValidationError) as ctx:
            product_a.clean()

        self.assertIn("default_variant", ctx.exception.message_dict)

    def test_clean_is_noop_when_default_variant_is_unset(self):
        product = self.make_product(slug="no-default")

        # Should not raise.
        product.clean()

    def test_clean_is_noop_for_unsaved_product(self):
        """
        A brand-new Product has no pk yet, so the ownership check
        cannot run. That's fine — the check will run on the next
        full_clean() after the product is saved.
        """
        variant_of_b = self.make_variant(
            product=self.make_product(slug="some-product"),
        )

        unsaved = Product(
            product_type=self.product_type,
            name="Unsaved",
            slug="unsaved",
            default_variant=variant_of_b,
        )

        # Should not raise (pk is None).
        unsaved.clean()


# ----------------------------------------------------------------------
# ProductChannelListing — discounted_price <= price
# ----------------------------------------------------------------------


class ProductChannelListingDiscountConstraintTests(ProductTestFixture):

    def test_discounted_price_equal_to_price_is_allowed(self):
        product = self.make_product(slug="equal-price")

        listing = ProductChannelListing.objects.create(
            product=product,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("100.00"),
            discounted_price_amount=Decimal("100.00"),
        )

        self.assertEqual(
            listing.discounted_price_amount,
            Decimal("100.00"),
        )

    def test_discounted_price_below_price_is_allowed(self):
        product = self.make_product(slug="below-price")

        listing = ProductChannelListing.objects.create(
            product=product,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("100.00"),
            discounted_price_amount=Decimal("80.00"),
        )

        self.assertEqual(
            listing.discounted_price_amount,
            Decimal("80.00"),
        )

    def test_discounted_price_null_is_allowed(self):
        product = self.make_product(slug="null-discount")

        listing = ProductChannelListing.objects.create(
            product=product,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("100.00"),
            discounted_price_amount=None,
        )

        self.assertIsNone(listing.discounted_price_amount)

    def test_discounted_price_above_price_is_rejected(self):
        product = self.make_product(slug="above-price")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductChannelListing.objects.create(
                    product=product,
                    channel=self.channel,
                    currency="NGN",
                    price_amount=Decimal("100.00"),
                    discounted_price_amount=Decimal("120.00"),
                )


# ----------------------------------------------------------------------
# ProductVariantChannelListing — same constraint on variants
# ----------------------------------------------------------------------


class ProductVariantChannelListingDiscountConstraintTests(
    ProductTestFixture
):

    def test_discounted_price_below_price_is_allowed(self):
        product = self.make_product(slug="variant-below")
        variant = self.make_variant(product=product)

        listing = ProductVariantChannelListing.objects.create(
            variant=variant,
            channel=self.channel,
            currency="NGN",
            price_amount=Decimal("100.00"),
            discounted_price_amount=Decimal("75.00"),
        )

        self.assertEqual(
            listing.discounted_price_amount,
            Decimal("75.00"),
        )

    def test_discounted_price_above_price_is_rejected(self):
        product = self.make_product(slug="variant-above")
        variant = self.make_variant(product=product)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariantChannelListing.objects.create(
                    variant=variant,
                    channel=self.channel,
                    currency="NGN",
                    price_amount=Decimal("100.00"),
                    discounted_price_amount=Decimal("120.00"),
                )


# ----------------------------------------------------------------------
# ProductReview.helpful_count atomicity
# ----------------------------------------------------------------------


class ProductReviewHelpfulCountTests(ProductTestFixture):

    def test_mark_helpful_increments_count(self):
        product = self.make_product(slug="review-count")
        review = ProductReview.objects.create(
            product=product,
            user=self.user,
            rating=5,
        )

        review.mark_helpful()

        review.refresh_from_db()
        self.assertEqual(review.helpful_count, 1)

    def test_mark_helpful_returns_updated_instance(self):
        product = self.make_product(slug="review-returns")
        review = ProductReview.objects.create(
            product=product,
            user=self.user,
            rating=4,
        )

        review.mark_helpful()

        # The instance's local attribute is refreshed.
        self.assertEqual(review.helpful_count, 1)

    def test_record_helpful_vote_by_id(self):
        product = self.make_product(slug="review-by-id")
        review = ProductReview.objects.create(
            product=product,
            user=self.user,
            rating=3,
        )

        new_count = ProductReview.record_helpful_vote(review.pk)

        self.assertEqual(new_count, 1)

    def test_record_helpful_vote_raises_for_missing_review(self):
        import uuid

        with self.assertRaises(ProductReview.DoesNotExist):
            ProductReview.record_helpful_vote(uuid.uuid4())

    def test_multiple_increments_accumulate(self):
        product = self.make_product(slug="review-multi")
        review = ProductReview.objects.create(
            product=product,
            user=self.user,
            rating=5,
        )

        for _ in range(5):
            review.mark_helpful()

        review.refresh_from_db()
        self.assertEqual(review.helpful_count, 5)


# ----------------------------------------------------------------------
# DigitalContentUrl.token
# ----------------------------------------------------------------------


class DigitalContentUrlTokenTests(ProductTestFixture):

    def test_token_is_generated_on_create(self):
        product = self.make_product(slug="digital-token")
        variant = self.make_variant(product=product)
        content = DigitalContent.objects.create(product_variant=variant)

        url = DigitalContentUrl.objects.create(content=content)

        self.assertIsNotNone(url.token)
        self.assertEqual(len(url.token), 32)

    def test_token_is_generated_on_bulk_create(self):
        """
        Regression test: the previous implementation set the token
        in save(). bulk_create() bypasses save(), so the token
        would have been empty. With default=... on the field, Django
        evaluates it per instance regardless of insertion path.
        """
        product = self.make_product(slug="digital-bulk")
        variant = self.make_variant(product=product)
        content = DigitalContent.objects.create(product_variant=variant)

        DigitalContentUrl.objects.bulk_create([
            DigitalContentUrl(content=content),
            DigitalContentUrl(content=content),
        ])

        tokens = list(
            DigitalContentUrl.objects
            .filter(content=content)
            .values_list("token", flat=True)
        )

        self.assertEqual(len(tokens), 2)
        self.assertTrue(all(token for token in tokens))
        self.assertTrue(all(len(token) == 32 for token in tokens))
        self.assertEqual(len(set(tokens)), 2)  # distinct

    def test_tokens_are_unique(self):
        product = self.make_product(slug="digital-unique")
        variant = self.make_variant(product=product)
        content = DigitalContent.objects.create(product_variant=variant)

        url_a = DigitalContentUrl.objects.create(content=content)
        url_b = DigitalContentUrl.objects.create(content=content)

        self.assertNotEqual(url_a.token, url_b.token)


# ----------------------------------------------------------------------
# ProductVariant.preorder_global_threshold
# ----------------------------------------------------------------------


class ProductVariantPreorderThresholdTests(ProductTestFixture):

    def test_positive_threshold_is_accepted(self):
        product = self.make_product(slug="preorder-positive")
        variant = self.make_variant(
            product=product,
            preorder_global_threshold=100,
        )

        self.assertEqual(variant.preorder_global_threshold, 100)

    def test_null_threshold_is_accepted(self):
        product = self.make_product(slug="preorder-null")
        variant = self.make_variant(product=product)

        self.assertIsNone(variant.preorder_global_threshold)

    def test_negative_threshold_is_rejected_by_database(self):
        """
        Regression test: the field is now PositiveIntegerField, so
        Postgres rejects negative values at the DB level.
        """
        product = self.make_product(slug="preorder-negative")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.create(
                    product=product,
                    name="Negative",
                    preorder_global_threshold=-1,
                )