# apps/backend/graphq/accounts/mixin.py

"""
Shared mutation mixins for the Accounts GraphQL layer.

Architecture
------------

This module contains shared GraphQL mutation infrastructure.

The Accounts GraphQL layer has three deliberately separated concerns:

    RateLimitMixin
        -> request/rate limiting only

    TokenGenerationMixin
        -> delegates authentication-token issuance to univa_jwt

    FaceProcessingMixin
        -> biometric/image-processing utilities

JWT ARCHITECTURAL BOUNDARY
--------------------------

GraphQL mutations do not implement JWT logic.

The canonical authentication boundary is:

    GraphQL Mutation
          |
          v
    TokenGenerationMixin
          |
          +----> univa_jwt.shortcuts.get_token()
          |
          +----> univa_jwt.tokens.create_refresh_token()
          |
          v
    Access + Refresh Tokens

Refresh-token rotation is owned by:

    univa_jwt.refresh

Refresh-token revocation is owned by:

    univa_jwt.revocation

The deprecated:

    univa_jwt.models.RefreshToken

model is NOT used by this module.

BIOMETRIC ARCHITECTURAL BOUNDARY
--------------------------------

InsightFace is a domain-specific biometric dependency.

It MUST NOT be imported or initialized when this module is merely
being imported by ordinary Accounts mutations.

Therefore InsightFace dependencies are loaded lazily inside the
biometric workflow itself.

This prevents:

    import graphq.accounts.mutations.user

from requiring InsightFace to be installed or initialized.

This is particularly important because account registration,
authentication, email verification, and user management do not
require biometric processing.

FAILURE ISOLATION
-----------------

If InsightFace is unavailable:

    - account mutations can still import
    - JWT functionality can still import
    - rate limiting can still import
    - email-verification functionality can still import

Only operations that explicitly invoke FaceProcessingMixin will fail,
with a clear GraphQLError explaining that biometric processing is
unavailable.

This module therefore follows the dependency direction:

    CORE
      |
      v
    ACCOUNTS
      |
      +----> GraphQL account mutations
      |
      +----> authentication services
      |
      +----> email services
      |
      +----> biometric workflows where explicitly required

Biometric processing is never an implicit dependency of account
registration.
"""

from __future__ import annotations

import logging
import tempfile

import numpy as np

from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone

from graphql import GraphQLError

from PIL import Image


logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

MIN_PASSWORD_LENGTH = 8

MAX_AUTH_ATTEMPTS = 5

AUTH_ATTEMPT_WINDOW = 300  # 5 minutes


# =============================================================================
# RATE LIMITING
# =============================================================================


class RateLimitMixin:
    """
    Shared cache-backed rate limiting for GraphQL mutations.

    This mixin contains no authentication logic and no JWT logic.
    """

    @classmethod
    def check_rate_limit(
        cls,
        key,
        limit=5,
        window=300,
        identifier=None,
    ):
        """
        Check and increment a rate-limit counter.

        Args:
            key:
                Logical identifier for the protected operation.

            limit:
                Maximum number of attempts allowed within the window.

            window:
                Rate-limit window in seconds.

            identifier:
                Optional secondary identifier used for diagnostics.

        Raises:
            GraphQLError:
                When the rate limit has been exceeded.

        Returns:
            bool:
                True when the request is allowed.
        """

        cache_key = (
            f"rate_limit:{key}"
        )

        attempts_data = cache.get(
            cache_key,
            {
                "count": 0,
                "identifiers": set(),
            },
        )

        # Defensive handling in case a cache backend returns an unexpected
        # value instead of the expected dictionary.
        if not isinstance(
            attempts_data,
            dict,
        ):
            attempts_data = {
                "count": 0,
                "identifiers": set(),
            }

        current_count = attempts_data.get(
            "count",
            0,
        )

        try:
            current_count = int(
                current_count,
            )
        except (
            TypeError,
            ValueError,
        ):
            current_count = 0

        identifiers = attempts_data.get(
            "identifiers",
            set(),
        )

        # Cache backends may serialize sets differently.
        if not isinstance(
            identifiers,
            set,
        ):
            identifiers = set(
                identifiers or [],
            )

        if identifier:
            identifiers.add(
                str(identifier),
            )

        if current_count >= limit:
            minutes = max(
                1,
                window // 60,
            )

            raise GraphQLError(
                (
                    "Too many attempts. "
                    f"Please try again in {minutes} minutes."
                )
            )

        first_attempt = attempts_data.get(
            "first_attempt",
        )

        if first_attempt is None:
            first_attempt = timezone.now()

        cache.set(
            cache_key,
            {
                "count": current_count + 1,
                "identifiers": identifiers,
                "first_attempt": first_attempt,
            },
            timeout=window,
        )

        return True

    @classmethod
    def get_remaining_attempts(
        cls,
        key,
        limit=5,
    ):
        """
        Return the number of attempts remaining.
        """

        cache_key = (
            f"rate_limit:{key}"
        )

        data = cache.get(
            cache_key,
            {
                "count": 0,
            },
        )

        if not isinstance(
            data,
            dict,
        ):
            data = {
                "count": 0,
            }

        count = data.get(
            "count",
            0,
        )

        try:
            count = int(
                count,
            )
        except (
            TypeError,
            ValueError,
        ):
            count = 0

        return max(
            0,
            limit - count,
        )

    @classmethod
    def check_global_rate_limit(
        cls,
        request,
        action,
        limit=100,
        window=3600,
    ):
        """
        Apply a global rate limit based on the request IP address.
        """

        ip_address = (
            request.META.get(
                "REMOTE_ADDR",
            )
            or "unknown"
        )

        key = (
            f"global_rate_limit:"
            f"{action}:"
            f"{ip_address}"
        )

        return cls.check_rate_limit(
            key,
            limit=limit,
            window=window,
        )


# =============================================================================
# TOKEN GENERATION
# =============================================================================


class TokenGenerationMixin:
    """
    Canonical JWT issuance boundary for GraphQL mutations.

    This class deliberately contains no JWT implementation.

    Access token:

        univa_jwt.shortcuts.get_token()

    Refresh token:

        univa_jwt.tokens.create_refresh_token()

    Refresh-token rotation and revocation are deliberately outside
    this mixin.

    IMPORTANT
    ---------

    This mixin does not:

        - encode JWT payloads
        - construct JWT claims manually
        - access RefreshToken.objects
        - import univa_jwt.models.RefreshToken
        - revoke refresh tokens
        - rotate refresh tokens
        - manage refresh-token persistence directly

    The univa_jwt package owns those concerns.
    """

    @classmethod
    def generate_tokens(
        cls,
        user,
        request=None,
    ):
        """
        Issue canonical Univa access and refresh tokens.

        Parameters
        ----------
        user:
            Django user for whom credentials are issued.

        request:
            Optional Django request.

            Accepted for GraphQL compatibility. The canonical JWT
            issuance API does not currently require it.

        Returns
        -------
        tuple[str, str]
            ``(access_token, refresh_token)``

        Raises
        ------
        ValueError
            If the user is missing, unsaved, or inactive.

        Notes
        -----

        Security-sensitive exceptions raised by ``univa_jwt`` are
        intentionally allowed to propagate.
        """

        # ``request`` is retained for API compatibility. The canonical
        # token functions currently do not require it.
        del request

        # ---------------------------------------------------------------------
        # Validate user
        # ---------------------------------------------------------------------

        if user is None:
            raise ValueError(
                "User is required.",
            )

        user_id = getattr(
            user,
            "pk",
            None,
        )

        if not user_id:
            raise ValueError(
                "User must have a primary key.",
            )

        if not getattr(
            user,
            "is_active",
            False,
        ):
            raise ValueError(
                "User account is disabled.",
            )

        # ---------------------------------------------------------------------
        # Import canonical JWT boundaries lazily
        # ---------------------------------------------------------------------
        #
        # Keeping these imports inside the method avoids unnecessary
        # authentication-package initialization when this mixin is merely
        # imported.
        # ---------------------------------------------------------------------

        from univa_jwt.shortcuts import get_token
        from univa_jwt.tokens import create_refresh_token

        # ---------------------------------------------------------------------
        # Access token
        # ---------------------------------------------------------------------

        access_token = get_token(
            user,
        )

        # ---------------------------------------------------------------------
        # Refresh token
        # ---------------------------------------------------------------------
        #
        # create_refresh_token() is the canonical refresh-token boundary.
        #
        # It returns:
        #
        #     (encoded_token, TokenClaims)
        #
        # This GraphQL mixin deliberately does not inspect or persist the
        # refresh-token claims.
        # ---------------------------------------------------------------------

        refresh_token, _refresh_claims = (
            create_refresh_token(
                user_id=str(
                    user_id,
                ),
            )
        )

        return (
            access_token,
            refresh_token,
        )


# =============================================================================
# FACE PROCESSING
# =============================================================================


class FaceProcessingMixin:
    """
    Shared InsightFace processing utilities.

    IMPORTANT
    ---------

    InsightFace is intentionally NOT imported at module level.

    The model is initialized lazily the first time biometric processing
    is actually requested.

    This means importing:

        graphq.accounts.mixin

    does not require InsightFace.

    It also means ordinary account mutations such as:

        - registration
        - login
        - profile management
        - email verification
        - account deletion

    do not initialize the biometric runtime.

    Only a mutation/workflow that explicitly uses FaceProcessingMixin
    will load InsightFace.
    """

    _face_model = None

    # =========================================================================
    # INSIGHTFACE LOADING
    # =========================================================================

    @classmethod
    def get_face_model(
        cls,
    ):
        """
        Lazily initialize and return the shared InsightFace model.

        Returns:
            insightface.app.FaceAnalysis

        Raises:
            GraphQLError:
                If InsightFace or one of its runtime dependencies is
                unavailable or model initialization fails.
        """

        if cls._face_model is not None:
            return cls._face_model

        # ---------------------------------------------------------------------
        # Lazy import
        # ---------------------------------------------------------------------

        try:
            import insightface

        except ImportError as exc:
            logger.exception(
                "InsightFace is unavailable.",
            )

            raise GraphQLError(
                (
                    "Biometric processing is currently unavailable. "
                    "The InsightFace dependency is not installed."
                )
            ) from exc

        # ---------------------------------------------------------------------
        # Initialize model
        # ---------------------------------------------------------------------

        try:
            model = insightface.app.FaceAnalysis(
                name="buffalo_l",
                providers=[
                    "CUDAExecutionProvider",
                    "CPUExecutionProvider",
                ],
            )

            # Use CPU context by default.

            # This avoids forcing CUDA for environments where GPU support
            # is unavailable. InsightFace can still use the configured
            # providers.
            model.prepare(
                ctx_id=0,
            )

        except Exception as exc:
            logger.exception(
                "Failed to initialize InsightFace.",
            )

            raise GraphQLError(
                "Biometric processing could not be initialized.",
            ) from exc

        cls._face_model = model

        return cls._face_model

    # =========================================================================
    # IMAGE VALIDATION
    # =========================================================================

    @staticmethod
    def process_uploaded_image(
        uploaded_file,
    ):
        """
        Validate an uploaded image and persist it temporarily.

        Parameters
        ----------
        uploaded_file:
            Django uploaded-file object.

        Returns
        -------
        str
            Path to the temporary image file.

        Raises
        ------
        GraphQLError
            If the uploaded object is invalid or the image cannot be
            decoded.
        """

        if not isinstance(
            uploaded_file,
            InMemoryUploadedFile,
        ):
            raise GraphQLError(
                "Invalid file format.",
            )

        try:
            uploaded_file.seek(
                0,
            )

            # -----------------------------------------------------------------
            # Validate image
            # -----------------------------------------------------------------

            image = Image.open(
                uploaded_file,
            )

            image.verify()

            # ``verify()`` consumes the stream. Reset before writing.
            uploaded_file.seek(
                0,
            )

            # -----------------------------------------------------------------
            # Persist temporary image
            # -----------------------------------------------------------------

            with tempfile.NamedTemporaryFile(
                suffix=".jpg",
                delete=False,
            ) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(
                        chunk,
                    )

                return tmp.name

        except GraphQLError:
            raise

        except Exception as exc:
            logger.warning(
                "Uploaded biometric image failed validation: %s",
                exc,
            )

            raise GraphQLError(
                "Invalid image file.",
            ) from exc

    # =========================================================================
    # FACE EMBEDDING
    # =========================================================================

    def get_face_embedding(
        self,
        image_path,
    ):
        """
        Extract an ArcFace embedding from an image.

        Parameters
        ----------
        image_path:
            Path to a validated image file.

        Returns
        -------
        tuple
            (
                embedding_as_list,
                face_bbox,
            )

        Raises
        ------
        GraphQLError
            If no face is detected, multiple faces are detected, or
            biometric processing fails.
        """

        model = self.get_face_model()

        try:
            faces = model.get(
                image_path,
            )

            if len(faces) == 0:
                raise GraphQLError(
                    "No face detected.",
                )

            if len(faces) > 1:
                raise GraphQLError(
                    "Image must contain exactly one face.",
                )

            face = faces[0]

            embedding = np.asarray(
                face.embedding,
                dtype=np.float32,
            )

            return (
                embedding.tolist(),
                face.bbox,
            )

        except GraphQLError:
            raise

        except Exception as exc:
            logger.exception(
                "Face processing failed for image %s.",
                image_path,
            )

            raise GraphQLError(
                "Face processing failed.",
            ) from exc


__all__ = [
    "MIN_PASSWORD_LENGTH",
    "MAX_AUTH_ATTEMPTS",
    "AUTH_ATTEMPT_WINDOW",
    "RateLimitMixin",
    "TokenGenerationMixin",
    "FaceProcessingMixin",
]
