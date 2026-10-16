# ecommerce/manager/managers.py

"""
Ecommerce querysets and managers.

This module contains database-level querying behavior for the ecommerce
domain.

Design principles:
    - Querysets contain reusable database filtering/annotation logic.
    - Managers expose those querysets to the models.
    - Business workflows belong in ecommerce.services.
    - No model imports are performed at module import time when circular
      dependencies are possible.
    - Django's timezone utilities are used instead of pytz.
"""

from __future__ import annotations

from typing import Optional

from django.contrib.postgres.aggregates import StringAgg
from django.db import models
from django.db.models import (
    Case,
    Count,
    Exists,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from django.contrib.auth import get_user_model


from ecommerce.models.channel import Channel

User = get_user_model()


# ============================================================================
# PRODUCT
# ============================================================================


class ProductQuerySet(models.QuerySet):
    """
    Queryset for Product.

    Contains visibility, publication, search/sorting and webhook-related
    database operations.
    """

    def published(self, channel: Channel):
        """
        Return products published on an active channel.

        A product is considered published when its channel listing:
            - belongs to the requested channel,
            - is published,
            - and its publication date has arrived or is unset.
        """

        if not channel or not channel.is_active:
            return self.none()

        from ecommerce.models.product import ProductChannelListing

        now = timezone.now()

        published_listings = (
            ProductChannelListing.objects.using(self.db)
            .filter(
                channel_id=channel.pk,
                is_published=True,
            )
            .filter(
                Q(published_at__lte=now)
                | Q(published_at__isnull=True)
            )
            .values("product_id")
        )

        return self.filter(
            Exists(
                published_listings.filter(
                    product_id=OuterRef("pk")
                )
            )
        )

    def not_published(self, channel: Channel):
        """
        Return products that are not currently published on a channel.
        """

        if not channel:
            return self.none()

        now = timezone.now()

        return (
            self.annotate_publication_info(channel)
            .filter(
                Q(published_at__gt=now)
                | Q(is_published=False)
                | Q(is_published__isnull=True)
            )
        )

    def published_with_variants(self, channel: Channel):
        """
        Return published products that have at least one purchasable
        variant listing for the requested channel.
        """

        if not channel or not channel.is_active:
            return self.none()

        from ecommerce.models.product import (
            ProductVariant,
            ProductVariantChannelListing,
        )

        variant_listings = (
            ProductVariantChannelListing.objects.using(self.db)
            .filter(
                channel_id=channel.pk,
                price_amount__isnull=False,
            )
            .values("variant_id")
        )

        variants = ProductVariant.objects.using(self.db).filter(
            Exists(
                variant_listings.filter(
                    variant_id=OuterRef("pk")
                )
            )
        )

        return self.published(channel).filter(
            Exists(
                variants.filter(
                    product_id=OuterRef("pk")
                )
            )
        )

    def visible_to_user(
        self,
        requestor: Optional[User],
        channel: Optional[Channel],
        limited_channel_access: bool = False,
    ):
        """
        Return products visible to the requesting user.

        Staff users with product-management permission can access products
        according to their channel restrictions.

        Storefront users only receive active, published products with
        available variants.
        """

        if requestor and requestor.has_perm(
            "ecommerce.manage_products"
        ):
            if limited_channel_access:
                if not channel:
                    return self.none()

                from ecommerce.models.product import ProductChannelListing

                channel_products = (
                    ProductChannelListing.objects.using(self.db)
                    .filter(channel_id=channel.pk)
                    .values("product_id")
                )

                return self.filter(
                    Exists(
                        channel_products.filter(
                            product_id=OuterRef("pk")
                        )
                    )
                )

            return self.all()

        if not channel or not channel.is_active:
            return self.none()

        return self.published_with_variants(channel)

    def annotate_publication_info(self, channel: Channel):
        """
        Annotate products with publication state and publication date
        for the supplied channel.
        """

        return (
            self.annotate_is_published(channel)
            .annotate_published_at(channel)
        )

    def annotate_is_published(self, channel: Channel):
        """
        Annotate each product with channel-specific publication state.
        """

        from ecommerce.models.product import ProductChannelListing

        query = (
            ProductChannelListing.objects.using(self.db)
            .filter(
                product_id=OuterRef("pk"),
                channel_id=channel.pk,
            )
            .values("is_published")[:1]
        )

        return self.annotate(
            is_published=Subquery(
                query,
                output_field=models.BooleanField(),
            )
        )

    def annotate_published_at(self, channel: Channel):
        """
        Annotate each product with its channel publication date.
        """

        from ecommerce.models.product import ProductChannelListing

        query = (
            ProductChannelListing.objects.using(self.db)
            .filter(
                product_id=OuterRef("pk"),
                channel_id=channel.pk,
            )
            .values("published_at")[:1]
        )

        return self.annotate(
            published_at=Subquery(
                query,
                output_field=models.DateTimeField(),
            )
        )

    def annotate_visible_in_listings(
        self,
        channel: Optional[Channel],
    ):
        """
        Annotate products with their channel listing visibility.
        """

        if not channel:
            return self.annotate(
                visible_in_listings=Value(
                    False,
                    output_field=models.BooleanField(),
                )
            )

        from ecommerce.models.product import ProductChannelListing

        query = (
            ProductChannelListing.objects.using(self.db)
            .filter(
                product_id=OuterRef("pk"),
                channel_id=channel.pk,
            )
            .values("visible_in_listings")[:1]
        )

        return self.annotate(
            visible_in_listings=Subquery(
                query,
                output_field=models.BooleanField(),
            )
        )

    def sort_by_attribute(
        self,
        attribute_pk: int,
        descending: bool = False,
    ):
        """
        Sort products by an attribute.

        Ordering rules:
            1. Products missing the attribute come last.
            2. Products with the attribute but no values come next.
            3. Products with values come first, concatenated in
               attribute-value sort order.

        Uses the new AssignedAttribute model, which stores both
        preset values (attribute_value) and raw values (raw_value).
        Sorting operates on `attribute_value__name` and falls back
        to `raw_value` when no preset is set.
        """

        from ecommerce.models.attribute import (
            AssignedAttribute,
            AttributeScopeLink,
        )

        try:
            attribute_pk = int(attribute_pk)
        except (TypeError, ValueError):
            return self.annotate(
                concatenated_values_order=Value(
                    None,
                    output_field=models.IntegerField(),
                ),
                concatenated_values=Value(
                    None,
                    output_field=models.CharField(),
                ),
            )

        # Attribute is linked to this product's type via a scope link.
        attribute_applies = AttributeScopeLink.objects.using(self.db).filter(
            product_type_id=OuterRef("product_type_id"),
            attribute_id=attribute_pk,
        )

        # This product has at least one assignment of the attribute.
        has_assignment = AssignedAttribute.objects.using(self.db).filter(
            product_id=OuterRef("pk"),
            attribute_id=attribute_pk,
        )

        return (
            self.annotate(
                grouped_ids=Count("id"),
                concatenated_values=Case(
                    # Attribute doesn't apply to this product type → ""
                    When(
                        ~Exists(attribute_applies),
                        then=Value(""),
                    ),
                    # Attribute applies but no values assigned → ""
                    When(
                        ~Exists(has_assignment),
                        then=Value(""),
                    ),
                    # Attribute applies and has values → concatenate
                    default=StringAgg(
                        F("assigned_attributes__attribute_value__name"),
                        filter=Q(
                            assigned_attributes__attribute_id=attribute_pk,
                            assigned_attributes__attribute_value__isnull=False,
                        ),
                        delimiter=",",
                        ordering=[
                            "assigned_attributes__attribute_value__sort_order",
                            "assigned_attributes__attribute_value__name",
                        ],
                    ),
                    output_field=models.CharField(),
                ),
            )
            .annotate(
                concatenated_values_order=Case(
                    When(
                        concatenated_values__isnull=True,
                        then=Value(2),
                    ),
                    When(
                        concatenated_values="",
                        then=Value(1),
                    ),
                    default=Value(0),
                    output_field=models.IntegerField(),
                )
            )
            .order_by(
                f"{'-' if descending else ''}concatenated_values_order",
                f"{'-' if descending else ''}concatenated_values",
                f"{'-' if descending else ''}name",
            )
        )

    def prefetched_for_webhook(
        self,
        single_object: bool = True,
    ):
        """
        Prefetch the relationships required by ecommerce webhook payloads.
        """

        common_fields = (
            "media",
            "variants__assigned_attributes__attribute",
            "variants__assigned_attributes__attribute_value",
            "variants__variant_media__media",
            "variants__stocks__allocations",
            "variants__channel_listings__channel",
            "channel_listings__channel",
            "product_type__attribute_scope_links__attribute",
        )

        if single_object:
            return self.prefetch_related(*common_fields)

        return self.prefetch_related(
            "collections",
            "category",
            *common_fields,
        )


ProductManager = models.Manager.from_queryset(ProductQuerySet)


# ============================================================================
# PRODUCT VARIANT
# ============================================================================


class ProductVariantQuerySet(models.QuerySet):
    """
    Queryset for ProductVariant.
    """
    
    def annotate_quantities(self):
        """
        Annotate variants with inventory quantities.

        quantity:
            Total physical stock.

        quantity_allocated:
            Total stock currently allocated. Computed from
            Allocation rows; there is no cached counter on Stock.

        available_quantity:
            Physical stock minus allocated stock.

        All quantities are Decimal(12, 3) — market items can be sold
        by continuous units (2.5 kg, 0.75 l) and the annotation must
        not truncate to integers.
        """

        from warehouse.models import Allocation

        allocations_subquery = (
            Allocation.objects.using(self.db)
            .filter(
                stock__product_variant_id=OuterRef("pk")
            )
            .values(
                "stock__product_variant_id"
            )
            .annotate(
                total_allocated=Coalesce(
                    Sum("quantity_allocated"),
                    Value(0),
                )
            )
            .values("total_allocated")
        )

        allocated_expression = Coalesce(
            Subquery(
                allocations_subquery,
                output_field=models.DecimalField(
                    max_digits=12,
                    decimal_places=3,
                ),
            ),
            Value(0),
        )

        return (
            self.annotate(
                quantity=Coalesce(
                    Sum("stocks__quantity"),
                    Value(0),
                ),
            )
            .annotate(
                quantity_allocated=allocated_expression,
            )
            .annotate(
                available_quantity=ExpressionWrapper(
                    F("quantity") - F("quantity_allocated"),
                    output_field=models.DecimalField(
                        max_digits=12,
                        decimal_places=3,
                    ),
                )
            )
        )
    
    def available_in_channel(
        self,
        channel: Optional[Channel],
    ):
        """
        Return variants that have a price configured for the channel.
        """

        if not channel or not channel.is_active:
            return self.none()

        from ecommerce.models.product import ProductVariantChannelListing

        channel_variants = (
            ProductVariantChannelListing.objects.using(self.db)
            .filter(
                channel_id=channel.pk,
                price_amount__isnull=False,
            )
            .values("variant_id")
        )

        return self.filter(
            Exists(
                channel_variants.filter(
                    variant_id=OuterRef("pk")
                )
            )
        )

    def prefetched_for_webhook(self):
        """
        Prefetch relationships required by variant webhook payloads.
        """

        return self.prefetch_related(
            "assigned_attributes__attribute",
            "assigned_attributes__attribute_value",
            "variant_media__media",
        )

    def visible_to_user(
        self,
        requestor: Optional[User],
        channel: Optional[Channel],
        limited_channel_access: bool = False,
    ):
        """
        Return variants visible to the requesting user.
        """

        if requestor and requestor.has_perm(
            "ecommerce.manage_products"
        ):
            if limited_channel_access:
                if not channel:
                    return self.none()

                return self.filter(
                    product__channel_listings__channel_id=channel.pk
                )

            return self.all()

        if not channel or not channel.is_active:
            return self.none()

        now = timezone.now()

        return self.filter(
            channel_listings__channel_id=channel.pk,
            channel_listings__price_amount__isnull=False,
            product__channel_listings__published_at__lte=now,
            product__channel_listings__is_published=True,
            product__channel_listings__visible_in_listings=True,
        )


ProductVariantManager = models.Manager.from_queryset(
    ProductVariantQuerySet
)


# ============================================================================
# PRODUCT VARIANT CHANNEL LISTING
# ============================================================================


class ProductVariantChannelListingQuerySet(models.QuerySet):
    """
    Queryset for variant/channel pricing listings.
    """

    def annotate_preorder_quantity_allocated(self):
        """
        Annotate listings with allocated preorder quantity.
        """

        return self.annotate(
            preorder_quantity_allocated=Coalesce(
                Sum("preorder_allocations__quantity"),
                Value(0),
            )
        )


ProductVariantChannelListingManager = models.Manager.from_queryset(
    ProductVariantChannelListingQuerySet
)


# ============================================================================
# COLLECTION
# ============================================================================


class CollectionQuerySet(models.QuerySet):
    """
    Queryset for product collections.
    """

    def published(self, channel_slug: str):
        """
        Return collections published on an active channel.
        """

        if not channel_slug:
            return self.none()

        now = timezone.now()

        return self.filter(
            Q(channel_listings__published_at__lte=now)
            | Q(channel_listings__published_at__isnull=True),
            channel_listings__channel__slug=str(channel_slug),
            channel_listings__channel__is_active=True,
            channel_listings__is_published=True,
        ).distinct()

    def visible_to_user(
        self,
        requestor: Optional[User],
        channel_slug: Optional[str],
    ):
        """
        Return collections visible to the requesting user.
        """

        if requestor and requestor.has_perm(
            "ecommerce.manage_products"
        ):
            if channel_slug:
                return self.filter(
                    channel_listings__channel__slug=str(channel_slug)
                ).distinct()

            return self.all()

        if not channel_slug:
            return self.none()

        return self.published(channel_slug)


CollectionManager = models.Manager.from_queryset(
    CollectionQuerySet
)