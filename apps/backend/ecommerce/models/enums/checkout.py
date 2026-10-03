# apps/backend/ecommerce/models/enums/checkout.py
"""Checkout enums."""


class CheckoutAuthorizeStatus:
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"

    CHOICES = [
        (NONE, "Not authorized"),
        (PARTIAL, "Partially authorized"),
        (FULL, "Fully authorized"),
    ]


class CheckoutChargeStatus:
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"
    OVERCHARGED = "overcharged"

    CHOICES = [
        (NONE, "Not charged"),
        (PARTIAL, "Partially charged"),
        (FULL, "Fully charged"),
        (OVERCHARGED, "Overcharged"),
    ]