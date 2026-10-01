# apps/backend/biometrics/services/liveness.py

"""
Biometric liveness service.

This module owns liveness-related business logic for the biometrics domain.

Architecture
------------

GraphQL / API
      |
      v
biometrics.services.liveness
      |
      v
liveness provider / computer-vision implementation

Liveness and face identity matching are deliberately separate:

    Liveness
        "Is this a live person rather than a presentation attack?"

    Face matching
        "Does this face correspond to the enrolled biometric?"

This service must not:

- issue JWTs
- authenticate Django users
- access GraphQL
- raise GraphQLError
- perform database queries for authentication
- contain GraphQL mutation logic
- fabricate successful liveness results

A dedicated liveness/anti-spoofing provider can be connected through
`assess_liveness()` later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ============================================================================
# EXCEPTIONS
# ============================================================================


class LivenessError(Exception):
    """Base exception for liveness-related failures."""


class InvalidLivenessInput(LivenessError):
    """Raised when liveness input or configuration is invalid."""


class LivenessDetectionFailed(LivenessError):
    """Raised when liveness could not be determined."""


class LivenessRejected(LivenessError):
    """Raised when the liveness score does not meet the threshold."""


# ============================================================================
# RESULT
# ============================================================================


@dataclass(frozen=True, slots=True)
class LivenessResult:
    """
    Immutable result of a liveness evaluation.

    Attributes:
        is_live:
            Whether the subject passed the liveness check.

        score:
            Liveness score normalized to the range 0..1.

        threshold:
            Minimum score required to pass.

        method:
            Provider or algorithm used to produce the score.

        metadata:
            Provider-specific diagnostic information.
    """

    is_live: bool
    score: float
    threshold: float
    method: str
    metadata: dict[str, Any]


# ============================================================================
# VALIDATION
# ============================================================================


def validate_liveness_score(score: float) -> float:
    """
    Validate and normalize a liveness score.

    Args:
        score:
            Numeric value between 0 and 1. Strings containing a valid
            numeric literal are accepted and coerced.

    Returns:
        float:
            Normalized score.

    Raises:
        InvalidLivenessInput:
            If the score is invalid.
    """

    try:
        value = float(score)
    except (TypeError, ValueError) as exc:
        raise InvalidLivenessInput(
            "Liveness score must be numeric."
        ) from exc

    if not 0.0 <= value <= 1.0:
        raise InvalidLivenessInput(
            "Liveness score must be between 0 and 1."
        )

    return value


def validate_liveness_threshold(threshold: float) -> float:
    """
    Validate a liveness decision threshold.

    Args:
        threshold:
            Numeric value between 0 and 1. Strings containing a valid
            numeric literal are accepted and coerced.

    Returns:
        float:
            Normalized threshold.

    Raises:
        InvalidLivenessInput:
            If the threshold is invalid.
    """

    try:
        value = float(threshold)
    except (TypeError, ValueError) as exc:
        raise InvalidLivenessInput(
            "Liveness threshold must be numeric."
        ) from exc

    if not 0.0 <= value <= 1.0:
        raise InvalidLivenessInput(
            "Liveness threshold must be between 0 and 1."
        )

    return value


# ============================================================================
# EVALUATION
# ============================================================================


def evaluate_liveness(
    score: float,
    threshold: float = 0.8,
    *,
    method: str = "configured",
    metadata: dict[str, Any] | None = None,
) -> LivenessResult:
    """
    Evaluate an already-computed liveness score.

    This function performs the domain decision only.

    It does not perform computer vision.

    A liveness provider is responsible for calculating the score. This
    service determines whether that score satisfies the configured
    security threshold.

    Args:
        score:
            Liveness score between 0 and 1.

        threshold:
            Minimum score required to pass.

        method:
            Name of the provider/algorithm.

        metadata:
            Optional provider metadata.

    Returns:
        LivenessResult

    Raises:
        InvalidLivenessInput:
            If score or threshold are not numeric or out of range.
    """

    normalized_score = validate_liveness_score(score)
    normalized_threshold = validate_liveness_threshold(threshold)

    return LivenessResult(
        is_live=normalized_score >= normalized_threshold,
        score=normalized_score,
        threshold=normalized_threshold,
        method=method,
        metadata=dict(metadata or {}),
    )


# ============================================================================
# REQUIREMENT
# ============================================================================


def require_live(
    score: float,
    threshold: float = 0.8,
    *,
    method: str = "configured",
    metadata: dict[str, Any] | None = None,
) -> LivenessResult:
    """
    Evaluate liveness and reject failed evaluations.

    This is useful for security-sensitive flows where execution must stop
    immediately when liveness fails.

    Args:
        score:
            Liveness score between 0 and 1.

        threshold:
            Minimum score required to pass.

        method:
            Name of the provider/algorithm.

        metadata:
            Optional provider metadata.

    Returns:
        LivenessResult

    Raises:
        InvalidLivenessInput:
            If score or threshold are invalid.

        LivenessRejected:
            If the liveness score is below the configured threshold.
    """

    result = evaluate_liveness(
        score=score,
        threshold=threshold,
        method=method,
        metadata=metadata,
    )

    if not result.is_live:
        raise LivenessRejected(
            "Liveness verification failed."
        )

    return result


# ============================================================================
# PROVIDER ADAPTER
# ============================================================================


def assess_liveness(
    *,
    image_path: str | None = None,
    frames: list[str] | None = None,
    threshold: float = 0.8,
) -> LivenessResult:
    """
    Assess liveness using the configured biometric provider.

    This function is the provider boundary.

    Important:
        ArcFace face detection/embedding is NOT itself a liveness
        detector. A detected face can still be a photograph, screen
        replay, printed image, or other presentation attack.

    Therefore this function deliberately refuses to fabricate a
    liveness score until an actual liveness provider is configured.

    Args:
        image_path:
            Optional path to a liveness image.

        frames:
            Optional sequence of captured frame paths.

        threshold:
            Minimum liveness score required.

    Returns:
        LivenessResult

    Raises:
        InvalidLivenessInput:
            If neither an image nor frames are supplied.

        LivenessDetectionFailed:
            If no liveness provider is configured.
    """

    if not image_path and not frames:
        raise InvalidLivenessInput(
            "A liveness image or frame sequence is required."
        )

    if frames is not None and not isinstance(frames, list):
        raise InvalidLivenessInput(
            "Liveness frames must be provided as a list."
        )

    validate_liveness_threshold(threshold)

    # ------------------------------------------------------------------
    # Provider boundary
    # ------------------------------------------------------------------
    #
    # A real implementation should be connected here or through a
    # dedicated provider module, for example:
    #
    #     biometrics.providers.liveness
    #
    # Possible implementations include:
    #
    #     - active challenge/response
    #     - blink detection
    #     - head movement
    #     - depth information
    #     - anti-spoofing model
    #     - camera/device-native liveness
    #
    # We intentionally do NOT return a fabricated score.
    #

    raise LivenessDetectionFailed(
        "No liveness provider is configured."
    )


# ============================================================================
# PUBLIC API
# ============================================================================


__all__ = [
    "LivenessError",
    "InvalidLivenessInput",
    "LivenessDetectionFailed",
    "LivenessRejected",
    "LivenessResult",
    "validate_liveness_score",
    "validate_liveness_threshold",
    "evaluate_liveness",
    "require_live",
    "assess_liveness",
]