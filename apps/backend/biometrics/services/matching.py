# apps/backend/biometrics/services/matching.py

"""
Face matching service.

Architecture
------------

GraphQL / API
      │
      ▼
biometrics.services.matching
      │
      ├── FaceEncoding
      ├── pgvector
      │     └── CosineDistance
      │
      └── Face matching result

This module owns biometric vector matching.

Responsibilities
----------------

- Validate probe embeddings.
- Query active FaceEncoding records.
- Calculate cosine distance using pgvector.
- Convert distance into similarity.
- Apply biometric thresholds.
- Match a probe against one user's registered faces.
- Match a probe against multiple users.
- Return structured matching results.

This module deliberately does NOT:

- issue JWTs
- authenticate users
- mutate GraphQL state
- access request objects
- execute raw SQL
- handle uploaded files
- perform face detection
- generate embeddings
- send notifications

Embedding generation belongs to:

    biometrics.processing.face

Persistence/enrollment belongs to:

    biometrics.services.enrollment

Authentication/verification orchestration belongs to:

    biometrics.services.verification
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from pgvector.django import CosineDistance

from biometrics.models import FaceEncoding


# ============================================================================
# CONSTANTS
# ============================================================================

EMBEDDING_DIMENSIONS = 512

# ArcFace embeddings are compared using cosine distance.
#
# IMPORTANT:
#     cosine distance = 1 - cosine similarity
#
# Therefore:
#
#     distance 0.0  -> identical vectors
#     distance 1.0  -> orthogonal vectors
#     distance 2.0  -> opposite vectors
#
# The threshold should remain configurable at the service boundary rather
# than being duplicated throughout GraphQL mutations.
DEFAULT_COSINE_DISTANCE_THRESHOLD = 0.40

DEFAULT_SIMILARITY_THRESHOLD = (
    1.0 - DEFAULT_COSINE_DISTANCE_THRESHOLD
)


# ============================================================================
# RESULT TYPES
# ============================================================================


@dataclass(frozen=True)
class FaceMatchResult:
    """
    Result of a face-vector comparison.

    Attributes
    ----------
    matched:
        Whether the face passed the configured threshold.

    distance:
        pgvector cosine distance.

    similarity:
        Converted cosine similarity.

    encoding:
        The FaceEncoding record that produced the best match.

    user_id:
        User owning the matched encoding.

    threshold:
        Maximum allowed cosine distance.
    """

    matched: bool
    distance: float
    similarity: float
    encoding: FaceEncoding | None
    user_id: int | None
    threshold: float

    @property
    def encoding_id(self) -> int | None:
        """
        Return the matched encoding primary key.
        """
        if self.encoding is None:
            return None

        return self.encoding.pk


# ============================================================================
# EMBEDDING VALIDATION
# ============================================================================


def validate_embedding(
    embedding: Sequence[float] | np.ndarray,
) -> list[float]:
    """
    Validate and normalize a face embedding.

    ArcFace embeddings used by this application must contain exactly
    512 floating-point dimensions.

    Parameters
    ----------
    embedding:
        List, tuple, NumPy array, or other numeric sequence.

    Returns
    -------
    list[float]
        A normalized Python list suitable for pgvector.

    Raises
    ------
    ValidationError
        If the embedding is invalid.
    """

    if embedding is None:
        raise ValidationError(
            "Face embedding is required."
        )

    try:
        array = np.asarray(
            embedding,
            dtype=np.float32,
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Face embedding contains invalid values."
        ) from exc

    if array.ndim != 1:
        raise ValidationError(
            "Face embedding must be a one-dimensional vector."
        )

    if array.shape[0] != EMBEDDING_DIMENSIONS:
        raise ValidationError(
            (
                "Face embedding must contain "
                f"{EMBEDDING_DIMENSIONS} dimensions; "
                f"received {array.shape[0]}."
            )
        )

    if not np.all(np.isfinite(array)):
        raise ValidationError(
            "Face embedding contains non-finite values."
        )

    return array.astype(
        np.float32,
        copy=False,
    ).tolist()


# ============================================================================
# THRESHOLD VALIDATION
# ============================================================================


def validate_distance_threshold(
    threshold: float,
) -> float:
    """
    Validate a cosine-distance threshold.

    Cosine distance is normally in the range [0, 2].

    A smaller threshold means stricter matching.
    """

    try:
        value = float(threshold)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Face matching threshold must be numeric."
        ) from exc

    if not 0.0 <= value <= 2.0:
        raise ValidationError(
            "Face matching threshold must be between 0 and 2."
        )

    return value


# ============================================================================
# DISTANCE / SIMILARITY
# ============================================================================


def distance_to_similarity(
    distance: float,
) -> float:
    """
    Convert cosine distance to cosine similarity.

    pgvector:

        cosine distance = 1 - cosine similarity

    Therefore:

        similarity = 1 - distance

    The result is clamped to [-1, 1] defensively.
    """

    value = 1.0 - float(distance)

    return max(
        -1.0,
        min(1.0, value),
    )


def similarity_to_distance(
    similarity: float,
) -> float:
    """
    Convert cosine similarity into cosine distance.
    """

    try:
        value = float(similarity)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Similarity must be numeric."
        ) from exc

    if not -1.0 <= value <= 1.0:
        raise ValidationError(
            "Cosine similarity must be between -1 and 1."
        )

    return 1.0 - value


# ============================================================================
# QUERYSET
# ============================================================================


def get_active_encodings(
    user=None,
) -> QuerySet[FaceEncoding]:
    """
    Return active face encodings.

    If ``user`` is supplied, only encodings belonging to that user
    are returned.

    No biometric mutation occurs here.
    """

    queryset = FaceEncoding.objects.filter(
        is_active=True,
        embedding__isnull=False,
    )

    if user is not None:
        queryset = queryset.filter(
            user=user,
        )

    return queryset


# ============================================================================
# BEST MATCH
# ============================================================================


def get_best_match(
    embedding: Sequence[float] | np.ndarray,
    *,
    user=None,
    threshold: float = DEFAULT_COSINE_DISTANCE_THRESHOLD,
) -> FaceMatchResult:
    """
    Find the closest registered face encoding.

    Parameters
    ----------
    embedding:
        Probe ArcFace embedding.

    user:
        Optional Django User instance.

        If supplied, matching is restricted to that user.

        If omitted, the entire active biometric encoding collection
        is searched.

    threshold:
        Maximum accepted cosine distance.

    Returns
    -------
    FaceMatchResult

    Notes
    -----
    The actual nearest-neighbor calculation is delegated to pgvector
    through Django's ``CosineDistance`` expression.

    No raw SQL is used.
    """

    normalized_embedding = validate_embedding(
        embedding,
    )

    threshold = validate_distance_threshold(
        threshold,
    )

    queryset = get_active_encodings(
        user=user,
    )

    if not queryset.exists():
        return FaceMatchResult(
            matched=False,
            distance=float("inf"),
            similarity=-1.0,
            encoding=None,
            user_id=getattr(user, "pk", None),
            threshold=threshold,
        )

    queryset = queryset.annotate(
        distance=CosineDistance(
            "embedding",
            normalized_embedding,
        ),
    ).order_by(
        "distance",
    )

    encoding = queryset.first()

    if encoding is None:
        return FaceMatchResult(
            matched=False,
            distance=float("inf"),
            similarity=-1.0,
            encoding=None,
            user_id=getattr(user, "pk", None),
            threshold=threshold,
        )

    distance = float(
        encoding.distance,
    )

    similarity = distance_to_similarity(
        distance,
    )

    matched = distance <= threshold

    return FaceMatchResult(
        matched=matched,
        distance=distance,
        similarity=similarity,
        encoding=encoding,
        user_id=getattr(
            encoding,
            "user_id",
            getattr(user, "pk", None),
        ),
        threshold=threshold,
    )


# ============================================================================
# USER-SPECIFIC MATCHING
# ============================================================================


def match_user_face(
    user,
    embedding: Sequence[float] | np.ndarray,
    *,
    threshold: float = DEFAULT_COSINE_DISTANCE_THRESHOLD,
) -> FaceMatchResult:
    """
    Match a probe face against a specific user's active face encodings.

    This is the primary service used by authentication flows such as:

    - password + face authentication
    - magic-link + face verification
    - explicit face verification
    """

    if user is None:
        raise ValidationError(
            "A user is required for face matching."
        )

    return get_best_match(
        embedding,
        user=user,
        threshold=threshold,
    )


# ============================================================================
# GLOBAL MATCHING
# ============================================================================


def match_face(
    embedding: Sequence[float] | np.ndarray,
    *,
    threshold: float = DEFAULT_COSINE_DISTANCE_THRESHOLD,
) -> FaceMatchResult:
    """
    Match a probe face against all active registered faces.

    The closest active FaceEncoding is returned.

    This should only be exposed to workflows that are authorized to
    perform cross-user biometric identification.

    Ordinary authentication should normally use ``match_user_face``.
    """

    return get_best_match(
        embedding,
        threshold=threshold,
    )


# ============================================================================
# BOOLEAN HELPERS
# ============================================================================


def is_face_match(
    embedding: Sequence[float] | np.ndarray,
    *,
    user=None,
    threshold: float = DEFAULT_COSINE_DISTANCE_THRESHOLD,
) -> bool:
    """
    Return only whether the supplied face matches.

    This is useful when callers do not need the complete match result.
    """

    result = get_best_match(
        embedding,
        user=user,
        threshold=threshold,
    )

    return result.matched


# ============================================================================
# SIMILARITY HELPERS
# ============================================================================


def calculate_face_similarity(
    embedding_a: Sequence[float] | np.ndarray,
    embedding_b: Sequence[float] | np.ndarray,
) -> float:
    """
    Calculate cosine similarity between two embeddings.

    This function is intentionally implemented in Python rather than
    through a database query because both embeddings already exist in
    memory.

    Database-backed nearest-neighbor searches should use ``CosineDistance``.
    """

    vector_a = np.asarray(
        validate_embedding(embedding_a),
        dtype=np.float32,
    )

    vector_b = np.asarray(
        validate_embedding(embedding_b),
        dtype=np.float32,
    )

    norm_a = np.linalg.norm(
        vector_a,
    )

    norm_b = np.linalg.norm(
        vector_b,
    )

    if norm_a == 0.0 or norm_b == 0.0:
        raise ValidationError(
            "Face embedding cannot be a zero vector."
        )

    similarity = float(
        np.dot(vector_a, vector_b)
        / (norm_a * norm_b)
    )

    return max(
        -1.0,
        min(1.0, similarity),
    )


def calculate_face_distance(
    embedding_a: Sequence[float] | np.ndarray,
    embedding_b: Sequence[float] | np.ndarray,
) -> float:
    """
    Calculate cosine distance between two in-memory embeddings.
    """

    similarity = calculate_face_similarity(
        embedding_a,
        embedding_b,
    )

    return similarity_to_distance(
        similarity,
    )


# ============================================================================
# BATCH MATCHING
# ============================================================================


def get_top_matches(
    embedding: Sequence[float] | np.ndarray,
    *,
    limit: int = 5,
    threshold: float | None = None,
) -> QuerySet[FaceEncoding]:
    """
    Return the nearest active face encodings.

    Parameters
    ----------
    embedding:
        Probe embedding.

    limit:
        Maximum number of results.

    threshold:
        Optional maximum cosine distance.

    Returns
    -------
    QuerySet
        QuerySet annotated with ``distance`` and ``similarity`` fields.

    Notes
    -----
    ``similarity`` is intentionally not calculated as a database annotation
    here. ``distance`` is the native pgvector operation and is the value
    needed for ordering/index-assisted nearest-neighbor queries.
    """

    normalized_embedding = validate_embedding(
        embedding,
    )

    if not isinstance(limit, int) or limit <= 0:
        raise ValidationError(
            "Match limit must be a positive integer."
        )

    if threshold is not None:
        threshold = validate_distance_threshold(
            threshold,
        )

    queryset = get_active_encodings().annotate(
        distance=CosineDistance(
            "embedding",
            normalized_embedding,
        ),
    )

    if threshold is not None:
        queryset = queryset.filter(
            distance__lte=threshold,
        )

    return queryset.order_by(
        "distance",
    )[:limit]


# ============================================================================
# RESULT SERIALIZATION
# ============================================================================


def serialize_match_result(
    result: FaceMatchResult,
) -> dict:
    """
    Convert a FaceMatchResult into a plain dictionary.

    Useful at API/service boundaries where a dataclass should not leak
    into GraphQL or other transport layers.
    """

    return {
        "matched": result.matched,
        "distance": result.distance,
        "similarity": result.similarity,
        "encoding_id": result.encoding_id,
        "user_id": result.user_id,
        "threshold": result.threshold,
    }