# apps/backend/biometrics/services/__init__.py

from .enrollment import enroll_face
from .verification import (
    get_face_verification,
    get_verification_channel,
    get_verification_method,
    is_face_verified,
    requires_face_verification,
)

__all__ = [
    "enroll_face",
    "get_face_verification",
    "get_verification_channel",
    "get_verification_method",
    "is_face_verified",
    "requires_face_verification",
]