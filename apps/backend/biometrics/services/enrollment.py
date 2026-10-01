# apps/backend/biometrics/services/enrollment.py

"""
Biometric face-enrollment service.

Architecture
------------

GraphQL / API
      │
      ▼
biometrics.services.enrollment
      │
      ├── FaceVerificationImage
      ├── FaceEncoding
      └── FaceVerification
             │
             └── database state

Embedding generation belongs to:

    biometrics.processing.face

Vector matching belongs to:

    biometrics.services.matching

Authentication belongs to:

    accounts / authentication services

This module owns the persistence lifecycle of a user's enrolled face.
"""

from __future__ import annotations

import os
from typing import Any, Sequence

import numpy as np

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from biometrics.models import (
    FaceEncoding,
    FaceVerification,
    FaceVerificationImage,
)
from biometrics.services.matching import (
    EMBEDDING_DIMENSIONS,
    validate_embedding,
)


# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_FACE_VERSION = "v1"


# ============================================================================
# VALIDATION
# ============================================================================


def validate_embedding_for_enrollment(
    embedding: Sequence[float] | np.ndarray,
) -> list[float]:
    """
    Validate an ArcFace embedding before persistence.

    The canonical application embedding size is 512 dimensions.
    """

    normalized = validate_embedding(
        embedding,
    )

    if len(normalized) != EMBEDDING_DIMENSIONS:
        raise ValidationError(
            (
                "Invalid face embedding dimensions. "
                f"Expected {EMBEDDING_DIMENSIONS}, "
                f"received {len(normalized)}."
            )
        )

    return normalized


def validate_enrollment_image(
    uploaded_file,
    *,
    max_size: int = 10 * 1024 * 1024,
) -> None:
    """
    Validate an uploaded face-enrollment image.

    File-content validation should still be performed by the image
    processing layer. This function handles the basic transport-level
    checks required before persistence.
    """

    if uploaded_file is None:
        raise ValidationError(
            "Face image is required."
        )

    size = getattr(
        uploaded_file,
        "size",
        None,
    )

    if size is not None and size > max_size:
        raise ValidationError(
            "Face image is too large. Maximum size is 10MB."
        )

    content_type = getattr(
        uploaded_file,
        "content_type",
        None,
    )

    allowed_types = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    }

    if content_type and content_type.lower() not in allowed_types:
        raise ValidationError(
            "Unsupported face image format."
        )


# ============================================================================
# FACE VERIFICATION RECORD
# ============================================================================


def get_or_create_face_verification(
    user,
) -> tuple[FaceVerification, bool]:
    """
    Return the user's FaceVerification record.

    A user has at most one FaceVerification record because the model
    uses a OneToOneField.
    """

    if user is None:
        raise ValidationError(
            "A user is required."
        )

    return FaceVerification.objects.get_or_create(
        user=user,
    )


# ============================================================================
# IMAGE PERSISTENCE
# ============================================================================


@transaction.atomic
def create_face_verification_image(
    user,
    uploaded_file,
    *,
    metadata: dict[str, Any] | None = None,
) -> FaceVerificationImage:
    """
    Persist a face-verification image.

    The image is initially marked as unverified because biometric
    processing has not necessarily completed yet.
    """

    if user is None:
        raise ValidationError(
            "A user is required."
        )

    validate_enrollment_image(
        uploaded_file,
    )

    return FaceVerificationImage.objects.create(
        user=user,
        image=uploaded_file,
        is_verified=False,
        face_detected=False,
        face_count=0,
        metadata=metadata or {},
    )


# ============================================================================
# ENCODING PERSISTENCE
# ============================================================================


def deactivate_active_encodings(
    user,
    *,
    exclude_id: int | None = None,
) -> int:
    """
    Deactivate all active face encodings belonging to a user.

    This is used when a newly enrolled face becomes the user's
    primary face encoding.
    """

    if user is None:
        raise ValidationError(
            "A user is required."
        )

    queryset = FaceEncoding.objects.filter(
        user=user,
        is_active=True,
    )

    if exclude_id is not None:
        queryset = queryset.exclude(
            pk=exclude_id,
        )

    
    updated = queryset.update(
        is_active=False,
    )
    return updated


@transaction.atomic
def create_face_encoding(
    user,
    embedding: Sequence[float] | np.ndarray,
    *,
    source_image: FaceVerificationImage | None = None,
    is_primary: bool = True,
    version: str = DEFAULT_FACE_VERSION,
    metadata: dict[str, Any] | None = None,
) -> FaceEncoding:
    """
    Persist a canonical face encoding.

    The pgvector ``embedding`` field is the canonical representation.

    The legacy binary ``encoding`` field is populated by
    ``FaceEncoding.create_from_embedding()`` for backward compatibility.

    Parameters
    ----------
    user:
        Django User owning the biometric encoding.

    embedding:
        512-dimensional ArcFace embedding.

    source_image:
        Optional FaceVerificationImage associated with the encoding.

    is_primary:
        Whether this encoding should become the user's active encoding.

    version:
        Embedding/model version.

    metadata:
        Additional non-sensitive processing metadata.
    """

    if user is None:
        raise ValidationError(
            "A user is required."
        )

    normalized_embedding = validate_embedding_for_enrollment(
        embedding,
    )

    if source_image is not None:
        if source_image.user_id != user.pk:
            raise ValidationError(
                "Source image does not belong to this user."
            )

    encoding = FaceEncoding.create_from_embedding(
        user=user,
        embedding=normalized_embedding,
        source_image=source_image,
        version=version,
        is_active=is_primary,
        metadata=metadata or {},
    )

    if is_primary:
        deactivate_active_encodings(
            user,
            exclude_id=encoding.pk,
        )

    return encoding


# ============================================================================
# COMPLETE ENROLLMENT
# ============================================================================


@transaction.atomic
def enroll_face(
    user,
    embedding: Sequence[float] | np.ndarray,
    *,
    source_image: FaceVerificationImage | None = None,
    is_primary: bool = True,
    version: str = DEFAULT_FACE_VERSION,
    metadata: dict[str, Any] | None = None,
    verification_channel: str = "photo",
    verification_method: str | None = None,
) -> FaceEncoding:
    """
    Complete synchronous face enrollment.

    This function:

        1. validates the embedding
        2. creates the FaceEncoding
        3. optionally makes it primary
        4. updates FaceVerification
        5. marks the source image as verified

    The operation is atomic.
    """

    if user is None:
        raise ValidationError(
            "A user is required."
        )

    encoding = create_face_encoding(
        user=user,
        embedding=embedding,
        source_image=source_image,
        is_primary=is_primary,
        version=version,
        metadata=metadata,
    )

    verification, _ = get_or_create_face_verification(
        user,
    )

    verification.is_verified = True
    verification.last_verified_at = timezone.now()
    verification.verification_channel = (
        verification_channel
    )

    if verification_method:
        verification.verification_method = (
            verification_method
        )

    verification.verification_attempts = 0
    verification.locked_until = None

    verification.save(
        update_fields=[
            "is_verified",
            "last_verified_at",
            "verification_channel",
            "verification_method",
            "verification_attempts",
            "locked_until",
        ],
    )

    if source_image is not None:
        source_image.is_verified = True
        source_image.face_detected = True
        source_image.face_count = 1

        source_image.save(
            update_fields=[
                "is_verified",
                "face_detected",
                "face_count",
            ],
        )

    return encoding


# ============================================================================
# PENDING ENROLLMENT
# ============================================================================


@transaction.atomic
def create_pending_enrollment(
    user,
    source_image: FaceVerificationImage,
    *,
    is_primary: bool = True,
    version: str = DEFAULT_FACE_VERSION,
    metadata: dict[str, Any] | None = None,
) -> FaceEncoding:
    """
    Create a placeholder FaceEncoding for asynchronous processing.

    The encoding remains inactive until the asynchronous embedding task
    successfully generates and persists a valid vector.

    This prevents GraphQL from needing to know about Celery/task
    implementation details.
    """

    if user is None:
        raise ValidationError(
            "A user is required."
        )

    if source_image is None:
        raise ValidationError(
            "A source image is required."
        )

    if source_image.user_id != user.pk:
        raise ValidationError(
            "Source image does not belong to this user."
        )

    if is_primary:
        deactivate_active_encodings(
            user,
        )

    return FaceEncoding.objects.create(
        user=user,
        encoding=None,
        embedding=None,
        version=version,
        is_active=False,
        source_image=source_image,
        metadata={
            "status": "pending",
            **(metadata or {}),
        },
    )


# ============================================================================
# COMPLETE PENDING ENROLLMENT
# ============================================================================


@transaction.atomic
def complete_pending_enrollment(
    encoding: FaceEncoding,
    embedding: Sequence[float] | np.ndarray,
    *,
    is_primary: bool = True,
    metadata: dict[str, Any] | None = None,
) -> FaceEncoding:
    """
    Complete an existing pending enrollment.

    This is intended for asynchronous workers.

    The worker can:

        1. load the pending FaceEncoding
        2. generate the ArcFace embedding
        3. call this function
        4. let this service finalize persistence
    """

    if encoding is None:
        raise ValidationError(
            "Face encoding is required."
        )

    if encoding.pk is None:
        raise ValidationError(
            "Face encoding must be persisted before completion."
        )

    normalized_embedding = validate_embedding_for_enrollment(
        embedding,
    )

    encoding_array = np.asarray(
        normalized_embedding,
        dtype=np.float32,
    )

    # ------------------------------------------------------------------
    # Maintain legacy binary representation for compatibility.
    # ------------------------------------------------------------------

    import pickle

    encoding.encoding = pickle.dumps(
        encoding_array,
    )

    # ------------------------------------------------------------------
    # Canonical pgvector representation.
    # ------------------------------------------------------------------

    encoding.embedding = normalized_embedding

    encoding.is_active = bool(
        is_primary,
    )

    existing_metadata = (
        encoding.metadata
        if isinstance(encoding.metadata, dict)
        else {}
    )

    existing_metadata.update(
        metadata or {},
    )

    existing_metadata["status"] = "completed"

    encoding.metadata = existing_metadata

    encoding.save(
        update_fields=[
            "encoding",
            "embedding",
            "is_active",
            "metadata",
            "updated_at",
        ],
    )

    if is_primary:
        deactivate_active_encodings(
            encoding.user,
            exclude_id=encoding.pk,
        )

    verification, _ = get_or_create_face_verification(
        encoding.user,
    )

    verification.is_verified = True
    verification.last_verified_at = timezone.now()
    verification.verification_attempts = 0
    verification.locked_until = None

    verification.save(
        update_fields=[
            "is_verified",
            "last_verified_at",
            "verification_attempts",
            "locked_until",
        ],
    )

    if encoding.source_image_id:
        source_image = encoding.source_image

        source_image.is_verified = True
        source_image.face_detected = True
        source_image.face_count = 1

        source_image.save(
            update_fields=[
                "is_verified",
                "face_detected",
                "face_count",
            ],
        )

    return encoding


# ============================================================================
# REVOKE / REMOVE ENROLLMENT
# ============================================================================


@transaction.atomic
def deactivate_face_encoding(
    encoding: FaceEncoding,
) -> FaceEncoding:
    """
    Deactivate a face encoding without deleting biometric history.
    """

    if encoding is None:
        raise ValidationError(
            "Face encoding is required."
        )

    encoding.is_active = False

    metadata = (
        encoding.metadata
        if isinstance(encoding.metadata, dict)
        else {}
    )

    metadata["status"] = "deactivated"

    encoding.metadata = metadata

    encoding.save(
        update_fields=[
            "is_active",
            "metadata",
            "updated_at",
        ],
    )

    return encoding


@transaction.atomic
def deactivate_all_user_encodings(
    user,
) -> int:
    """
    Deactivate every face encoding belonging to a user.

    Existing biometric records are retained for audit/history purposes.
    """

    if user is None:
        raise ValidationError(
            "A user is required."
        )

    updated = FaceEncoding.objects.filter(
        user=user,
        is_active=True,
    ).update(
        is_active=False,
    )

    return updated


# ============================================================================
# VERIFICATION STATE
# ============================================================================


@transaction.atomic
def mark_face_verified(
    user,
    *,
    verification_channel: str | None = None,
    verification_method: str | None = None,
) -> FaceVerification:
    """
    Mark a user's biometric verification state as verified.
    """

    verification, _ = get_or_create_face_verification(
        user,
    )

    verification.is_verified = True
    verification.last_verified_at = timezone.now()
    verification.verification_attempts = 0
    verification.locked_until = None

    update_fields = [
        "is_verified",
        "last_verified_at",
        "verification_attempts",
        "locked_until",
    ]

    if verification_channel is not None:
        verification.verification_channel = (
            verification_channel
        )
        update_fields.append(
            "verification_channel",
        )

    if verification_method is not None:
        verification.verification_method = (
            verification_method
        )
        update_fields.append(
            "verification_method",
        )

    verification.save(
        update_fields=update_fields,
    )

    return verification


@transaction.atomic
def mark_face_unverified(
    user,
) -> FaceVerification:
    """
    Mark a user's face verification state as unverified.

    Existing encodings are not automatically deleted.
    """

    verification, _ = get_or_create_face_verification(
        user,
    )

    verification.is_verified = False

    verification.save(
        update_fields=[
            "is_verified",
        ],
    )

    return verification


# ============================================================================
# CLEANUP
# ============================================================================


def delete_temporary_file(
    path: str | None,
) -> None:
    """
    Safely remove a temporary processing file.

    File cleanup is kept here as a small service utility so callers do not
    duplicate filesystem cleanup logic.
    """

    if not path:
        return

    try:
        if os.path.exists(path):
            os.unlink(path)
    except OSError:
        # Cleanup failure must not hide the original biometric failure.
        pass