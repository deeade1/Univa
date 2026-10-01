# apps/backend/biometrics/services/verification.py

"""
Biometric verification service.

Architecture
------------

GraphQL
    │
    ▼
biometrics.services.verification
    │
    ├── verification state
    ├── verification policy
    ├── biometric matching
    ├── liveness policy
    └── verification lifecycle
    │
    ▼
biometrics.models
    └── FaceVerification

This module is the canonical application-service boundary for face
verification.

It deliberately does NOT:

- issue JWTs
- authenticate Django passwords
- create magic-login tokens
- contain GraphQL code
- execute raw SQL
- implement pgvector queries directly
- import UserProfile

Those responsibilities belong to their respective domains/services.

The matching service owns embedding similarity.
The liveness service owns liveness evaluation.
This service coordinates them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np
from django.db import transaction
from django.utils import timezone

from biometrics.models import FaceVerification
from biometrics.models.encoding import FaceEncoding
from biometrics.services.liveness import (
    LivenessResult,
    evaluate_liveness,
)
from biometrics.services.matching import (
    FaceMatchResult,
    match_face,
)


# ============================================================================
# RESULT
# ============================================================================


@dataclass(frozen=True)
class VerificationResult:
    """
    Result of a biometric verification operation.

    This is deliberately independent of GraphQL.

    GraphQL mutations may convert this result into GraphQL fields,
    but the service layer should remain transport-independent.
    """

    verified: bool

    confidence: float = 0.0

    threshold: float = 0.0

    message: str = ""

    method: str = "face"

    channel: str = "photo"

    user_id: Optional[int] = None

    match: Optional[FaceMatchResult] = None

    liveness: Optional[LivenessResult] = None

    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# VERIFICATION RECORD
# ============================================================================


def get_face_verification(user) -> Optional[FaceVerification]:
    """
    Return the user's FaceVerification record if one exists.

    No record means biometric verification has not yet been configured.
    """

    try:
        return user.face_verification
    except FaceVerification.DoesNotExist:
        return None


def get_or_create_face_verification(
    user,
    *,
    verification_method: Optional[str] = None,
    verification_channel: Optional[str] = None,
) -> tuple[FaceVerification, bool]:
    """
    Return the user's verification record, creating it when necessary.

    This is the canonical persistence boundary for FaceVerification.
    """

    defaults: dict[str, Any] = {}

    if verification_method is not None:
        defaults["verification_method"] = verification_method

    if verification_channel is not None:
        defaults["verification_channel"] = verification_channel

    return FaceVerification.objects.get_or_create(
        user=user,
        defaults=defaults,
    )


# ============================================================================
# VERIFICATION STATE
# ============================================================================


def requires_face_verification(user) -> bool:
    """
    Determine whether the user currently requires face verification.

    A missing verification record means verification is required.
    """

    verification = get_face_verification(user)

    if verification is None:
        return True

    return not verification.is_verified


def is_face_verified(user) -> bool:
    """
    Return True when the user's biometric verification state is verified.
    """

    verification = get_face_verification(user)

    return bool(
        verification
        and verification.is_verified
    )


def get_verification_method(user) -> Optional[str]:
    """
    Return the configured biometric verification method.
    """

    verification = get_face_verification(user)

    if verification is None:
        return None

    return verification.verification_method


def get_verification_channel(user) -> Optional[str]:
    """
    Return the configured biometric verification channel.

    Kept as a first-class service API because callers should not need to
    access FaceVerification model fields directly.
    """

    verification = get_face_verification(user)

    if verification is None:
        return None

    return verification.verification_channel


# ============================================================================
# LOCKOUT
# ============================================================================


def check_verification_lock(
    verification: FaceVerification,
) -> None:
    """
    Raise ValueError if biometric verification is currently locked.

    The model owns the lockout state and policy.
    """

    verification.check_lockout()


def record_failed_verification(
    verification: FaceVerification,
) -> FaceVerification:
    """
    Record a failed biometric verification attempt.

    Emits a security alert when the account locks out for the first
    time. Subsequent failures while already locked do not re-emit.
    """

    was_locked = verification.is_locked()

    verification.increment_attempts()

    is_now_locked = verification.is_locked()

    if not was_locked and is_now_locked:
        verification.trigger_alert()

    return verification


def record_successful_verification(
    verification: FaceVerification,
) -> FaceVerification:
    """
    Record a successful biometric verification.

    Successful verification:

    - marks the verification record as verified
    - updates last_verified_at
    - clears failed-attempt state
    """

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
        ]
    )

    return verification


def invalidate_face_verification(
    user,
) -> Optional[FaceVerification]:
    """
    Mark the user's biometric verification state as unverified.

    This does not delete face encodings.

    Existing encodings remain owned by the enrollment domain and may be
    explicitly revoked there when required.
    """

    verification = get_face_verification(user)

    if verification is None:
        return None

    verification.is_verified = False
    verification.last_verified_at = None

    verification.save(
        update_fields=[
            "is_verified",
            "last_verified_at",
        ]
    )

    return verification


# ============================================================================
# POLICY
# ============================================================================


def get_confidence_threshold(
    user,
    default: float = 0.6,
) -> float:
    """
    Return the user's configured biometric confidence threshold.
    """

    verification = get_face_verification(user)

    if verification is None:
        return default

    return float(
        verification.confidence_threshold
    )


def get_liveness_threshold(
    user,
    default: float = 0.8,
) -> float:
    """
    Return the user's configured liveness threshold.
    """

    verification = get_face_verification(user)

    if verification is None:
        return default

    return float(
        verification.liveness_threshold
    )


# ============================================================================
# INTERNAL HELPERS
# ============================================================================


def _match_user_face(
    user,
    probe_embedding: Sequence[float] | np.ndarray,
    *,
    threshold: float,
) -> FaceMatchResult:
    """
    Match a probe embedding against a specific user's active encodings.

    This is the ordinary authentication path. It does NOT do cross-user
    identification — only the encodings owned by ``user`` are considered.
    """

    active_encodings = FaceEncoding.objects.filter(
        user=user,
        is_active=True,
    )

    if not active_encodings.exists():
        return FaceMatchResult(
            matched=False,
            distance=1.0,
            similarity=0.0,
            encoding=None,
            user_id=user.pk,
            threshold=threshold,
        )

    try:
        return match_face(
            probe_embedding,
            threshold=threshold,
            user=user,
        )
    except TypeError:
        return _manual_match(
            probe_embedding,
            active_encodings,
            threshold=threshold,
            user_id=user.pk,
        )


def _manual_match(
    probe_embedding: Sequence[float] | np.ndarray,
    encodings,
    *,
    threshold: float,
    user_id: Optional[int] = None,
) -> FaceMatchResult:
    """
    Fallback matcher used when matching.match_face() has no user filter.

    Computes cosine similarity between the probe and every active
    encoding in the provided queryset, returning the best match.
    """

    probe = np.asarray(probe_embedding, dtype=np.float32)
    probe_norm = np.linalg.norm(probe)

    if probe_norm == 0:
        return FaceMatchResult(
            matched=False,
            distance=1.0,
            similarity=0.0,
            encoding=None,
            user_id=user_id,
            threshold=threshold,
        )

    best_encoding = None
    best_similarity = -1.0

    for encoding in encodings:
        stored = encoding.embedding
        if stored is None:
            continue
        stored_vec = np.asarray(stored, dtype=np.float32)
        stored_norm = np.linalg.norm(stored_vec)
        if stored_norm == 0:
            continue
        similarity = float(
            np.dot(probe, stored_vec) / (probe_norm * stored_norm)
        )
        if similarity > best_similarity:
            best_similarity = similarity
            best_encoding = encoding

    if best_encoding is None:
        return FaceMatchResult(
            matched=False,
            distance=1.0,
            similarity=0.0,
            encoding=None,
            user_id=user_id,
            threshold=threshold,
        )

    distance = 1.0 - best_similarity
    matched = best_similarity >= threshold

    return FaceMatchResult(
        matched=matched,
        distance=distance,
        similarity=best_similarity,
        encoding=best_encoding,
        user_id=user_id,
        threshold=threshold,
    )


# ============================================================================
# FACE VERIFICATION
# ============================================================================


@transaction.atomic
def verify_face(
    user,
    probe_embedding,
    *,
    liveness_score: Optional[float] = None,
    channel: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> VerificationResult:
    """
    Verify a face embedding against the user's active face encodings.
    """

    verification, _ = get_or_create_face_verification(
        user,
        verification_channel=channel,
    )

    check_verification_lock(verification)

    threshold = get_confidence_threshold(user)

    # ------------------------------------------------------------------
    # Liveness
    # ------------------------------------------------------------------

    liveness_result = None

    if liveness_score is not None:
        liveness_result = evaluate_liveness(
            liveness_score,
            get_liveness_threshold(user),
        )

        if not liveness_result.is_live:
            raise ValueError(
                "Liveness verification failed."
            )

    # ------------------------------------------------------------------
    # Face matching
    # ------------------------------------------------------------------

    match_result = _match_user_face(
        user,
        probe_embedding,
        threshold=threshold,
    )

    if not match_result.matched:
        record_failed_verification(
            verification,
        )

        return VerificationResult(
            verified=False,
            confidence=float(match_result.similarity),
            threshold=float(match_result.threshold),
            message="Face verification failed.",
            method=verification.verification_method,
            channel=(
                channel
                or verification.verification_channel
            ),
            user_id=user.pk,
            match=match_result,
            liveness=liveness_result,
            metadata=metadata or {},
        )

    # ------------------------------------------------------------------
    # Successful verification
    # ------------------------------------------------------------------

    record_successful_verification(
        verification,
    )

    return VerificationResult(
        verified=True,
        confidence=float(match_result.similarity),
        threshold=float(match_result.threshold),
        message="Face verification successful.",
        method=verification.verification_method,
        channel=(
            channel
            or verification.verification_channel
        ),
        user_id=user.pk,
        match=match_result,
        liveness=liveness_result,
        metadata=metadata or {},
    )


def verify_biometric(
    user,
    probe_embedding,
    *,
    liveness_score=None,
    channel=None,
    metadata=None,
):
    """
    Public biometric verification API.
    """

    return verify_face(
        user=user,
        probe_embedding=probe_embedding,
        liveness_score=liveness_score,
        channel=channel,
        metadata=metadata,
    )


# ============================================================================
# EXISTING VERIFICATION STATE
# ============================================================================


def require_verified_user(user) -> FaceVerification:
    """
    Require the user to already have verified biometric state.
    """

    verification = get_face_verification(user)

    if verification is None:
        raise ValueError(
            "Face verification required."
        )

    verification.check_lockout()

    if not verification.is_verified:
        raise ValueError(
            "Face verification required."
        )

    return verification


# ============================================================================
# LIVENESS-ONLY HELPER
# ============================================================================


def verify_liveness(
    user,
    score: float,
) -> LivenessResult:
    """
    Evaluate liveness using the user's configured threshold.

    This function does not modify FaceVerification state.
    """

    threshold = get_liveness_threshold(
        user,
    )

    result = evaluate_liveness(
        score,
        threshold,
    )

    return result