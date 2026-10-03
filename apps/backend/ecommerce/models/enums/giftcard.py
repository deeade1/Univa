# apps/backend/ecommerce/models/enums/giftcard.py
"""Gift card enums."""


class GiftCardEvents:
    ISSUED = "issued"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    BALANCE_RESET = "balance_reset"
    USED = "used"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    TRANSFERRED = "transferred"

    CHOICES = [
        (ISSUED, "Issued"),
        (ACTIVATED, "Activated"),
        (DEACTIVATED, "Deactivated"),
        (BALANCE_RESET, "Balance Reset"),
        (USED, "Used"),
        (EXPIRED, "Expired"),
        (REFUNDED, "Refunded"),
        (TRANSFERRED, "Transferred"),
    ]


class GiftCardStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    USED = "used"
    PARTIALLY_USED = "partially_used"
    REFUNDED = "refunded"

    CHOICES = [
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
        (EXPIRED, "Expired"),
        (USED, "Used"),
        (PARTIALLY_USED, "Partially Used"),
        (REFUNDED, "Refunded"),
    ]