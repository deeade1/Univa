"""
Gift card validators.

These validators are intentionally kept outside the ecommerce.models
package so Django migrations can import them without loading the entire
ecommerce model graph.
"""

from django.core.exceptions import ValidationError


def validate_gift_card_code(value):
    """
    Validate a gift card code.

    Gift card codes must:

        - exist
        - contain at least 8 characters
        - contain only letters and numbers

    The validator intentionally does not perform uniqueness checks.
    Uniqueness is enforced by the database through the GiftCard.code
    unique constraint.
    """

    if not value:
        raise ValidationError(
            "Gift card code must be at least 8 characters long."
        )

    if len(value) < 8:
        raise ValidationError(
            "Gift card code must be at least 8 characters long."
        )

    if not value.isalnum():
        raise ValidationError(
            "Gift card code must contain only letters and numbers."
        )