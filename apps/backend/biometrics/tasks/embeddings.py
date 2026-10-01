"""
Biometric background tasks.

Ownership:
    biometrics

These tasks handle asynchronous biometric processing and persistence.
Accounts must not own biometric processing.
"""

import logging
import os

from celery import shared_task
from django.db import transaction

from biometrics.models import FaceEncoding, FaceVerificationImage
from biometrics.processing import ArcFaceModel
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def create_and_store_embedding(
    self,
    user_id,
    profile_image_id,
    image_path,
    set_as_primary=True,
    use_gpu=False,
):
    """
    Generate a face embedding from a verification image.

    The task:

    1. Runs face detection/embedding.
    2. Stores the FaceEncoding.
    3. Marks the source image as face-detected.
    4. Optionally makes the new encoding the active encoding.
    5. Removes the temporary local image.

    Args:
        user_id:
            ID of the accounts.User.

        profile_image_id:
            ID of biometrics.FaceVerificationImage.

        image_path:
            Temporary/local image path.

        set_as_primary:
            Whether the generated encoding becomes active.

        use_gpu:
            Whether GPU processing should be requested.
    """

    try:
        embedding, detection = (
            ArcFaceModel.get_embedding_and_detection(
                image_path,
                use_gpu=use_gpu,
            )
        )

        with transaction.atomic():

            user = User.objects.get(pk=user_id)

            profile_image = (
                FaceVerificationImage.objects
                .select_for_update()
                .get(pk=profile_image_id)
            )

            encoding = FaceEncoding.create_from_embedding(
                user=user,
                embedding=embedding,
                source_image=profile_image,
                is_active=set_as_primary,
                metadata={
                    "detection": detection,
                },
            )

            if set_as_primary:
                (
                    FaceEncoding.objects
                    .filter(user_id=user_id)
                    .exclude(pk=encoding.pk)
                    .update(is_active=False)
                )

            profile_image.face_detected = True
            profile_image.face_count = 1
            profile_image.metadata = {
                **(profile_image.metadata or {}),
                "detection": detection,
            }

            profile_image.save(
                update_fields=[
                    "face_detected",
                    "face_count",
                    "metadata",
                ]
            )

        return {
            "status": "ok",
            "encoding_id": encoding.pk,
        }

    except FaceVerificationImage.DoesNotExist:
        logger.error(
            "Face verification image %s does not exist.",
            profile_image_id,
        )
        raise

    except Exception as exc:
        logger.exception(
            "Embedding task failed for user %s: %s",
            user_id,
            exc,
        )
        raise self.retry(exc=exc)

    finally:
        if image_path and os.path.exists(image_path):
            try:
                os.unlink(image_path)
            except OSError:
                logger.exception(
                    "Failed to delete temporary image: %s",
                    image_path,
                )