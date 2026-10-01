"""
QuerySet and manager utilities for refresh tokens.
"""

from django.db import models
from django.db.models import Case, Value, When
from django.utils import timezone

from univa_jwt.settings import jwt_settings


class RefreshTokenQuerySet(models.QuerySet):
    def expired(self):
        expiration_time = (
            timezone.now()
            - jwt_settings.UNIVA_JWT_REFRESH_EXPIRATION_DELTA
        )

        return self.annotate(
            expired=Case(
                When(
                    created__lt=expiration_time,
                    then=Value(True),
                ),
                default=Value(False),
                output_field=models.BooleanField(),
            )
        )

    def active(self):
        return self.filter(
            revoked__isnull=True,
        ).filter(
            created__gte=(
                timezone.now()
                - jwt_settings.UNIVA_JWT_REFRESH_EXPIRATION_DELTA
            )
        )

    def revoked(self):
        return self.filter(
            revoked__isnull=False,
        )