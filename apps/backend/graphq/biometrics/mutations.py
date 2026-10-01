# apps/backend/graphq/biometrics/mutations.py

"""
GraphQL mutations for the Biometrics domain.

Architecture
------------

GraphQL is a transport layer only.

The mutation layer is responsible for:

    - authentication / authorization
    - GraphQL input validation
    - resolving Relay global IDs
    - handling uploaded files
    - translating service results into GraphQL results

The mutation layer does NOT own:

    - ArcFace processing
    - pgvector queries
    - face matching
    - enrollment persistence
    - liveness policy
    - biometric verification state
    - JWT construction

Those responsibilities belong to the biometrics and authentication
service layers.

Architecture:

    GraphQL
       │
       ├── enrollment service
       ├── matching service
       ├── liveness service
       └── verification service
                │
                ▼
          biometrics domain
                │
          ┌─────┴─────┐
          ▼           ▼
      processing     models
          │
          ▼
       InsightFace
"""

from __future__ import annotations

import os
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

import graphene
from graphene import (
    Boolean,
    Float,
    ID,
    String,
    relay,
    Field
)

from univa_jwt.decorators import login_required
from graphql import GraphQLError
from graphql_relay import from_global_id

from biometrics.models import (
    BiometricDevice,
    FaceEncoding,
    FaceVerification,
    FaceVerificationImage,
)
from biometrics.processing import ArcFaceModel
from biometrics.services.device_auth import (
    authenticate_device,
    get_challenge_for_device,
    revoke_device_challenge,
    DeviceAuthResult,
)
from biometrics.services.enrollment import (
    complete_pending_enrollment,
    create_pending_enrollment,
    enroll_face,
)
from biometrics.services.liveness import (
    evaluate_liveness,
)
from biometrics.services.matching import (
    match_face,
)
from biometrics.services.verification import (
    get_confidence_threshold,
    get_liveness_threshold,
    get_or_create_face_verification,
    get_verification_channel,
    get_verification_method,
    is_face_verified,
    requires_face_verification,
    verify_biometric,
)
from graphq.accounts.types import (
    UserNode,
)
from graphq.biometrics.types import (
    BiometricDeviceNode,
    FaceEncodingNode,
    FaceVerificationImageNode,
    FaceVerificationNode,
)
from graphq.accounts.mixin import (
    RateLimitMixin,
    TokenGenerationMixin,
)


# ============================================================================
# CONSTANTS
# ============================================================================

MAX_IMAGE_SIZE = 10 * 1024 * 1024

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
}

DEFAULT_MATCH_THRESHOLD = 0.4


# ============================================================================
# GRAPHQL RESULT TYPES
# ============================================================================


class FaceVerificationResult(graphene.ObjectType):
    """
    GraphQL representation of a biometric verification result.
    """

    verified = Boolean(required=True)

    confidence = Float(required=True)

    threshold = Float(required=True)

    message = String()

    method = String()

    channel = String()

    is_new_face = Boolean()

    image_id = ID()

    metadata = graphene.JSONString()


class FaceMatchResultType(graphene.ObjectType):
    """
    GraphQL representation of a face matching result.
    """

    matched = Boolean(required=True)

    confidence = Float(required=True)

    threshold = Float(required=True)

    distance = Float()

    encoding_id = ID()

    user_id = ID()


# ============================================================================
# HELPERS
# ============================================================================


def _get_authenticated_user(info):
    """
    Return the authenticated Django user.

    GraphQL mutations should call this rather than directly assuming
    authentication has already been applied.
    """

    user = getattr(
        info.context,
        "user",
        None,
    )

    if not user or not user.is_authenticated:
        raise GraphQLError(
            "Authentication required."
        )

    return user


def _coerce_optional_float(
    value,
    *,
    field_name: str = "value",
):
    """
    Coerce an optional numeric GraphQL input to float.

    Multipart form requests sometimes deliver numeric scalars as
    strings. Coerce here so domain services always receive a real
    float — or None when the client did not supply a value.

    Empty strings are treated as None (no value provided). Booleans
    are rejected to avoid silent ``True`` -> ``1.0`` coercion.
    """

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

    if isinstance(value, bool):
        raise GraphQLError(
            f"{field_name} must be numeric."
        )

    try:
        return float(value)
    except (TypeError, ValueError):
        raise GraphQLError(
            f"{field_name} must be numeric."
        )


def _validate_uploaded_image(uploaded_file):
    """
    Validate a biometric image upload.

    Returns the validated UploadedFile.
    """

    if not uploaded_file:
        raise GraphQLError(
            "No image provided."
        )

    if not isinstance(
        uploaded_file,
        UploadedFile,
    ):
        raise GraphQLError(
            "Invalid image upload."
        )

    if uploaded_file.size > MAX_IMAGE_SIZE:
        raise GraphQLError(
            "Image file too large. Maximum size is 10 MB."
        )

    content_type = (
        getattr(
            uploaded_file,
            "content_type",
            None,
        )
        or ""
    ).lower()

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise GraphQLError(
            "Only JPEG and PNG images are allowed."
        )

    return uploaded_file


def _save_uploaded_image(
    user,
    uploaded_file,
):
    """
    Persist the uploaded image as a FaceVerificationImage.

    The model owns the actual storage configuration.
    """

    return FaceVerificationImage.objects.create(
        user=user,
        image=uploaded_file,
        face_detected=False,
    )


def _process_uploaded_image(
    uploaded_file,
):
    """
    Persist an uploaded image temporarily for ArcFace processing.

    The temporary file is owned by the caller and must be deleted
    after processing.
    """

    uploaded_file.seek(0)

    suffix = ".jpg"

    content_type = (
        getattr(
            uploaded_file,
            "content_type",
            "",
        )
        or ""
    ).lower()

    if content_type == "image/png":
        suffix = ".png"

    temporary_file = tempfile.NamedTemporaryFile(
        suffix=suffix,
        delete=False,
    )

    try:
        for chunk in uploaded_file.chunks():
            temporary_file.write(chunk)

        temporary_file.flush()

        return temporary_file.name

    finally:
        temporary_file.close()


def _delete_temp_file(path):
    """
    Safely remove a temporary biometric image.
    """

    if not path:
        return

    try:
        if os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass


def _resolve_user(info, global_id):
    """
    Resolve a Relay global ID into a Django user.

    If no ID is provided, use the authenticated user.
    """

    if not global_id:
        return _get_authenticated_user(info)

    try:
        user = relay.Node.get_node_from_global_id(
            info,
            global_id,
        )
    except Exception as exc:
        raise GraphQLError(
            "Invalid user ID."
        ) from exc

    if user is None:
        raise GraphQLError(
            "User not found."
        )

    return user


def _result_from_verification(
    result,
    *,
    is_new_face=False,
    image_id=None,
):
    """
    Convert a service VerificationResult into GraphQL output.
    """

    metadata = getattr(
        result,
        "metadata",
        {},
    ) or {}

    return FaceVerificationResult(
        verified=bool(
            result.verified
        ),
        confidence=float(
            result.confidence
        ),
        threshold=float(
            result.threshold
        ),
        message=result.message,
        method=result.method,
        channel=result.channel,
        is_new_face=is_new_face,
        image_id=image_id,
        metadata=metadata,
    )


# ============================================================================
# FACE ENROLLMENT
# ============================================================================


class RegisterFaceMutation(
    RateLimitMixin,
    relay.ClientIDMutation,
):
    """
    Register a user's face.

    This mutation delegates enrollment to biometrics.services.enrollment.
    """

    class Input:
        set_as_primary = Boolean(
            default_value=True,
        )

        verify_immediately = Boolean(
            default_value=False,
        )

    success = Boolean(
        required=True,
    )

    verification = Field(
        FaceVerificationResult,
    )

    image = Field(
        FaceVerificationImageNode,
    )

    encoding = Field(
        FaceEncodingNode,
    )

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        user = _get_authenticated_user(
            info
        )

        uploaded_file = _validate_uploaded_image(
            info.context.FILES.get("image")
        )

        cls.check_global_rate_limit(
            info.context,
            "face_enrollment",
            limit=10,
            window=3600,
        )

        cls.check_rate_limit(
            f"face_enrollment:{user.pk}",
            limit=3,
            window=900,
        )

        set_as_primary = input.get(
            "set_as_primary",
            True,
        )

        verify_immediately = input.get(
            "verify_immediately",
            False,
        )

        profile_image = _save_uploaded_image(
            user,
            uploaded_file,
        )

        temp_path = None

        try:
            temp_path = _process_uploaded_image(
                uploaded_file
            )

            embedding, detection = (
                ArcFaceModel.get_embedding_and_detection(
                    temp_path
                )
            )

            profile_image.face_detected = True
            profile_image.face_count = 1
            profile_image.metadata = {
                "detection": detection,
            }

            profile_image.save(
                update_fields=[
                    "face_detected",
                    "face_count",
                    "metadata",
                ]
            )

            # ----------------------------------------------------------
            # Enrollment
            # ----------------------------------------------------------

            encoding = enroll_face(
                user,
                embedding,
                source_image=profile_image,
                is_primary=set_as_primary,
                version="v1",
                metadata={
                    "detection": detection,
                },
                verification_channel="photo",
            )

            # ----------------------------------------------------------
            # Immediate verification
            # ----------------------------------------------------------

            verification_result = None

            if verify_immediately:
                result = verify_biometric(
                    user,
                    embedding,
                    channel="photo",
                    metadata={
                        "source": "face_enrollment",
                        "image_id": profile_image.pk,
                    },
                )

                profile_image.is_verified = bool(
                    result.verified
                )

                profile_image.verification_score = float(
                    result.confidence
                )

                profile_image.save(
                    update_fields=[
                        "is_verified",
                        "verification_score",
                    ]
                )

                verification_result = (
                    _result_from_verification(
                        result,
                        is_new_face=True,
                        image_id=profile_image.pk,
                    )
                )

            return cls(
                success=True,
                verification=verification_result,
                image=profile_image,
                encoding=encoding,
            )

        except (ValidationError, ValueError) as exc:
            raise GraphQLError(
                str(exc)
            ) from exc

        finally:
            _delete_temp_file(
                temp_path
            )


# ============================================================================
# VERIFY FACE
# ============================================================================


class VerifyFaceMutation(
    RateLimitMixin,
    relay.ClientIDMutation,
):
    """
    Verify a supplied face against registered biometric encodings.

    The matching service owns pgvector access.
    """

    class Input:
        user_id = ID()

        liveness_score = Float()

    verification = Field(
        FaceVerificationResult,
    )

    @classmethod
    @login_required
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        authenticated_user = _get_authenticated_user(
            info
        )

        target_user = _resolve_user(
            info,
            input.get("user_id"),
        )

        # --------------------------------------------------------------
        # Authorization
        # --------------------------------------------------------------

        if (
            target_user.pk
            != authenticated_user.pk
        ):
            raise GraphQLError(
                "You are not authorized to verify another user's face."
            )

        cls.check_rate_limit(
            f"face_verify:{target_user.pk}",
            limit=3,
            window=300,
        )

        cls.check_global_rate_limit(
            info.context,
            "face_verification",
            limit=20,
            window=3600,
        )

        uploaded_file = _validate_uploaded_image(
            info.context.FILES.get("image")
        )

        temp_path = None

        try:
            temp_path = _process_uploaded_image(
                uploaded_file
            )

            embedding, detection = (
                ArcFaceModel.get_embedding_and_detection(
                    temp_path
                )
            )

            liveness_score = _coerce_optional_float(
                input.get("liveness_score"),
                field_name="Liveness score",
            )

            result = verify_biometric(
                target_user,
                embedding,
                liveness_score=liveness_score,
                channel="photo",
                metadata={
                    "detection": detection,
                },
            )

            return cls(
                verification=_result_from_verification(
                    result
                )
            )

        except ValueError as exc:
            raise GraphQLError(
                str(exc)
            ) from exc

        finally:
            _delete_temp_file(
                temp_path
            )


# ============================================================================
# AUTHENTICATE WITH FACE
# ============================================================================

class AuthenticateWithFaceMutation(
    RateLimitMixin,
    TokenGenerationMixin,
    relay.ClientIDMutation,
):
    """
    Authenticate a user using credentials plus optional face verification.

    Password authentication remains Django authentication's responsibility.

    Biometric verification is delegated to the biometrics service.

    JWT issuance remains owned by TokenGenerationMixin / univa_jwt.
    """

    class Input:
        contact = String(
            required=True
        )

        password = String(
            required=True
        )

        liveness_score = Float()

    token = String()

    refresh_token = String()

    user = Field(
        UserNode
    )

    requires_face_verification = Boolean()

    verification = Field(
        FaceVerificationResult
    )

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        from django.contrib.auth import authenticate

        contact = (
            input.get("contact")
            or ""
        ).strip()

        password = input.get(
            "password"
        )

        if not contact:
            raise GraphQLError(
                "Contact is required."
            )

        if not password:
            raise GraphQLError(
                "Password is required."
            )

        cls.check_rate_limit(
            f"auth_face:{contact}",
            limit=3,
            window=300,
        )

        cls.check_global_rate_limit(
            info.context,
            "authentication",
            limit=10,
            window=900,
        )

        user = None

        if "@" in contact:
            user = authenticate(
                request=info.context,
                email=contact,
                password=password,
            )
        else:
            user = authenticate(
                request=info.context,
                phone_number=contact,
                password=password,
            )

        if user is None:
            raise GraphQLError(
                "Invalid credentials."
            )

        # --------------------------------------------------------------
        # Determine biometric requirement
        # --------------------------------------------------------------

        if not is_face_verified(user):
            # No completed biometric enrollment.
            token, refresh_token = (
                cls.generate_tokens(
                    user,
                    request=info.context,
                )
            )

            return cls(
                token=token,
                refresh_token=refresh_token,
                user=user,
                requires_face_verification=False,
            )

        uploaded_file = info.context.FILES.get(
            "face_image"
        )

        if not uploaded_file:
            return cls(
                user=user,
                requires_face_verification=True,
            )

        uploaded_file = _validate_uploaded_image(
            uploaded_file
        )

        temp_path = None

        try:
            temp_path = _process_uploaded_image(
                uploaded_file
            )

            embedding, detection = (
                ArcFaceModel.get_embedding_and_detection(
                    temp_path
                )
            )

            liveness_score = _coerce_optional_float(
                input.get("liveness_score"),
                field_name="Liveness score",
            )

            result = verify_biometric(
                user,
                embedding,
                liveness_score=liveness_score,
                channel="photo",
                metadata={
                    "source": "authentication",
                    "detection": detection,
                },
            )

            if not result.verified:
                raise GraphQLError(
                    "Face verification failed."
                )

            token, refresh_token = (
                cls.generate_tokens(
                    user,
                    request=info.context,
                )
            )

            return cls(
                token=token,
                refresh_token=refresh_token,
                user=user,
                requires_face_verification=False,
                verification=_result_from_verification(
                    result
                ),
            )

        except ValueError as exc:
            raise GraphQLError(
                str(exc)
            ) from exc

        finally:
            _delete_temp_file(
                temp_path
            )


# ============================================================================
# MAGIC LINK FACE VERIFICATION
# ============================================================================


class VerifyFaceForMagicLinkMutation(
    RateLimitMixin,
    TokenGenerationMixin,
    relay.ClientIDMutation,
):
    """
    Complete a magic-login flow using face verification.

    The MagicLoginToken belongs to Accounts.

    Biometrics only verifies the user's face.

    JWT issuance remains delegated to the canonical JWT boundary.
    """

    class Input:
        token = String(
            required=True
        )

        liveness_score = Float()

    success = Boolean(
        required=True
    )

    token = String()

    refresh_token = String()

    user = Field(
        UserNode
    )

    verification = Field(
        FaceVerificationResult
    )

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        from accounts.models import MagicLoginToken

        magic_token = (
            input.get("token")
            or ""
        ).strip()

        if not magic_token:
            raise GraphQLError(
                "Magic login token is required."
            )

        uploaded_file = _validate_uploaded_image(
            info.context.FILES.get("image")
        )

        try:
            token_record = (
                MagicLoginToken.validate_token(
                    magic_token,
                    purpose="login",
                    request=info.context,
                )
            )
        except ValueError as exc:
            raise GraphQLError(
                str(exc)
            ) from exc

        user = token_record.user

        cls.check_rate_limit(
            f"magic_face:{user.pk}",
            limit=3,
            window=300,
        )

        cls.check_global_rate_limit(
            info.context,
            "magic_face_authentication",
            limit=10,
            window=900,
        )

        if not is_face_verified(user):
            raise GraphQLError(
                "Face verification is not configured for this account."
            )

        temp_path = None

        try:
            temp_path = _process_uploaded_image(
                uploaded_file
            )

            embedding, detection = (
                ArcFaceModel.get_embedding_and_detection(
                    temp_path
                )
            )

            liveness_score = _coerce_optional_float(
                input.get("liveness_score"),
                field_name="Liveness score",
            )

            result = verify_biometric(
                user,
                embedding,
                liveness_score=liveness_score,
                channel="photo",
                metadata={
                    "source": "magic_link",
                    "detection": detection,
                },
            )

            if not result.verified:
                raise GraphQLError(
                    "Face verification failed."
                )

            token, refresh_token = (
                cls.generate_tokens(
                    user,
                    request=info.context,
                )
            )

            # Only consume the magic token after biometric verification
            # and JWT issuance have both succeeded.
            token_record.mark_as_used()

            return cls(
                success=True,
                token=token,
                refresh_token=refresh_token,
                user=user,
                verification=_result_from_verification(
                    result
                ),
            )

        except ValueError as exc:
            raise GraphQLError(
                str(exc)
            ) from exc

        finally:
            _delete_temp_file(
                temp_path
            )


# ============================================================================
# COMPARE FACES
# ============================================================================


class CompareFacesMutation(
    RateLimitMixin,
    relay.ClientIDMutation,
):
    """
    Compare a submitted face against the authenticated user's
    registered face.

    This mutation deliberately does not permit arbitrary user-to-user
    biometric comparison.

    Biometric templates are security-sensitive data and should not be
    exposed as a general comparison primitive.
    """

    class Input:
        liveness_score = Float()

    similarity_score = Float()

    are_similar = Boolean()

    threshold = Float()

    @classmethod
    @login_required
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        user = _get_authenticated_user(
            info
        )

        cls.check_rate_limit(
            f"compare_face:{user.pk}",
            limit=3,
            window=300,
        )

        uploaded_file = _validate_uploaded_image(
            info.context.FILES.get("image")
        )

        temp_path = None

        try:
            temp_path = _process_uploaded_image(
                uploaded_file
            )

            embedding, _ = (
                ArcFaceModel.get_embedding_and_detection(
                    temp_path
                )
            )

            threshold = get_confidence_threshold(
                user,
                default=DEFAULT_MATCH_THRESHOLD,
            )

            result = match_face(
                embedding,
                threshold=threshold,
            )

            # The matching service may return a result for another
            # account if it performs global matching. Do not expose
            # another user's identity through this mutation.
            are_similar = (
                result.matched
                and getattr(
                    result,
                    "user_id",
                    user.pk,
                )
                == user.pk
            )

            similarity_score = float(
                result.similarity
            )

            return cls(
                similarity_score=similarity_score,
                are_similar=are_similar,
                threshold=float(
                    result.threshold
                ),
            )

        finally:
            _delete_temp_file(
                temp_path
            )


# ============================================================================
# LIVENESS
# ============================================================================

class VerifyLivenessMutation(
    RateLimitMixin,
    relay.ClientIDMutation,
):
    """
    Evaluate a liveness score.

    Actual liveness detection should be performed by the biometric
    processing/client pipeline. This service validates the resulting
    score against the configured policy.
    """

    class Input:
        score = Float(
            required=True
        )

        threshold = Float()

    success = Boolean(
        required=True
    )

    is_live = Boolean(
        required=True
    )

    score = Float(
        required=True
    )

    threshold = Float(
        required=True
    )

    method = String()

    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        user = _get_authenticated_user(
            info
        )

        cls.check_rate_limit(
            f"liveness:{user.pk}",
            limit=5,
            window=300,
        )

        configured_threshold = (
            get_liveness_threshold(
                user,
                default=0.8,
            )
        )

        threshold = input.get(
            "threshold"
        )

        # Clients may not weaken the configured security policy.
        if threshold is None:
            threshold = configured_threshold
        else:
            threshold = max(
                float(threshold),
                float(configured_threshold),
            )

        result = evaluate_liveness(
            float(input["score"]),
            threshold,
        )

        return cls(
            success=bool(
                result.is_live
            ),
            is_live=bool(
                result.is_live
            ),
            score=float(
                result.score
            ),
            threshold=float(
                result.threshold
            ),
            method=result.method,
            message=(
                "Liveness verification successful."
                if result.is_live
                else "Liveness verification failed."
            ),
        )


# ============================================================================
# BIOMETRIC DEVICE CHALLENGE (NEW)
# ============================================================================


class GetBiometricChallengeMutation(
    RateLimitMixin,
    relay.ClientIDMutation,
):
    """
    Get a challenge for biometric device authentication.

    This is the first step in the biometric authentication flow.
    The client must sign this challenge with the device's private key.
    """

    class Input:
        device_id = String(
            required=True
        )

    challenge = String(
        required=True
    )

    expires_in_seconds = graphene.Int(
        required=True
    )

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        device_id = (
            input.get("device_id")
            or ""
        ).strip()

        if not device_id:
            raise GraphQLError(
                "Device ID is required."
            )

        cls.check_rate_limit(
            f"biometric_challenge:{device_id}",
            limit=5,
            window=300,
        )

        # Check if device exists and is trusted
        device = (
            BiometricDevice.objects
            .filter(
                device_id=device_id,
                trusted=True,
            )
            .first()
        )

        if device is None:
            raise GraphQLError(
                "Device not registered or not trusted."
            )

        # Generate challenge
        challenge_data = get_challenge_for_device(device_id)

        return cls(
            challenge=challenge_data["challenge"],
            expires_in_seconds=challenge_data["expires_in_seconds"],
        )


# ============================================================================
# BIOMETRIC DEVICE REGISTRATION
# ============================================================================



class RegisterBiometricDeviceMutation(
    relay.ClientIDMutation,
):
    """
    Register a trusted biometric authentication device.

    BiometricDevice belongs directly to User.
    """

    class Input:
        device_id = String(
            required=True
        )

        public_key = String(
            required=True
        )

        device_name = String()

    device = Field(
        BiometricDeviceNode
    )

    success = Boolean(
        required=True
    )

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        user = _get_authenticated_user(
            info
        )

        device_id = (
            input.get("device_id")
            or ""
        ).strip()

        public_key = (
            input.get("public_key")
            or ""
        ).strip()

        if not device_id:
            raise GraphQLError(
                "Device ID is required."
            )

        if not public_key:
            raise GraphQLError(
                "Public key is required."
            )

        # Validate public key
        from biometrics.services.device_auth import validate_public_key

        try:
            validate_public_key(public_key)
        except Exception as exc:
            raise GraphQLError(f"Invalid public key: {exc}") from exc

        device, _ = (
            BiometricDevice.objects.update_or_create(
                user=user,
                device_id=device_id,
                defaults={
                    "public_key": public_key,
                    "device_info": (
                        input.get(
                            "device_name"
                        )
                        or ""
                    ),
                    "trusted": True,
                    "last_used_at": timezone.now(),
                },
            )
        )

        return cls(
            device=device,
            success=True,
        )


# ============================================================================
# BIOMETRIC DEVICE AUTHENTICATION (UPDATED - REPLACE THE PLACEHOLDER)
# ============================================================================


class BiometricAuthMutation(
    RateLimitMixin,
    TokenGenerationMixin,
    relay.ClientIDMutation,
):
    """
    Authenticate using a registered biometric device.

    Cryptographic signature verification is delegated to the
    device-authentication service.

    This mutation performs the complete biometric authentication flow:
        1. Validate device exists and is trusted
        2. Verify cryptographic signature
        3. Issue JWT on success
    """

    class Input:
        device_id = String(
            required=True
        )

        signature = String(
            required=True
        )

        challenge = String(
            required=True
        )

    token = String()

    refresh_token = String()

    user = Field(
        UserNode
    )

    success = Boolean(
        required=True
    )

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        device_id = (
            input.get("device_id")
            or ""
        ).strip()

        signature = (
            input.get("signature")
            or ""
        ).strip()

        challenge = (
            input.get("challenge")
            or ""
        ).strip()

        if not device_id:
            raise GraphQLError(
                "Device ID is required."
            )

        if not signature:
            raise GraphQLError(
                "Signature is required."
            )

        if not challenge:
            raise GraphQLError(
                "Challenge is required."
            )

        cls.check_rate_limit(
            f"biometric_auth:{device_id}",
            limit=3,
            window=300,
        )

        cls.check_global_rate_limit(
            info.context,
            "biometric_auth",
            limit=15,
            window=3600,
        )

        device = (
            BiometricDevice.objects
            .select_related("user")
            .filter(
                device_id=device_id,
                trusted=True,
            )
            .first()
        )

        if device is None:
            raise GraphQLError(
                "Device not registered or not trusted."
            )

        if not device.public_key:
            raise GraphQLError(
                "Device has no registered public key."
            )

        # --------------------------------------------------------------
        # Perform cryptographic signature verification
        # --------------------------------------------------------------

        result = authenticate_device(
            device_id=device_id,
            public_key_pem=device.public_key,
            challenge=challenge,
            signature=signature,
        )

        if not result.verified:
            if result.lockout_until:
                raise GraphQLError(
                    f"Device locked until {result.lockout_until.isoformat()}"
                )
            raise GraphQLError(
                result.message or "Biometric authentication failed."
            )

        # --------------------------------------------------------------
        # Update device last used
        # --------------------------------------------------------------

        device.mark_used()

        # --------------------------------------------------------------
        # Issue JWT
        # --------------------------------------------------------------

        token, refresh_token = (
            cls.generate_tokens(
                device.user,
                request=info.context,
            )
        )

        return cls(
            token=token,
            refresh_token=refresh_token,
            user=device.user,
            success=True,
        )



# ============================================================================
# QUERY-SAFE STATE MUTATION
# ============================================================================

# apps/backend/graphq/biometrics/mutations.py

class FaceVerificationStatusMutation(
    relay.ClientIDMutation,
):
    """
    Return the current biometric verification state.

    This is useful to mobile clients after enrollment or authentication.
    """

    success = Boolean(
        required=True
    )

    is_verified = Boolean(
        required=True
    )

    requires_verification = Boolean(
        required=True
    )

    verification_method = String()

    verification_channel = String()

    confidence_threshold = Float()

    liveness_threshold = Float()

    @classmethod
    @login_required
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        user = _get_authenticated_user(
            info
        )

        verification = (
            get_or_create_face_verification(
                user
            )[0]
        )

        return cls(
            success=True,
            is_verified=bool(
                verification.is_verified
            ),
            requires_verification=(
                requires_face_verification(
                    user
                )
            ),
            verification_method=(
                get_verification_method(
                    user
                )
            ),
            verification_channel=(
                get_verification_channel(
                    user
                )
            ),
            confidence_threshold=(
                get_confidence_threshold(
                    user
                )
            ),
            liveness_threshold=(
                get_liveness_threshold(
                    user
                )
            ),
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class BiometricsMutations(graphene.ObjectType):
    register_face = RegisterFaceMutation.Field()
    verify_face = VerifyFaceMutation.Field()
    authenticate_with_face = AuthenticateWithFaceMutation.Field()
    verify_face_for_magic_link = VerifyFaceForMagicLinkMutation.Field()
    compare_faces = CompareFacesMutation.Field()
    verify_liveness = VerifyLivenessMutation.Field()
    register_biometric_device = RegisterBiometricDeviceMutation.Field()
    biometric_auth = BiometricAuthMutation.Field()
    get_biometric_challenge = GetBiometricChallengeMutation.Field()
    face_verification_status = FaceVerificationStatusMutation.Field()


# ============================================================================
# MUTATION EXPORTS
# ============================================================================

__all__ = [
    "BiometricsMutations",

    "RegisterFaceMutation",
    "VerifyFaceMutation",
    "AuthenticateWithFaceMutation",
    "VerifyFaceForMagicLinkMutation",
    "CompareFacesMutation",
    "VerifyLivenessMutation",
    "RegisterBiometricDeviceMutation",
    "BiometricAuthMutation",
    "GetBiometricChallengeMutation",
    "FaceVerificationStatusMutation",
]