# apps/backend/biometrics/tasks/images.py

from io import BytesIO
import logging

from celery import shared_task
from django.core.files.base import ContentFile
from PIL import Image

from biometrics.models import FaceVerificationImage

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
)
def process_profile_image_upload(self, image_id):
    """
    Process a FaceVerificationImage after upload.

    Generates a 300x300 thumbnail and stores it on the
    biometric image record.
    """
    try:
        profile_image = FaceVerificationImage.objects.get(
            pk=image_id
        )

        if not profile_image.image:
            raise ValueError(
                f"FaceVerificationImage {image_id} has no image."
            )

        with Image.open(profile_image.image) as img:
            img.thumbnail((300, 300))

            # JPEG does not support RGBA/P mode reliably.
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            thumb_io = BytesIO()

            img.save(
                thumb_io,
                format="JPEG",
                quality=85,
                optimize=True,
            )

            thumbnail_name = (
                f"thumb_{profile_image.pk}.jpg"
            )

            profile_image.thumbnail.save(
                thumbnail_name,
                ContentFile(thumb_io.getvalue()),
                save=False,
            )

            profile_image.save(
                update_fields=["thumbnail"]
            )

        logger.info(
            "Processed biometric profile image %s",
            image_id,
        )

        return {
            "status": "ok",
            "image_id": image_id,
        }

    except FaceVerificationImage.DoesNotExist:
        logger.error(
            "FaceVerificationImage %s does not exist",
            image_id,
        )
        raise

    except Exception as exc:
        logger.exception(
            "Failed to process biometric image %s",
            image_id,
        )
        raise self.retry(
            exc=exc,
            countdown=120,
        )