# graphq/ecommerce/tests/conftest.py

"""
Shared fixtures for ecommerce GraphQL tests.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from graphene.test import Client
from accounts.models import Address
from ecommerce.models.channel import Channel
from ecommerce.models.product import (
    Product,
    ProductChannelListing,
    ProductType,
    ProductVariant,
    ProductVariantChannelListing,
)
from ecommerce.models.inventory import Stock
from ecommerce.models.shipping import (
    ShippingMethod,
    ShippingMethodChannelListing,
    ShippingZone,
)
from ecommerce.models.warehouse import Warehouse


User = get_user_model()


# =====================================================================
# CLIENT
# =====================================================================


@pytest.fixture
def gql_client():
    """Graphene test client bound to the project schema."""
    from backend.schema import schema as project_schema
    return Client(project_schema)


class FakeRequest:
    """
    Minimal context object for GraphQL execution.

    Matches what the resolvers and decorators read:
        info.context.user
        info.context.session
        info.context.META
    """

    def __init__(self, user, session=None):
        self.user = user
        self.session = session if session is not None else {}
        self.META = {"REMOTE_ADDR": "127.0.0.1"}


# =====================================================================
# CHANNEL
# =====================================================================


@pytest.fixture
def channel(db):
    return Channel.objects.create(
        name="Test Channel",
        slug="test-channel",
        currency_code="NGN",
        default_country="NG",
        is_active=True,
    )


@pytest.fixture
def channel_b(db):
    return Channel.objects.create(
        name="Channel B",
        slug="channel-b",
        currency_code="NGN",
        default_country="NG",
        is_active=True,
    )


# =====================================================================
# USERS
# =====================================================================


@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        email="a@example.com",
        password="secret",
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        email="b@example.com",
        password="secret",
    )


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@example.com",
        password="staffsecret",
        is_staff=True,
    )


@pytest.fixture
def anonymous_user():
    from django.contrib.auth.models import AnonymousUser
    return AnonymousUser()


# =====================================================================
# ADDRESSES
# =====================================================================


@pytest.fixture
def address_a(db, user_a):
    return Address.objects.create(
        user=user_a,
        address_type="shipping",
        is_default=True,
        first_name="Test",
        last_name="User",
        company_name="",
        street_address_1="123 Test St",
        street_address_2="",
        city="Lagos",
        city_area="",
        postal_code="100001",
        state="Lagos",
        country="NG",
        country_area="",
        phone="+2348000000000",
        validation_skipped=False,
    )


# =====================================================================
# PRODUCT CATALOG
# =====================================================================


@pytest.fixture
def product_type(db):
    return ProductType.objects.create(
        name="Physical",
        slug="physical-e2e",
        kind="normal",
        has_variants=True,
        is_shipping_required=True,
    )


@pytest.fixture
def product(db, product_type):
    return Product.objects.create(
        name="E2E Test Product",
        slug="e2e-test-product",
        product_type=product_type,
    )


@pytest.fixture
def variant(db, product):
    return ProductVariant.objects.create(
        sku="E2E-SKU-001",
        product=product,
        name="Default",
        track_inventory=True,
    )


@pytest.fixture
def variant_b(db, product):
    return ProductVariant.objects.create(
        sku="E2E-SKU-002",
        product=product,
        name="Second",
        track_inventory=True,
    )


@pytest.fixture
def product_listing(db, product, channel):
    return ProductChannelListing.objects.create(
        product=product,
        channel=channel,
        currency="NGN",
        price_amount=Decimal("1000.00"),
        visible_in_listings=True,
    )


@pytest.fixture
def variant_listing(db, variant, channel):
    return ProductVariantChannelListing.objects.create(
        variant=variant,
        channel=channel,
        currency="NGN",
        price_amount=Decimal("1000.00"),
    )


@pytest.fixture
def variant_b_listing(db, variant_b, channel):
    return ProductVariantChannelListing.objects.create(
        variant=variant_b,
        channel=channel,
        currency="NGN",
        price_amount=Decimal("500.00"),
    )


# =====================================================================
# WAREHOUSE + STOCK
# =====================================================================


@pytest.fixture
def warehouse(db, channel, address_a):
    wh = Warehouse.objects.create(
        name="Main Warehouse",
        slug="main-warehouse-e2e",
        address=address_a,
    )
    wh.channels.add(channel)
    return wh


@pytest.fixture
def stock(db, warehouse, variant):
    return Stock.objects.create(
        warehouse=warehouse,
        product_variant=variant,
        quantity=Decimal("100.000"),
    )


@pytest.fixture
def stock_b(db, warehouse, variant_b):
    return Stock.objects.create(
        warehouse=warehouse,
        product_variant=variant_b,
        quantity=Decimal("100.000"),
        
    )


# =====================================================================
# SHIPPING
# =====================================================================


@pytest.fixture
def shipping_zone(db, channel):
    zone = ShippingZone.objects.create(
        name="Test Zone",
        description="E2E test zone",
        is_active=True,
        default=True,
    )
    zone.channels.add(channel)
    return zone


@pytest.fixture
def shipping_method(db, shipping_zone, channel):
    method = ShippingMethod.objects.create(
        name="Standard Shipping",
        type="price",
        status="active",
        is_active=True,
        shipping_zone=shipping_zone,
    )
    ShippingMethodChannelListing.objects.create(
        shipping_method=method,
        channel=channel,
        price_amount=Decimal("500.00"),
        currency="NGN",
        is_active=True,
    )
    return method


