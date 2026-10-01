# apps/backend/graphq/accounts/mutations/profile.py

import io
import logging
import time

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from graphql import GraphQLError
from graphql_relay import from_global_id
from graphene import (
    Boolean,
    Field,
    Float,
    ID,
    String,
    relay,
)
from graphene.types.generic import GenericScalar
from PIL import Image

from accounts.models.profile import UserProfile
from accounts.update_user import update_user_and_profile
from graphq.accounts.types import UserNode, UserProfileNode
from univa_jwt.decorators import login_required


User = get_user_model()

logger = logging.getLogger(__name__)


# ============================================================================
# MUTATIONS
# ============================================================================

class UpdateUserAndProfileMutation(relay.ClientIDMutation):
    """
    Unified mutation to update both User and Profile fields.
    """

    class Input:
        first_name = graphene.String()
        last_name = graphene.String()
        email = graphene.String()
        phone_number = graphene.String()

        date_of_birth = graphene.Date()
        gender = graphene.String()
        bio = graphene.String()
        website = graphene.String()
        company_name = graphene.String()
        univa_id = graphene.String()
        language_code = graphene.String()
        preferred_notification_method = graphene.String()
        is_business = graphene.Boolean()

    user = graphene.Field(UserNode)
    profile = graphene.Field(UserProfileNode)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        user_fields = ['first_name', 'last_name', 'email', 'phone_number']
        user_data = {k: input[k] for k in user_fields if k in input}

        profile_fields = [
            'date_of_birth', 'gender', 'bio', 'website', 'company_name',
            'univa_id', 'language_code', 'preferred_notification_method',
            'is_business',
        ]
        profile_data = {k: input[k] for k in profile_fields if k in input}

        if profile_data.get('univa_id'):
            univa_id = profile_data['univa_id']
            if UserProfile.objects.filter(
                univa_id=univa_id
            ).exclude(user=user).exists():
                raise GraphQLError("This Univa ID is already taken")

        if profile_data.get('gender'):
            valid_genders = ['male', 'female', 'other', 'prefer_not_to_say']
            if profile_data['gender'] not in valid_genders:
                raise GraphQLError(
                    f"Invalid gender. Must be one of: {', '.join(valid_genders)}"
                )

        if profile_data.get('preferred_notification_method'):
            valid_methods = ['email', 'sms', 'push', 'whatsapp']
            if profile_data['preferred_notification_method'] not in valid_methods:
                raise GraphQLError(
                    f"Invalid notification method. Must be one of: {', '.join(valid_methods)}"
                )

        try:
            updated_user, updated_profile = update_user_and_profile(
                user, user_data, profile_data
            )
        except Exception as e:
            raise GraphQLError(str(e))

        return cls(user=updated_user, profile=updated_profile)


class UploadProfilePictureMutation(relay.ClientIDMutation):
    """Upload or update user profile picture with optional cropping."""

    class Input:
        crop_data = GenericScalar(required=False)

    profile = Field(UserProfileNode)
    success = Boolean()
    image_url = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        uploaded_file = (
            info.context.FILES.get('image')
            or info.context.FILES.get('profile_picture')
        )
        if not uploaded_file:
            raise GraphQLError("No image file provided")

        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        if uploaded_file.size > MAX_FILE_SIZE:
            raise GraphQLError(
                f"Image file too large. "
                f"Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB"
            )

        ALLOWED_TYPES = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif',
        ]
        if uploaded_file.content_type not in ALLOWED_TYPES:
            raise GraphQLError(
                f"Unsupported image format. "
                f"Allowed formats: {', '.join(ALLOWED_TYPES)}"
            )

        # -------------------------------------------------------------------
        # Read the upload into memory ONCE, before anything can close the
        # underlying file handle. Everything downstream works on bytes.
        # -------------------------------------------------------------------
        file_bytes = uploaded_file.read()
        file_name = uploaded_file.name
        content_type = uploaded_file.content_type

        # Validate dimensions against an in-memory buffer, not the upload.
        try:
            image = Image.open(io.BytesIO(file_bytes))
            width, height = image.size

            if width < 100 or height < 100:
                raise GraphQLError(
                    "Image dimensions too small. Minimum 100x100 pixels"
                )

            MAX_DIMENSION = 4096
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                raise GraphQLError(
                    f"Image dimensions too large. "
                    f"Maximum {MAX_DIMENSION}x{MAX_DIMENSION} pixels"
                )

            image.close()
        except GraphQLError:
            raise
        except Exception as e:
            raise GraphQLError(f"Invalid image file: {str(e)}")

        try:
            crop_data = input.get('crop_data')
            if crop_data:
                profile.profile_picture = cls._crop_and_save_image_bytes(
                    file_bytes, content_type, crop_data, user
                )
            else:
                profile.profile_picture = ContentFile(
                    file_bytes,
                    name=file_name,
                )

            profile.save(update_fields=['profile_picture'])

            image_url = (
                profile.profile_picture.url
                if profile.profile_picture else None
            )

            logger.info(f"Profile photo uploaded for user: {user.id}")

            return cls(
                profile=profile,
                success=True,
                image_url=image_url,
            )

        except Exception as e:
            logger.exception(
                f"Failed to upload profile picture for user {user.id}"
            )
            raise GraphQLError(f"Failed to upload image: {str(e)}")

    @classmethod
    def _crop_and_save_image_bytes(cls, file_bytes, content_type, crop_data, user):
        """
        Crop image from in-memory bytes and return a ContentFile.

        crop_data format:
            {'x': int, 'y': int, 'width': int, 'height': int,
             'rotate': float (optional)}
        """
        try:
            image = Image.open(io.BytesIO(file_bytes))

            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(
                    image,
                    mask=image.split()[-1] if image.mode == 'RGBA' else None,
                )
                image = background

            if crop_data.get('rotate'):
                image = image.rotate(float(crop_data['rotate']), expand=True)

            x = int(crop_data.get('x', 0))
            y = int(crop_data.get('y', 0))
            width = int(crop_data.get('width', image.width))
            height = int(crop_data.get('height', image.height))

            x = max(0, min(x, image.width - 1))
            y = max(0, min(y, image.height - 1))
            width = min(width, image.width - x)
            height = min(height, image.height - y)

            MIN_SIZE = 100
            if width < MIN_SIZE or height < MIN_SIZE:
                aspect_ratio = width / height if height > 0 else 1.0
                if width < MIN_SIZE:
                    width = MIN_SIZE
                    height = (
                        int(width / aspect_ratio)
                        if aspect_ratio > 0 else MIN_SIZE
                    )
                if height < MIN_SIZE:
                    height = MIN_SIZE
                    width = (
                        int(height * aspect_ratio)
                        if aspect_ratio > 0 else MIN_SIZE
                    )
                x = max(0, min(x, image.width - width))
                y = max(0, min(y, image.height - height))

            cropped_image = image.crop((x, y, x + width, y + height))
            cropped_image.thumbnail(
                (1200, 1200), Image.Resampling.LANCZOS
            )

            image_io = io.BytesIO()

            format_map = {
                'image/png': ('PNG', 90),
                'image/webp': ('WEBP', 85),
                'image/jpeg': ('JPEG', 85),
                'image/jpg': ('JPEG', 85),
            }
            fmt, quality = format_map.get(content_type, ('JPEG', 85))

            cropped_image.save(
                image_io, format=fmt, quality=quality, optimize=True
            )

            new_name = f"{user.id}_profile_{int(time.time())}.{fmt.lower()}"
            return ContentFile(image_io.getvalue(), name=new_name)

        except Exception as e:
            logger.error(f"Image cropping failed: {str(e)}")
            # Fall back to the original bytes
            return ContentFile(
                file_bytes,
                name=f"{user.id}_profile_original.jpg",
            )


class DeleteProfilePictureMutation(relay.ClientIDMutation):
    """Delete user's profile picture."""

    class Input:
        pass

    success = Boolean()
    profile = Field(UserProfileNode)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            raise GraphQLError("User profile not found")

        if not profile.profile_picture:
            raise GraphQLError("No profile picture to delete")

        profile.profile_picture.delete(save=False)
        profile.profile_picture = None
        profile.save(update_fields=['profile_picture'])

        logger.info(f"Profile picture deleted for user: {user.id}")

        return cls(success=True, profile=profile)


class UpdateVerificationStatusMutation(relay.ClientIDMutation):
    """Update user's verification status (admin only)."""

    class Input:
        user_id = ID(required=True)
        verification_status = String(required=True)

    success = Boolean()
    user = Field(UserNode)
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_staff:
            raise GraphQLError("Permission denied. Admin access required.")

        try:
            _, target_user_id = from_global_id(input['user_id'])
            target_user = User.objects.get(id=target_user_id)
        except (ValueError, TypeError, User.DoesNotExist):
            raise GraphQLError("User not found")

        status = input['verification_status']
        valid_statuses = dict(UserProfile.VERIFICATION_STATUS_CHOICES)

        if status not in valid_statuses:
            raise GraphQLError(
                f"Invalid status. "
                f"Must be one of: {', '.join(valid_statuses.keys())}"
            )

        try:
            profile = target_user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=target_user)

        try:
            profile.verify(status, verified_by=user)
        except ValidationError as e:
            raise GraphQLError(str(e))

        return cls(
            success=True,
            user=target_user,
            message=f"Verification status updated to: {valid_statuses[status]}",
        )


class UpdateLocationMutation(relay.ClientIDMutation):
    """Update user's current location."""

    class Input:
        latitude = Float(required=True)
        longitude = Float(required=True)
        address = String()

    success = Boolean()
    profile = Field(UserProfileNode)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        latitude = input.get('latitude')
        longitude = input.get('longitude')
        address = input.get('address')

        if not (-90 <= latitude <= 90):
            raise GraphQLError("Invalid latitude. Must be between -90 and 90.")

        if not (-180 <= longitude <= 180):
            raise GraphQLError(
                "Invalid longitude. Must be between -180 and 180."
            )

        try:
            profile.update_location(latitude, longitude, address)
        except Exception as e:
            raise GraphQLError(f"Failed to update location: {str(e)}")

        return cls(success=True, profile=profile)


# ============================================================================
# REGISTRATION
# ============================================================================

class UserProfileMutations(graphene.ObjectType):
    """All user profile-related mutations."""

    update_user_and_profile = UpdateUserAndProfileMutation.Field()
    upload_profile_picture = UploadProfilePictureMutation.Field()
    delete_profile_picture = DeleteProfilePictureMutation.Field()
    update_verification_status = UpdateVerificationStatusMutation.Field()
    update_location = UpdateLocationMutation.Field()