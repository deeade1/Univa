"""
Database-backed refresh tokens — DEPRECATED.

Canonical refresh tokens are JWTs validated through tokens.py
and revoked through revocation.py.

This model is retained for backward compatibility only.
"""

import secrets
import warnings

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from univa_jwt import managers
from univa_jwt.settings import jwt_settings
from univa_jwt.utils import refresh_has_expired

warnings.warn(
    "RefreshToken model is deprecated. Use canonical JWT refresh "
    "tokens via tokens.create_refresh_token() and refresh.rotate_refresh_token().",
    DeprecationWarning,
    stacklevel=2,
)


class RefreshToken(models.Model):
    """
    DEPRECATED: Persistent refresh token.

    The canonical JWT refresh system does not use this model for
    validation. This is retained for backward compatibility only.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
        verbose_name=_("user"),
    )

    token = models.CharField(
        _("token"),
        max_length=255,
        unique=True,
        editable=False,
    )

    created = models.DateTimeField(
        _("created"),
        auto_now_add=True,
    )

    revoked = models.DateTimeField(
        _("revoked"),
        null=True,
        blank=True,
    )

    replaced_by = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaced_token",
    )

    class Meta:
        verbose_name = _("refresh token")
        verbose_name_plural = _("refresh tokens")

        indexes = [
            models.Index(
                fields=["user", "revoked"],
            ),
            models.Index(
                fields=["created"],
            ),
        ]

    objects = managers.RefreshTokenQuerySet.as_manager()

    def __str__(self):
        return f"RefreshToken<{self.pk}>"

    @classmethod
    def generate_token(cls):
        return secrets.token_urlsafe(48)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()

        super().save(*args, **kwargs)

    @property
    def is_revoked(self):
        return self.revoked is not None

    def is_expired(self):
        if not self.created:
            return True

        return refresh_has_expired(
            self.created.timestamp(),
        )

    def is_valid(self):
        return (
            not self.is_revoked
            and not self.is_expired()
            and self.user_id is not None
            and self.user.is_active
        )

    def revoke(self, *, replacement=None):
        """
        Deprecated: use revocation.revoke_jti().

        DEPRECATED: This method will be removed in a future version.
        """
        warnings.warn(
            "RefreshToken.revoke() is deprecated. "
            "Use revocation.revoke_jti().",
            DeprecationWarning,
            stacklevel=2,
        )

        if self.revoked is None:
            self.revoked = timezone.now()

            if replacement is not None:
                self.replaced_by = replacement

            self.save(
                update_fields=[
                    "revoked",
                    "replaced_by",
                ]
            )

        # Also mark as revoked in the canonical revocation system
        try:
            from univa_jwt.revocation import revoke_jti

            # If we have a JTI claim value stored, use it
            jti = getattr(self, "jti", None)

            if jti:
                revoke_jti(
                    jti=jti,
                    expires_at=self.created,
                    user_id=self.user_id,
                    token_type="refresh",
                )
        except ImportError:
            pass

    def rotate(self):
        """
        Deprecated: use refresh.rotate_refresh_token().

        DEPRECATED: This method will be removed in a future version.
        """
        warnings.warn(
            "RefreshToken.rotate() is deprecated. "
            "Use refresh.rotate_refresh_token().",
            DeprecationWarning,
            stacklevel=2,
        )

        if not self.is_valid():
            raise ValueError(
                "Cannot rotate an invalid refresh token."
            )

        new_token = RefreshToken.objects.create(
            user=self.user,
        )

        self.revoke(
            replacement=new_token,
        )

        return new_token


__all__ = ["RefreshToken"]