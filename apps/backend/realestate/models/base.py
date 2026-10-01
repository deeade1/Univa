# apps/backend/realestate/models/base.py

"""
Base models and shared utilities for the real estate app.
"""

import logging
import uuid

from django.contrib.postgres.indexes import BTreeIndex
from django.db import models

logger = logging.getLogger(__name__)


def listing_dir_path(instance, filename):
    """
    Generate a stable upload path for listing files/images.
    """
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    generated_name = f"{instance.pk or uuid.uuid4().hex}"

    if ext:
        generated_name = f"{generated_name}.{ext}"

    return f"listings/{generated_name}"


class TimeStampedModel(models.Model):
    """
    Abstract base model providing creation and modification timestamps.
    """

    created = models.DateTimeField(
        auto_now_add=True,
    )

    updated = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = True

        indexes = [
            BTreeIndex(
                fields=["created"],
                name="%(class)s_created_idx",
            ),
            BTreeIndex(
                fields=["updated"],
                name="%(class)s_updated_idx",
            ),
        ]