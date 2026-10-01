# apps/backend/core/models/publishable.py

"""
Reusable publishable model.

Provides:

    published_at
    is_published

and a queryset helper for retrieving currently published objects.
"""

from __future__ import annotations

from typing import Any, TypeVar

from django.db import models
from django.db.models import Q
from django.utils import timezone


T = TypeVar(
    "T",
    bound="PublishableModel",
)


class PublishedQuerySet(
    models.QuerySet[T]
):
    """
    QuerySet containing helpers for published objects.
    """

    def published(self):
        """
        Return objects that are marked as published and whose
        publication date has arrived.
        """

        now = timezone.now()

        return self.filter(
            Q(
                published_at__lte=now
            )
            | Q(
                published_at__isnull=True
            ),
            is_published=True,
        )


PublishableManager = models.Manager.from_queryset(
    PublishedQuerySet
)


class PublishableModel(models.Model):
    """
    Abstract model for publishable domain objects.
    """

    published_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    is_published = models.BooleanField(
        default=False,
    )

    objects: Any = PublishableManager()

    class Meta:
        abstract = True

    @property
    def is_visible(self) -> bool:
        """
        Return whether this object is currently visible.
        """

        return (
            self.is_published
            and (
                self.published_at is None
                or self.published_at <= timezone.now()
            )
        )
