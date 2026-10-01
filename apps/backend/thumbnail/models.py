# apps/backend/thumbnail/models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from . import THUMBNAIL_SIZES, ThumbnailFormat


# ============================================================================
# Optional model imports
# ============================================================================

try:
    from ecommerce.models.product import Category, Collection, ProductMedia

    PRODUCT_AVAILABLE = True
except ImportError:
    try:
        from product.models import Category, Collection, ProductMedia

        PRODUCT_AVAILABLE = True
    except ImportError:
        Category = None
        Collection = None
        ProductMedia = None
        PRODUCT_AVAILABLE = False


try:
    from realestate.models import ListingImage

    REALESTATE_AVAILABLE = True
except ImportError:
    ListingImage = None
    REALESTATE_AVAILABLE = False


try:
    from social.models import VideoContent

    SOCIAL_AVAILABLE = True
except ImportError:
    VideoContent = None
    SOCIAL_AVAILABLE = False


# ============================================================================
# Validators
# ============================================================================

def validate_thumbnail_size(size: int):
    """Validate that the thumbnail size is one of the supported sizes."""

    if size not in THUMBNAIL_SIZES:
        available_sizes = [str(value) for value in THUMBNAIL_SIZES]

        raise ValidationError(
            f"Only the following sizes are available: "
            f"{', '.join(available_sizes)}."
        )


# ============================================================================
# Thumbnail
# ============================================================================

class Thumbnail(models.Model):
    """
    Thumbnail model for generated and stored image thumbnails.

    A thumbnail may belong to one of the supported domain objects:

    - Ecommerce category
    - Ecommerce collection
    - Ecommerce product media
    - User
    - Real-estate listing image
    - Social/video content
    - Generic Django content type
    """

    # ------------------------------------------------------------------------
    # Thumbnail file
    # ------------------------------------------------------------------------

    image = models.ImageField(
        upload_to="thumbnails",
        help_text="The thumbnail image file.",
    )

    size = models.PositiveIntegerField(
        validators=[validate_thumbnail_size],
        help_text="Thumbnail size in pixels.",
    )

    format = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        choices=ThumbnailFormat.CHOICES,
        help_text="Thumbnail format, for example JPEG, PNG, or WebP.",
    )

    # ------------------------------------------------------------------------
    # Ecommerce relations
    # ------------------------------------------------------------------------

    category = (
        models.ForeignKey(
            Category,
            null=True,
            blank=True,
            on_delete=models.CASCADE,
            related_name="thumbnails",
            help_text="Category this thumbnail belongs to.",
        )
        if PRODUCT_AVAILABLE
        else None
    )

    collection = (
        models.ForeignKey(
            Collection,
            null=True,
            blank=True,
            on_delete=models.CASCADE,
            related_name="thumbnails",
            help_text="Collection this thumbnail belongs to.",
        )
        if PRODUCT_AVAILABLE
        else None
    )

    product_media = (
        models.ForeignKey(
            ProductMedia,
            null=True,
            blank=True,
            on_delete=models.CASCADE,
            related_name="thumbnails",
            help_text="Product media this thumbnail belongs to.",
        )
        if PRODUCT_AVAILABLE
        else None
    )

    # ------------------------------------------------------------------------
    # User relation
    # ------------------------------------------------------------------------

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="thumbnails",
        help_text="User this thumbnail belongs to.",
    )

    # ------------------------------------------------------------------------
    # Real-estate relation
    # ------------------------------------------------------------------------

    listing_image = (
        models.ForeignKey(
            ListingImage,
            null=True,
            blank=True,
            on_delete=models.CASCADE,
            related_name="thumbnails",
            help_text="Listing image this thumbnail belongs to.",
        )
        if REALESTATE_AVAILABLE
        else None
    )

    # ------------------------------------------------------------------------
    # Social/video relation
    # ------------------------------------------------------------------------

    video = (
        models.ForeignKey(
            VideoContent,
            null=True,
            blank=True,
            on_delete=models.CASCADE,
            related_name="video_thumbnails",
            help_text="Video content this thumbnail belongs to.",
        )
        if SOCIAL_AVAILABLE
        else None
    )

    # ------------------------------------------------------------------------
    # Generic relation
    # ------------------------------------------------------------------------

    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Content type of the related object.",
    )

    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID of the related object.",
    )

    # ------------------------------------------------------------------------
    # Image metadata
    # ------------------------------------------------------------------------

    width = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Actual width of the thumbnail.",
    )

    height = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Actual height of the thumbnail.",
    )

    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes.",
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type of the thumbnail.",
    )

    # ------------------------------------------------------------------------
    # Audit fields
    # ------------------------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="thumbnails_created",
        help_text="User who created this thumbnail.",
    )

    # ------------------------------------------------------------------------
    # Model metadata
    # ------------------------------------------------------------------------

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["size"],
                name="thumbnail_size_idx",
            ),
            models.Index(
                fields=["format"],
                name="thumbnail_format_idx",
            ),
            models.Index(
                fields=["created_at"],
                name="thumbnail_created_idx",
            ),
            models.Index(
                fields=["user", "size"],
                name="thumbnail_user_size_idx",
            ),
            models.Index(
                fields=["content_type", "object_id"],
                name="thumbnail_generic_idx",
            ),
        ]

        if SOCIAL_AVAILABLE:
            indexes.append(
                models.Index(
                    fields=["video", "size"],
                    name="thumbnail_video_size_idx",
                )
            )

        if PRODUCT_AVAILABLE:
            indexes.append(
                models.Index(
                    fields=["product_media", "size"],
                    name="thumb_product_media_size_idx",
                )
            )

        verbose_name = "Thumbnail"
        verbose_name_plural = "Thumbnails"

    # ------------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------------

    def __str__(self):
        related_name = "Unknown"

        if self.category and PRODUCT_AVAILABLE:
            related_name = f"Category: {self.category.name}"

        elif self.collection and PRODUCT_AVAILABLE:
            related_name = f"Collection: {self.collection.name}"

        elif self.product_media and PRODUCT_AVAILABLE:
            related_name = f"Product Media: {self.product_media.id}"

        elif self.user:
            related_name = f"User: {self.user.email}"

        elif self.listing_image and REALESTATE_AVAILABLE:
            related_name = f"Listing Image: {self.listing_image.id}"

        elif self.video and SOCIAL_AVAILABLE:
            related_name = f"Video: {self.video.id}"

        elif self.content_type and self.object_id:
            related_name = (
                f"{self.content_type.model}: {self.object_id}"
            )

        return f"Thumbnail ({self.size}px) - {related_name}"

    # ------------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------------

    def clean(self):
        """Validate thumbnail data."""

        relations = [
            self.category if PRODUCT_AVAILABLE else None,
            self.collection if PRODUCT_AVAILABLE else None,
            self.product_media if PRODUCT_AVAILABLE else None,
            self.user,
            self.listing_image if REALESTATE_AVAILABLE else None,
            self.video if SOCIAL_AVAILABLE else None,
            (
                self.content_type
                if self.content_type and self.object_id
                else None
            ),
        ]

        if not any(relations):
            raise ValidationError(
                "Thumbnail must be associated with at least one object "
                "(category, collection, product_media, user, listing_image, "
                "video, or generic relation)."
            )

        if self.size and self.size not in THUMBNAIL_SIZES:
            raise ValidationError(
                {
                    "size": (
                        f"Size {self.size} is not allowed. "
                        f"Allowed sizes: {THUMBNAIL_SIZES}"
                    )
                }
            )

    # ------------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------------

    def save(self, *args, **kwargs):
        """Validate and save the thumbnail."""

        self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------------
    # Related object
    # ------------------------------------------------------------------------

    def get_related_object(self):
        """
        Return the primary object associated with this thumbnail.

        Returns:
            Model instance or None.
        """

        if self.category and PRODUCT_AVAILABLE:
            return self.category

        if self.collection and PRODUCT_AVAILABLE:
            return self.collection

        if self.product_media and PRODUCT_AVAILABLE:
            return self.product_media

        if self.user:
            return self.user

        if self.listing_image and REALESTATE_AVAILABLE:
            return self.listing_image

        if self.video and SOCIAL_AVAILABLE:
            return self.video

        if self.content_type and self.object_id:
            try:
                return self.content_type.get_object_for_this_type(
                    id=self.object_id
                )
            except Exception:
                return None

        return None

    # ------------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------------

    def get_thumbnail_url(self):
        """Return the URL of the thumbnail file."""

        if self.image:
            return self.image.url

        return None

    def get_thumbnail_path(self):
        """Return the filesystem path of the thumbnail file."""

        if self.image:
            return self.image.path

        return None