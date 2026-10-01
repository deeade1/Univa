# apps/backend/accounts/services.py

"""
Account-level authentication services.

This module contains authentication helpers that sit at the boundary
between the accounts domain and authentication mechanisms.

Architecture:

    User
      │
      ├── biometric_devices
      │
      └── magic_login_tokens

BiometricDevice belongs directly to the canonical User model.
UserProfile is intentionally not involved in authentication ownership.
"""

import json

from django.utils import timezone

from biometrics.models import BiometricDevice
from .models import MagicLoginToken


# ============================================================================
# BIOMETRIC AUTHENTICATION
# ============================================================================

def verify_biometric_token(token):
    """
    Verify a trusted biometric device token.

    Accepted input:
        - dict containing device_id and user_id
        - JSON string containing device_id and user_id

    Returns:
        User instance when the device is valid and trusted.
        None when verification fails.

    Expected payload:

        {
            "device_id": "...",
            "user_id": 123
        }

    The biometric device belongs directly to User:

        BiometricDevice.user -> User
    """

    try:
        # ------------------------------------------------------------------
        # Normalize token payload
        # ------------------------------------------------------------------

        if isinstance(token, dict):
            token_data = token

        elif isinstance(token, str):
            token = token.strip()

            if not token:
                return None

            # Biometric payloads are JSON objects.
            if not (token.startswith("{") and token.endswith("}")):
                return None

            try:
                token_data = json.loads(token)
            except json.JSONDecodeError:
                return None

        else:
            return None

        # ------------------------------------------------------------------
        # Validate payload structure
        # ------------------------------------------------------------------

        if not isinstance(token_data, dict):
            return None

        device_id = token_data.get("device_id")
        user_id = token_data.get("user_id")

        if not device_id or user_id in (None, ""):
            return None

        # ------------------------------------------------------------------
        # Resolve trusted biometric device
        # ------------------------------------------------------------------

        device = (
            BiometricDevice.objects
            .select_related("user")
            .get(
                device_id=device_id,
                user_id=user_id,
                trusted=True,
            )
        )

        # ------------------------------------------------------------------
        # Update device usage timestamp
        # ------------------------------------------------------------------

        device.mark_used()

        # ------------------------------------------------------------------
        # Return canonical User
        # ------------------------------------------------------------------

        return device.user

    except BiometricDevice.DoesNotExist:
        return None

    except (TypeError, ValueError):
        return None

    except Exception:
        # Authentication helpers should fail closed.
        return None


# ============================================================================
# MAGIC LOGIN
# ============================================================================

def verify_magic_login_token(token):
    """
    Verify a magic login token.

    Returns:
        User instance when the token is valid.
        None when the token is invalid, expired, already used,
        or otherwise unusable.
    """

    try:
        # ------------------------------------------------------------------
        # Basic token validation
        # ------------------------------------------------------------------

        if not isinstance(token, str):
            return None

        token = token.strip()

        if not token or token == "null" or len(token) < 10:
            return None

        # ------------------------------------------------------------------
        # Validate signed/token record
        # ------------------------------------------------------------------

        record = MagicLoginToken.validate_token(
            token,
            purpose="login",
        )

        # ------------------------------------------------------------------
        # Explicit security checks
        # ------------------------------------------------------------------

        if record.used:
            return None

        if record.expires_at <= timezone.now():
            return None

        # ------------------------------------------------------------------
        # Consume token
        # ------------------------------------------------------------------

        record.mark_as_used()

        # ------------------------------------------------------------------
        # Return canonical User
        # ------------------------------------------------------------------

        return record.user

    except Exception:
        # Authentication must fail closed.
        return None

