# apps/backend/ecommerce/models/enums/shipping.py
"""Shipping enums."""


class ShippingMethodType:
    PRICE_BASED = "price"
    WEIGHT_BASED = "weight"

    CHOICES = [
        (PRICE_BASED, "Price based shipping"),
        (WEIGHT_BASED, "Weight based shipping"),
    ]


class PostalCodeRuleInclusionType:
    INCLUDE = "include"
    EXCLUDE = "exclude"

    CHOICES = [
        (INCLUDE, "Shipping method should include postal code rule"),
        (EXCLUDE, "Shipping method should exclude postal code rule"),
    ]


class ShippingMethodStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"

    CHOICES = [
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
        (DISCONTINUED, "Discontinued"),
    ]