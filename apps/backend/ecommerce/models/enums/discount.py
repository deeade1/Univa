# apps/backend/ecommerce/models/enums/discount.py
"""Discount, voucher, and promotion enums."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ecommerce.models.discount import PromotionRule


class VoucherType:
    ENTIRE_ORDER = "entire_order"
    SHIPPING = "shipping"
    SPECIFIC_PRODUCT = "specific_product"

    CHOICES = [
        (ENTIRE_ORDER, "Entire order"),
        (SHIPPING, "Shipping"),
        (SPECIFIC_PRODUCT, "Specific product"),
    ]


class DiscountValueType:
    FIXED = "fixed"
    PERCENTAGE = "percentage"

    CHOICES = [
        (FIXED, "Fixed"),
        (PERCENTAGE, "Percentage"),
    ]


class DiscountType:
    MANUAL = "manual"
    VOUCHER = "voucher"
    PROMOTION = "promotion"
    SALE = "sale"
    ORDER_PROMOTION = "order_promotion"

    CHOICES = [
        (MANUAL, "Manual"),
        (VOUCHER, "Voucher"),
        (PROMOTION, "Promotion"),
        (SALE, "Sale"),
        (ORDER_PROMOTION, "Order promotion"),
    ]


class PromotionType:
    CATALOGUE = "catalogue"
    ORDER = "order"

    CHOICES = [
        (CATALOGUE, "Catalogue"),
        (ORDER, "Order"),
    ]


class RewardType:
    DISCOUNT = "discount"
    GIFT = "gift"
    SUBTOTAL_DISCOUNT = "subtotal_discount"

    CHOICES = [
        (DISCOUNT, "Discount"),
        (GIFT, "Gift"),
        (SUBTOTAL_DISCOUNT, "Subtotal discount"),
    ]


class RewardValueType:
    FIXED = "fixed"
    PERCENTAGE = "percentage"

    CHOICES = [
        (FIXED, "Fixed"),
        (PERCENTAGE, "Percentage"),
    ]


class PromotionEvents:
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    RULE_CREATED = "rule_created"
    RULE_UPDATED = "rule_updated"
    RULE_DELETED = "rule_deleted"
    RULE_ACTIVATED = "rule_activated"
    RULE_DEACTIVATED = "rule_deactivated"
    PROMOTION_CREATED = "promotion_created"
    PROMOTION_UPDATED = "promotion_updated"
    PROMOTION_STARTED = "promotion_started"
    PROMOTION_ENDED = "promotion_ended"

    CHOICES = [
        (CREATED, "Created"),
        (UPDATED, "Updated"),
        (DELETED, "Deleted"),
        (ACTIVATED, "Activated"),
        (DEACTIVATED, "Deactivated"),
        (RULE_CREATED, "Rule created"),
        (RULE_UPDATED, "Rule updated"),
        (RULE_DELETED, "Rule deleted"),
        (RULE_ACTIVATED, "Rule activated"),
        (RULE_DEACTIVATED, "Rule deactivated"),
        (PROMOTION_CREATED, "Promotion created"),
        (PROMOTION_UPDATED, "Promotion updated"),
        (PROMOTION_STARTED, "Promotion started"),
        (PROMOTION_ENDED, "Promotion ended"),
    ]


@dataclass
class PromotionRuleInfo:
    rule: "PromotionRule"
    channel_ids: list[int]