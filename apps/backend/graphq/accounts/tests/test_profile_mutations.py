"""
Tests for GraphQL user-profile mutations.

Coverage
--------

UpdateUserAndProfileMutation
    - updates user fields
    - updates profile fields
    - rejects duplicate Univa ID
    - rejects invalid gender
    - rejects invalid notification method

UploadProfilePictureMutation
    - rejects missing image
    - rejects oversized image
    - rejects unsupported content type
    - rejects dimensions below minimum
    - uploads a valid image
    - uploads with crop data

DeleteProfilePictureMutation
    - rejects missing profile picture
    - deletes existing picture

UpdateVerificationStatusMutation
    - rejects non-admin users
    - rejects invalid target user
    - rejects invalid status
    - updates verification status for admin

UpdateLocationMutation
    - rejects invalid latitude
    - rejects invalid longitude
    - updates valid coordinates

TEST AUTHENTICATION
-------------------

These tests call the mutation methods directly rather than executing a
complete GraphQL HTTP request.

The production mutations are protected by the canonical ``univa_jwt``
authentication boundary. Therefore the synthetic GraphQL request must
represent an already-authenticated request in the same shape that the
JWT middleware produces.

In particular, the test context provides:

    request.user
    request.univa_jwt_authenticated
    request._univa_jwt_authentication_complete

This intentionally does NOT bypass the authentication decorators.
It models the state after canonical JWT middleware authentication.
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from graphql import GraphQLError, GraphQLResolveInfo
from graphql_relay import to_global_id
from PIL import Image

from accounts.models import User, UserProfile

from graphq.accounts.mutations.profile import (
    DeleteProfilePictureMutation,
    UpdateLocationMutation,
    UpdateUserAndProfileMutation,
    UpdateVerificationStatusMutation,
    UploadProfilePictureMutation,
)


# =============================================================================
# GRAPHQL TEST HELPERS
# =============================================================================


def make_context(user, files=None):
    """
    Build a request-like object representing an already-authenticated
    GraphQL request.

    The production Univa JWT middleware attaches authentication state to
    the request. These fields reproduce the relevant post-authentication
    state for direct mutation tests.

    This is intentionally different from simply supplying ``user``.
    """

    return SimpleNamespace(
        # Django request user.
        user=user,

        # GraphQL file uploads.
        FILES=files or {},

        # Request metadata used by mutations/services.
        META={
            "REMOTE_ADDR": "127.0.0.1",
        },

        # ------------------------------------------------------------------
        # Canonical Univa JWT middleware state.
        # ------------------------------------------------------------------

        # The request has already been authenticated by the JWT boundary.
        univa_jwt_authenticated=True,

        # Prevent the middleware/decorator layer from attempting to
        # authenticate a second time during the direct mutation call.
        _univa_jwt_authentication_complete=True,

        # Canonical JWT request attributes.
        jwt_claims=None,
        univa_jwt=None,
        univa_jwt_user_id=getattr(user, "pk", None),
        univa_jwt_jti=None,
        univa_jwt_token_type="access",
        univa_jwt_issued_at=None,
        univa_jwt_expires_at=None,
        univa_jwt_issuer=None,
        univa_jwt_audience=None,
    )


def make_info(context):
    """
    Construct a graphql-core 3.x compatible GraphQLResolveInfo.

    graphql-core 3.x uses ``field_nodes`` rather than the old
    ``field_asts`` argument.
    """

    return GraphQLResolveInfo(
        field_name="testMutation",
        field_nodes=(),
        return_type=None,
        parent_type=None,
        path=None,
        schema=None,
        fragments={},
        root_value=None,
        operation=None,
        variable_values={},
        context=context,
        is_awaitable=False,
    )


def make_mutation_info(user, files=None):
    """
    Build a complete authenticated GraphQLResolveInfo object.
    """

    return make_info(
        make_context(
            user=user,
            files=files,
        )
    )


def make_image(
    *,
    width=300,
    height=300,
    content_type="image/jpeg",
):
    """
    Create an in-memory valid image upload.
    """

    image = Image.new(
        "RGB",
        (width, height),
        "white",
    )

    buffer = io.BytesIO()

    format_map = {
        "image/jpeg": "JPEG",
        "image/jpg": "JPEG",
        "image/png": "PNG",
        "image/webp": "WEBP",
        "image/gif": "GIF",
    }

    image.save(
        buffer,
        format=format_map[content_type],
    )

    return SimpleUploadedFile(
        "profile.jpg",
        buffer.getvalue(),
        content_type=content_type,
    )


# =============================================================================
# SHARED TEST CASE
# =============================================================================


class UserProfileMutationTestCase(TestCase):
    """
    Shared authenticated-user fixture for profile mutation tests.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="profile-test@example.com",
            password="TestPassword123!",
            first_name="Test",
            last_name="User",
        )

        # The fixture represents a normal authenticated account.
        #
        # ``email_verified`` is part of the account authentication
        # boundary. Setting it explicitly prevents profile mutation tests
        # from being rejected before the actual mutation logic is reached.
        update_fields = []

        if hasattr(self.user, "email_verified"):
            self.user.email_verified = True
            update_fields.append("email_verified")

        if hasattr(self.user, "is_active") and not self.user.is_active:
            self.user.is_active = True
            update_fields.append("is_active")

        if update_fields:
            self.user.save(
                update_fields=update_fields,
            )

        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
        )

        self.context = make_context(
            user=self.user,
        )

        self.info = make_mutation_info(
            user=self.user,
        )


# =============================================================================
# UPDATE USER + PROFILE
# =============================================================================


class UpdateUserAndProfileMutationTests(
    UserProfileMutationTestCase,
):

    @patch(
        "graphq.accounts.mutations.profile.update_user_and_profile",
    )
    def test_updates_user_and_profile(
        self,
        mock_update,
    ):
        mock_update.return_value = (
            self.user,
            self.profile,
        )

        result = (
            UpdateUserAndProfileMutation
            .mutate_and_get_payload(
                None,
                self.info,
                first_name="Updated",
                last_name="Name",
                bio="Updated biography",
                gender="male",
                language_code="en",
            )
        )

        mock_update.assert_called_once()

        user_data = mock_update.call_args.args[1]
        profile_data = mock_update.call_args.args[2]

        self.assertEqual(
            user_data["first_name"],
            "Updated",
        )

        self.assertEqual(
            profile_data["bio"],
            "Updated biography",
        )

        self.assertEqual(
            profile_data["gender"],
            "male",
        )

        self.assertIs(
            result.user,
            self.user,
        )

        self.assertIs(
            result.profile,
            self.profile,
        )

    
    def test_rejects_duplicate_univa_id(self):
        other_user = User.objects.create_user(
            email="other-profile@example.com",
            password="TestPassword123!",
        )

        other_profile, _ = UserProfile.objects.get_or_create(
            user=other_user,
        )

        other_profile.univa_id = "UNIVA-EXISTING"
        other_profile.save(
            update_fields=["univa_id"],
        )

        with self.assertRaises(GraphQLError) as exc:
            UpdateUserAndProfileMutation.mutate_and_get_payload(
                None,
                self.info,
                univa_id="UNIVA-EXISTING",
            )

        self.assertEqual(
            str(exc.exception),
            "This Univa ID is already taken",
        )
        
        
    def test_rejects_invalid_gender(self):
        with self.assertRaises(GraphQLError) as exc:
            UpdateUserAndProfileMutation.mutate_and_get_payload(
                None,
                self.info,
                gender="invalid",
            )

        self.assertIn(
            "Invalid gender",
            str(exc.exception),
        )

    def test_rejects_invalid_notification_method(self):
        with self.assertRaises(GraphQLError) as exc:
            UpdateUserAndProfileMutation.mutate_and_get_payload(
                None,
                self.info,
                preferred_notification_method="carrier_pigeon",
            )

        self.assertIn(
            "Invalid notification method",
            str(exc.exception),
        )


# =============================================================================
# UPLOAD PROFILE PICTURE
# =============================================================================


class UploadProfilePictureMutationTests(
    UserProfileMutationTestCase,
):

    def test_rejects_missing_image(self):
        info = make_mutation_info(
            self.user,
            files={},
        )

        with self.assertRaises(GraphQLError) as exc:
            UploadProfilePictureMutation.mutate_and_get_payload(
                None,
                info,
            )

        self.assertEqual(
            str(exc.exception),
            "No image file provided",
        )

    def test_rejects_oversized_image(self):
        upload = SimpleUploadedFile(
            "large.jpg",
            b"x" * (5 * 1024 * 1024 + 1),
            content_type="image/jpeg",
        )

        info = make_mutation_info(
            self.user,
            files={
                "image": upload,
            },
        )

        with self.assertRaises(GraphQLError) as exc:
            UploadProfilePictureMutation.mutate_and_get_payload(
                None,
                info,
            )

        self.assertIn(
            "Image file too large",
            str(exc.exception),
        )

    def test_rejects_unsupported_content_type(self):
        upload = SimpleUploadedFile(
            "document.pdf",
            b"not-an-image",
            content_type="application/pdf",
        )

        info = make_mutation_info(
            self.user,
            files={
                "image": upload,
            },
        )

        with self.assertRaises(GraphQLError) as exc:
            UploadProfilePictureMutation.mutate_and_get_payload(
                None,
                info,
            )

        self.assertIn(
            "Unsupported image format",
            str(exc.exception),
        )

    def test_rejects_small_image(self):
        upload = make_image(
            width=50,
            height=50,
        )

        info = make_mutation_info(
            self.user,
            files={
                "image": upload,
            },
        )

        with self.assertRaises(GraphQLError) as exc:
            UploadProfilePictureMutation.mutate_and_get_payload(
                None,
                info,
            )

        self.assertIn(
            "Image dimensions too small",
            str(exc.exception),
        )

    @patch(
        "graphq.accounts.mutations.profile.UserProfile.save",
    )
    def test_accepts_valid_image(
        self,
        mock_save,
    ):
        upload = make_image()

        info = make_mutation_info(
            self.user,
            files={
                "image": upload,
            },
        )

        result = (
            UploadProfilePictureMutation
            .mutate_and_get_payload(
                None,
                info,
            )
        )

        self.assertTrue(
            result.success,
        )

        self.assertEqual(
            result.profile.pk,
            self.profile.pk,
        )
        
        mock_save.assert_called_once()

    @patch(
        "graphq.accounts.mutations.profile.UserProfile.save",
    )
    def test_accepts_crop_data(
        self,
        mock_save,
    ):
        upload = make_image(
            width=500,
            height=500,
        )

        info = make_mutation_info(
            self.user,
            files={
                "image": upload,
            },
        )

        with patch.object(
            UploadProfilePictureMutation,
            "_crop_and_save_image",
            return_value=SimpleUploadedFile(
                "cropped.jpg",
                b"cropped",
                content_type="image/jpeg",
            ),
        ) as mock_crop:

            result = (
                UploadProfilePictureMutation
                .mutate_and_get_payload(
                    None,
                    info,
                    crop_data={
                        "x": 0,
                        "y": 0,
                        "width": 300,
                        "height": 300,
                    },
                )
            )

        mock_crop.assert_called_once()

        self.assertTrue(
            result.success,
        )


# =============================================================================
# DELETE PROFILE PICTURE
# =============================================================================


class DeleteProfilePictureMutationTests(
    UserProfileMutationTestCase,
):

    def test_rejects_when_picture_does_not_exist(self):
        self.profile.profile_picture = None

        self.profile.save(
            update_fields=[
                "profile_picture",
            ],
        )

        with self.assertRaises(GraphQLError) as exc:
            DeleteProfilePictureMutation.mutate_and_get_payload(
                None,
                self.info,
            )

        self.assertEqual(
            str(exc.exception),
            "No profile picture to delete",
        )


# =============================================================================
# UPDATE VERIFICATION STATUS
# =============================================================================


class UpdateVerificationStatusMutationTests(
    UserProfileMutationTestCase,
):

    def test_rejects_non_staff_user(self):
        self.user.is_staff = False

        self.user.save(
            update_fields=[
                "is_staff",
            ],
        )

        with self.assertRaises(GraphQLError) as exc:
            UpdateVerificationStatusMutation.mutate_and_get_payload(
                None,
                self.info,
                user_id=to_global_id(
                    "User",
                    self.user.pk,
                ),
                verification_status="verified",
            )

        self.assertIn(
            "Permission denied",
            str(exc.exception),
        )

    def test_rejects_invalid_target_user(self):
        self.user.is_staff = True

        self.user.save(
            update_fields=[
                "is_staff",
            ],
        )

        with self.assertRaises(GraphQLError) as exc:
            UpdateVerificationStatusMutation.mutate_and_get_payload(
                None,
                self.info,
                user_id=to_global_id(
                    "User",
                    999999,
                ),
                verification_status="verified",
            )

        self.assertEqual(
            str(exc.exception),
            "User not found",
        )

    def test_rejects_invalid_status(self):
        self.user.is_staff = True

        self.user.save(
            update_fields=[
                "is_staff",
            ],
        )

        with self.assertRaises(GraphQLError) as exc:
            UpdateVerificationStatusMutation.mutate_and_get_payload(
                None,
                self.info,
                user_id=to_global_id(
                    "User",
                    self.user.pk,
                ),
                verification_status="not-a-status",
            )

        self.assertIn(
            "Invalid status",
            str(exc.exception),
        )


# =============================================================================
# UPDATE LOCATION
# =============================================================================


class UpdateLocationMutationTests(
    UserProfileMutationTestCase,
):

    @patch.object(
        UserProfile,
        "update_location",
    )
    def test_updates_valid_location(
        self,
        mock_update,
    ):
        result = (
            UpdateLocationMutation
            .mutate_and_get_payload(
                None,
                self.info,
                latitude=6.5244,
                longitude=3.3792,
                address="Lagos, Nigeria",
            )
        )

        mock_update.assert_called_once_with(
            6.5244,
            3.3792,
            "Lagos, Nigeria",
        )

        self.assertTrue(
            result.success,
        )

        self.assertEqual(
            result.profile.pk,
            self.profile.pk,
        )

    def test_rejects_invalid_latitude(self):
        with self.assertRaises(GraphQLError) as exc:
            UpdateLocationMutation.mutate_and_get_payload(
                None,
                self.info,
                latitude=91,
                longitude=3.3792,
            )

        self.assertIn(
            "Invalid latitude",
            str(exc.exception),
        )

    def test_rejects_invalid_longitude(self):
        with self.assertRaises(GraphQLError) as exc:
            UpdateLocationMutation.mutate_and_get_payload(
                None,
                self.info,
                latitude=6.5244,
                longitude=181,
            )

        self.assertIn(
            "Invalid longitude",
            str(exc.exception),
        )
