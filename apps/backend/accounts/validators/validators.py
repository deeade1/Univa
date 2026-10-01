# apps/backend/accounts/validators/validators.py

from django.core.exceptions import ValidationError
from phonenumbers import parse as to_python, is_possible_number, is_valid_number
from phonenumbers.phonenumberutil import region_code_for_number
from .error_codes import AccountErrorCode

ALLOWED_REGIONS = ["US", "GB", "NG"]


def validate_possible_number(phone, country=None):
    """
    Validate a phone number.
    
    Args:
        phone: Phone number string to validate.
        country: Optional country code (e.g., "US") for parsing.
    
    Raises:
        ValidationError: If the phone number is invalid.
    
    Returns:
        The parsed phone number object.
    """
    try:
        phone_number = to_python(phone, country)
    except Exception:
        raise ValidationError(
            "Invalid phone number format.",
            code=AccountErrorCode.INVALID.value,
        )

    # Validate phone structure
    if phone_number and (not is_possible_number(phone_number) or not is_valid_number(phone_number)):
        raise ValidationError(
            "The phone number entered is not valid.",
            code=AccountErrorCode.INVALID.value,
        )

    # Restrict regions
    if phone_number and region_code_for_number(phone_number) not in ALLOWED_REGIONS:
        raise ValidationError(
            f"Phone number must be from one of: {', '.join(ALLOWED_REGIONS)}.",
            code=AccountErrorCode.INVALID.value,
        )

    return phone_number