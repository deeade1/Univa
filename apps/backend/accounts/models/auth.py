# apps/backend/accounts/models/auth.py

import hashlib
import logging
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db import transaction

logger = logging.getLogger(__name__)


class MagicLoginToken(models.Model):
    """
    Secure, single-use token for passwordless authentication flows.

    This model belongs entirely to the accounts domain.

    Supported purposes:
        - login
        - verification
        - recovery

    Device/browser information is retained as security context only.
    Domain applications must not be imported here.
    """

    PURPOSE_CHOICES = [
        ("login", "Login"),
        ("verification", "Verification"),
        ("recovery", "Account Recovery"),
    ]

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="magic_login_tokens",
    )

    # ------------------------------------------------------------------
    # Token
    # ------------------------------------------------------------------

    token = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    expires_at = models.DateTimeField(
        db_index=True,
    )

    used = models.BooleanField(
        default=False,
        db_index=True,
    )

    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        default="login",
        db_index=True,
    )

    redirect_to = models.CharField(
        max_length=512,
        blank=True,
        null=True,
    )

    # ------------------------------------------------------------------
    # Security Context
    # ------------------------------------------------------------------

    device_info = models.JSONField(
        default=dict,
        blank=True,
    )

    device_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
    )

    browser_fingerprint = models.JSONField(
        default=dict,
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    session_data = models.JSONField(
        default=dict,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Timestamp
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "token",
                    "expires_at",
                    "used",
                    "purpose",
                ],
                name="magic_token_lookup_idx",
            ),
            models.Index(
                fields=[
                    "user",
                    "purpose",
                    "used",
                ],
                name="magic_user_purpose_idx",
            ),
            models.Index(
                fields=[
                    "device_fingerprint",
                ],
                name="magic_device_fp_idx",
            ),
        ]

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    @classmethod
    def create_for_user(
        cls,
        user,
        request=None,
        **kwargs,
    ):
        """
        Create a new magic-login token for a user.
        """

        token = get_random_string(64)

        expires_at = timezone.now() + timedelta(
            minutes=getattr(
                settings,
                "MAGIC_LINK_EXPIRY_MINUTES",
                15,
            )
        )

        device_info = cls._get_device_info(request)

        device_fingerprint = cls._generate_device_fingerprint(
            device_info,
        )

        browser_fingerprint = cls._get_browser_fingerprint(
            request,
        )

        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            device_info=device_info,
            device_fingerprint=device_fingerprint,
            browser_fingerprint=browser_fingerprint,
            ip_address=device_info.get(
                "ip_address",
                "",
            ) or None,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Device Information
    # ------------------------------------------------------------------

    @staticmethod
    def _get_device_info(request):
        """
        Extract security-relevant device information.
        """

        if request is None:
            return {}

        meta = request.META

        return {
            "user_agent": meta.get(
                "HTTP_USER_AGENT",
                "",
            )[:500],

            "ip_address": meta.get(
                "REMOTE_ADDR",
                "",
            ),

            "device_id": meta.get(
                "HTTP_X_DEVICE_ID",
                "",
            ),

            "accept_language": meta.get(
                "HTTP_ACCEPT_LANGUAGE",
                "",
            )[:100],

            "accept_encoding": meta.get(
                "HTTP_ACCEPT_ENCODING",
                "",
            )[:100],

            "screen_resolution": meta.get(
                "HTTP_X_SCREEN_RESOLUTION",
                "",
            ),

            "timezone": meta.get(
                "HTTP_X_TIMEZONE",
                "",
            ),
        }

    @staticmethod
    def _generate_device_fingerprint(
        device_info,
    ):
        """
        Generate a deterministic SHA-256 device fingerprint.
        """

        if not device_info:
            return None

        fingerprint_data = (
            f"{device_info.get('user_agent', '')}"
            f"{device_info.get('accept_language', '')}"
            f"{device_info.get('accept_encoding', '')}"
            f"{device_info.get('screen_resolution', '')}"
            f"{device_info.get('timezone', '')}"
        )

        if not fingerprint_data:
            return None

        return hashlib.sha256(
            fingerprint_data.encode("utf-8"),
        ).hexdigest()

    @staticmethod
    def _get_browser_fingerprint(request):
        """
        Extract browser-specific security context.
        """

        if request is None:
            return {}

        meta = request.META

        return {
            "user_agent": meta.get(
                "HTTP_USER_AGENT",
                "",
            )[:500],

            "accept_headers": {
                "language": meta.get(
                    "HTTP_ACCEPT_LANGUAGE",
                    "",
                ),
                "encoding": meta.get(
                    "HTTP_ACCEPT_ENCODING",
                    "",
                ),
                "charset": meta.get(
                    "HTTP_ACCEPT_CHARSET",
                    "",
                ),
            },

            "connection": meta.get(
                "HTTP_CONNECTION",
                "",
            ),

            "platform": meta.get(
                "HTTP_SEC_CH_UA_PLATFORM",
                "",
            ),
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @classmethod
    def validate_token(
        cls,
        token,
        purpose=None,
        request=None,
    ):
        """
        Validate a magic token.

        Returns:
            MagicLoginToken

        Raises:
            ValueError
        """

        try:
            record = cls.objects.select_related(
                "user",
            ).get(
                token=token,
            )
        except cls.DoesNotExist:
            raise ValueError(
                "Invalid token",
            )

        if record.used:
            raise ValueError(
                "Token already used",
            )

        if timezone.now() > record.expires_at:
            raise ValueError(
                "Token expired",
            )

        if purpose and record.purpose != purpose:
            raise ValueError(
                "Invalid token purpose",
            )

        # --------------------------------------------------------------
        # Optional device verification
        # --------------------------------------------------------------

        if request and record.device_fingerprint:
            current_fingerprint = (
                cls._generate_device_fingerprint(
                    cls._get_device_info(request),
                )
            )

            if (
                current_fingerprint
                != record.device_fingerprint
            ):
                logger.warning(
                    "Device fingerprint mismatch for magic "
                    "login token %s",
                    record.pk,
                )

                # Intentionally lenient for now.
                #
                # Authentication policy can decide whether a
                # mismatch should invalidate the token.
                #
                # Do NOT silently change this to a hard failure
                # until the frontend/device flow is confirmed.

        return record

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def mark_as_used(self):
        """
        Atomically consume this magic-login token.

        Returns:
            bool: True if this call consumed the token,
            False if it had already been consumed.
        """
        with transaction.atomic():
            updated = (
                type(self)
                .objects
                .filter(
                    pk=self.pk,
                    used=False,
                )
                .update(
                    used=True,
                )
            )

        if updated:
            self.used = True
            return True

        self.used = True
        return False
    
    # ------------------------------------------------------------------
    # URL
    # ------------------------------------------------------------------

    '''def get_absolute_url(self):
        """
        Generate the absolute magic-link URL pointing at the frontend.

        The frontend route is expected to extract the token from the
        URL and call the GraphQL mutation that consumes it.

        Uses:
            settings.FRONTEND_URL

        Example produced URL:

            http://localhost:8081/magic-link/<token>
        """

        base_url = getattr(
            settings,
            "FRONTEND_URL",
            "",
        ).rstrip("/")

        return (
            f"{base_url}"
            f"/magic-link/{self.token}"
        )'''

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self):
        return (
            f"Magic token for "
            f"{self.user.email} - "
            f"{self.purpose}"
        )