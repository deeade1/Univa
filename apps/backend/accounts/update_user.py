# apps/backend/accounts/services/update_user.py

from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from accounts.validators import validate_possible_number
from accounts.models import UserProfile

User = get_user_model()

# -----------------------------
# PHONE NORMALIZATION HELPERS
# -----------------------------

NIGERIAN_PREFIXES = (
    "070",
    "071",
    "080",
    "081",
    "090",
    "091",
)

def normalize_nigeria_phone(phone: str) -> str:
    """Convert Nigerian phone formats to E164 before validation."""

    if not phone:
        return None

    phone = phone.strip().replace(" ", "").replace("-", "")

    # If already international format
    if phone.startswith("+234"):
        return phone

    # If starts with 234 but missing "+"
    if phone.startswith("234") and len(phone) >= 13:
        return "+" + phone

    # Convert 11-digit Nigerian local number
    if phone.startswith("0") and len(phone) == 11:
        prefix = phone[:3]
        if prefix in NIGERIAN_PREFIXES:
            # Convert: 08012345678 -> +2348012345678
            return "+234" + phone[1:]

    # Convert 10-digit numbers (rare, but allow)
    if len(phone) == 10:
        return "+234" + phone

    return phone  # let validator handle rejection


def normalize_phone(phone: str):
    """Normalize and validate phone numbers using Nigerian formatting."""
    if not phone:
        return None

    phone = normalize_nigeria_phone(phone)

    try:
        parsed = validate_possible_number(phone, country="NG")
        return str(parsed)  # E164 normalized output
    except ValidationError as e:
        raise ValidationError(f"Invalid phone number: {e}")


# -----------------------------
# EMAIL NORMALIZATION
# -----------------------------
def normalize_email(email: str):
    if not email:
        return None
    return email.strip().lower()


# -----------------------------
# MAIN UPDATE FUNCTION
# -----------------------------
@transaction.atomic
def update_user_and_profile(user, user_data, profile_data):
    """
    Unified update for User + Profile.
    Handles:
    - email normalization
    - Nigerian phone cleanup
    - phone validation via your custom validator
    - profile auto-creation
    """

    # ------- USER FIELDS -------
    if "email" in user_data:
        user.email = normalize_email(user_data["email"])

    if "phone_number" in user_data:
        user.phone_number = normalize_phone(user_data["phone_number"])

    if "first_name" in user_data:
        user.first_name = user_data["first_name"]

    if "last_name" in user_data:
        user.last_name = user_data["last_name"]

    user.save()

    # ------- PROFILE FIELDS -------
    profile, _ = UserProfile.objects.get_or_create(user=user)

    for field, value in profile_data.items():
        setattr(profile, field, value)

    profile.save()

    return user, profile






