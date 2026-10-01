# apps/backend/biometrics/models/encoding.py

"""
Face encoding model.

Architecture
------------

FaceEncoding is the persistent representation of a user's facial
embedding.

The biometrics domain owns:

    - face embeddings
    - embedding versions
    - activation/deactivation
    - source verification images
    - embedding metadata

Vector matching itself belongs to:

    biometrics.services.matching

This model does NOT contain:

    - GraphQL logic
    - authentication logic
    - JWT logic
    - raw SQL
    - face-detection logic
    - matching policy

Storage
-------

The canonical representation is:

    embedding = pgvector VectorField(512)

The legacy `encoding` BinaryField is retained temporarily for
backwards compatibility and migration purposes.

Matching
--------

The canonical matching metric is cosine distance.

The corresponding pgvector HNSW operator class is:

    vector_cosine_ops
"""

from __future__ import annotations

import pickle

import numpy as np

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from pgvector.django import HnswIndex, VectorField


# ============================================================================
# CONSTANTS
# ============================================================================

FACE_EMBEDDING_DIMENSIONS = 512

FACE_ENCODING_VERSION = "v1"

MAX_EMBEDDING_ABSOLUTE_VALUE = 10.0


# ============================================================================
# FACE ENCODING
# ============================================================================


class FaceEncoding(models.Model):
    """
    Persistent facial embedding for a user.

    A user may have multiple historical encodings, but only active
    encodings participate in biometric authentication.

    The preferred representation is the pgvector `embedding` field.

    The legacy `encoding` BinaryField exists only to support existing
    records and migration from the previous implementation.
    """

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="face_encodings",
        verbose_name=_("user"),
    )

    # ------------------------------------------------------------------
    # Legacy representation
    # ------------------------------------------------------------------

    encoding = models.BinaryField(
        null=True,
        blank=True,
        editable=False,
        help_text=_(
            "Legacy serialized face embedding. "
            "Retained temporarily for migration compatibility."
        ),
    )

    # ------------------------------------------------------------------
    # Canonical pgvector representation
    # ------------------------------------------------------------------

    embedding = VectorField(
        dimensions=FACE_EMBEDDING_DIMENSIONS,
        null=True,
        blank=True,
        help_text=_(
            "Canonical 512-dimensional ArcFace embedding."
        ),
    )

    # ------------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------------

    version = models.CharField(
        max_length=20,
        default=FACE_ENCODING_VERSION,
        db_index=True,
        help_text=_(
            "Embedding/model version used to generate this encoding."
        ),
    )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_(
            "Whether this encoding is eligible for biometric matching."
        ),
    )

    # ------------------------------------------------------------------
    # Source image
    # ------------------------------------------------------------------

    source_image = models.ForeignKey(
        "biometrics.FaceVerificationImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="face_encodings",
        help_text=_(
            "Image from which this face encoding was generated."
        ),
    )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "Non-sensitive metadata associated with the embedding."
        ),
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        ordering = ["-created_at"]

        verbose_name = _("Face Encoding")
        verbose_name_plural = _("Face Encodings")

        indexes = [
            models.Index(
                fields=["user", "is_active"],
                name="face_enc_user_active_idx",
            ),
            models.Index(
                fields=["user", "version"],
                name="face_enc_user_version_idx",
            ),
            models.Index(
                fields=["created_at"],
                name="face_enc_created_idx",
            ),
            HnswIndex(
                name="face_enc_embedding_cos_idx",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self):
        email = getattr(self.user, "email", None)
        if email:
            return f"Face Encoding: {email} [{self.version}]"
        return f"Face Encoding {self.pk}"

    # ==================================================================
    # VALIDATION
    # ==================================================================

    @classmethod
    def normalize_embedding(cls, embedding) -> list[float]:
        """
        Validate and normalize a 512-dimensional embedding.

        Returns:
            list[float]

        Raises:
            ValidationError
        """

        if embedding is None:
            raise ValidationError(_("Face embedding is required."))

        try:
            vector = np.asarray(embedding, dtype=np.float32)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                _("Face embedding contains invalid values.")
            ) from exc

        if vector.ndim != 1:
            raise ValidationError(
                _("Face embedding must be one-dimensional.")
            )

        if vector.shape != (FACE_EMBEDDING_DIMENSIONS,):
            raise ValidationError(
                _(
                    "Face embedding must contain "
                    f"{FACE_EMBEDDING_DIMENSIONS} dimensions; "
                    f"received {vector.shape}."
                )
            )

        if not np.all(np.isfinite(vector)):
            raise ValidationError(
                _("Face embedding contains non-finite values.")
            )

        if np.any(np.abs(vector) > MAX_EMBEDDING_ABSOLUTE_VALUE):
            raise ValidationError(
                _(
                    "Face embedding contains values outside "
                    "the expected range."
                )
            )

        return vector.tolist()

    def clean(self):
        """
        Validate model state.

        The canonical embedding is preferred. Legacy binary encoding
        is allowed only when an embedding is not available, which
        permits migration of historical data.
        """

        super().clean()

        if self.embedding is not None:
            self.embedding = self.normalize_embedding(self.embedding)

        if self.encoding:
            self._validate_legacy_encoding()

        # Active records must have usable embedding data. This prevents
        # pending placeholder records from accidentally becoming active.
        if self.is_active and self.embedding is None and not self.encoding:
            raise ValidationError(
                _("An active face encoding must have an embedding.")
            )

    def _validate_legacy_encoding(self):
        """
        Validate the legacy serialized embedding.

        This method exists only for compatibility with existing records.
        New code should use `embedding`.
        """

        try:
            decoded = pickle.loads(self.encoding)
        except (
            pickle.PickleError,
            EOFError,
            AttributeError,
            ValueError,
            TypeError,
        ) as exc:
            raise ValidationError(
                _("Invalid legacy face encoding data.")
            ) from exc

        try:
            vector = np.asarray(decoded, dtype=np.float32)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                _("Legacy face encoding contains invalid values.")
            ) from exc

        if vector.ndim != 1:
            raise ValidationError(
                _("Legacy face encoding must be one-dimensional.")
            )

        if vector.shape != (FACE_EMBEDDING_DIMENSIONS,):
            raise ValidationError(
                _(
                    "Legacy face encoding must contain "
                    f"{FACE_EMBEDDING_DIMENSIONS} dimensions."
                )
            )

        if not np.all(np.isfinite(vector)):
            raise ValidationError(
                _("Legacy face encoding contains non-finite values.")
            )

    # ==================================================================
    # SAVE
    # ==================================================================

    def save(self, *args, **kwargs):
        """
        Validate embedding-bearing writes.

        Cheap lifecycle updates (``is_active``, ``updated_at``) skip
        full validation to keep hot paths fast. Writes that touch the
        embedding or the legacy encoding run full validation.
        """

        update_fields = kwargs.get("update_fields")
        force_full = kwargs.pop("full_clean", False)

        touches_embedding = (
            update_fields is None
            or "embedding" in update_fields
            or "encoding" in update_fields
        )

        if force_full or touches_embedding:
            # Normalize embedding in place before persisting. Avoids
            # a second full_clean() when callers already did it.
            if self.embedding is not None:
                self.embedding = self.normalize_embedding(self.embedding)

            self.full_clean()

        super().save(*args, **kwargs)

    # ==================================================================
    # FACTORIES
    # ==================================================================

    @classmethod
    def create_from_embedding(
        cls,
        user,
        embedding,
        *,
        source_image=None,
        is_active=True,
        version=FACE_ENCODING_VERSION,
        metadata=None,
        **kwargs,
    ):
        """
        Create a FaceEncoding from an ArcFace embedding.

        This is the preferred creation API. The embedding is stored in
        both the canonical pgvector field and the legacy binary field
        so existing consumers keep working during migration.
        """

        normalized = cls.normalize_embedding(embedding)
        vector = np.asarray(normalized, dtype=np.float32)

        legacy_encoding = pickle.dumps(
            vector,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

        return cls.objects.create(
            user=user,
            embedding=normalized,
            encoding=legacy_encoding,
            source_image=source_image,
            is_active=is_active,
            version=version,
            metadata=metadata or {},
            **kwargs,
        )

    @classmethod
    def create_pending(
        cls,
        user,
        *,
        source_image=None,
        version=FACE_ENCODING_VERSION,
        metadata=None,
        **kwargs,
    ):
        """
        Create a pending encoding record awaiting an embedding.

        Pending records are always inactive — they have no usable
        embedding yet and must not participate in matching.
        """

        return cls.objects.create(
            user=user,
            embedding=None,
            encoding=None,
            source_image=source_image,
            is_active=False,
            version=version,
            metadata={
                "status": "pending",
                **(metadata or {}),
            },
            **kwargs,
        )

    # ==================================================================
    # LEGACY ACCESS
    # ==================================================================

    def get_decoded_encoding(self):
        """
        Return the legacy serialized embedding as a numpy array.

        Prefer ``self.embedding`` for all new code.
        """

        if not self.encoding:
            return None

        try:
            decoded = pickle.loads(self.encoding)
        except (
            pickle.PickleError,
            EOFError,
            AttributeError,
            ValueError,
            TypeError,
        ) as exc:
            raise ValidationError(
                _("Unable to decode legacy face encoding.")
            ) from exc

        return np.asarray(decoded, dtype=np.float32)

    # ==================================================================
    # MIGRATION HELPERS
    # ==================================================================

    def populate_embedding_from_legacy(self):
        """
        Populate the canonical pgvector embedding from the legacy field.

        Does NOT save. Intended for a controlled data migration.
        """

        if self.embedding is not None:
            return self.embedding

        legacy = self.get_decoded_encoding()
        if legacy is None:
            raise ValidationError(
                _("No legacy encoding is available for migration.")
            )

        self.embedding = self.normalize_embedding(legacy)
        return self.embedding

    # ==================================================================
    # LIFECYCLE
    # ==================================================================

    def activate(self):
        """
        Activate this encoding, deactivating the user's other encodings.
        """

        if self.embedding is None:
            self.populate_embedding_from_legacy()

        # Full validation before touching state.
        self.full_clean()

        type(self).objects.filter(
            user=self.user,
            is_active=True,
        ).exclude(pk=self.pk).update(is_active=False)

        self.is_active = True

        # State-only update — save() skips full_clean on this path,
        # which is safe because we validated above.
        self.save(
            update_fields=["embedding", "is_active", "updated_at"],
        )

    def deactivate(self):
        """Deactivate this encoding."""

        if not self.is_active:
            return

        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])