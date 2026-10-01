'''import graphene
from django.db.models import Q
from django.utils import timezone
from graphql.accounts.types import UserNode
from graphql.product.types import (CategoryNode, CollectionNode,
                                   ProductMediaNode)
from graphql.subscriptions.subscription import Subscription
from graphql.thumbnail.types import ThumbnailNode
from graphql_relay import from_global_id

from product.models import Category, Collection, ProductMedia
from thumbnail.models import Thumbnail

from . import ThumbnailFormat

# ----------------------------------------------------------------------
# 🖼️ THUMBNAIL SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnThumbnailCreated(Subscription):
    class Arguments:
        category_id = graphene.ID(required=False)
        collection_id = graphene.ID(required=False)
        product_media_id = graphene.ID(required=False)
        user_id = graphene.ID(required=False)

    thumbnail = graphene.Field(ThumbnailNode)
    category = graphene.Field(CategoryNode)
    collection = graphene.Field(CollectionNode)
    product_media = graphene.Field(ProductMediaNode)
    user = graphene.Field(UserNode)
    size = graphene.Int()
    format = graphene.String()
    created_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, category_id=None, collection_id=None, product_media_id=None, user_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if category_id:
            real_id = from_global_id(category_id)[1]
            # Subscribe to thumbnails for specific category
            return [f"category_thumbnails_{real_id}"]
        
        elif collection_id:
            real_id = from_global_id(collection_id)[1]
            # Subscribe to thumbnails for specific collection
            return [f"collection_thumbnails_{real_id}"]
        
        elif product_media_id:
            real_id = from_global_id(product_media_id)[1]
            # Subscribe to thumbnails for specific product media
            return [f"product_media_thumbnails_{real_id}"]
        
        elif user_id:
            real_id = from_global_id(user_id)[1]
            # Subscribe to thumbnails for specific user
            if str(user.id) == real_id or user.has_perm('thumbnail.manage_thumbnails'):
                return [f"user_thumbnails_{real_id}"]
            else:
                raise Exception("Not authorized")
        
        else:
            # Staff can subscribe to all thumbnail creations
            if user.has_perm('thumbnail.manage_thumbnails'):
                return [f"all_thumbnails_created"]
            else:
                raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, category_id=None, collection_id=None, product_media_id=None, user_id=None):
        return OnThumbnailCreated(
            thumbnail=payload["thumbnail"],
            category=payload["category"],
            collection=payload["collection"],
            product_media=payload["product_media"],
            user=payload["user"],
            size=payload["size"],
            format=payload["format"],
            created_at=payload["created_at"]
        )

    @classmethod
    def broadcast_for_category(cls, category, thumbnail):
        cls.broadcast_group(
            group=f"category_thumbnails_{category.id}",
            payload={
                "thumbnail": thumbnail,
                "category": category,
                "collection": None,
                "product_media": None,
                "user": thumbnail.user,
                "size": thumbnail.size,
                "format": thumbnail.format,
                "created_at": thumbnail.created_at.isoformat()
            }
        )

    @classmethod
    def broadcast_for_collection(cls, collection, thumbnail):
        cls.broadcast_group(
            group=f"collection_thumbnails_{collection.id}",
            payload={
                "thumbnail": thumbnail,
                "category": None,
                "collection": collection,
                "product_media": None,
                "user": thumbnail.user,
                "size": thumbnail.size,
                "format": thumbnail.format,
                "created_at": thumbnail.created_at.isoformat()
            }
        )

    @classmethod
    def broadcast_for_product_media(cls, product_media, thumbnail):
        cls.broadcast_group(
            group=f"product_media_thumbnails_{product_media.id}",
            payload={
                "thumbnail": thumbnail,
                "category": None,
                "collection": None,
                "product_media": product_media,
                "user": thumbnail.user,
                "size": thumbnail.size,
                "format": thumbnail.format,
                "created_at": thumbnail.created_at.isoformat()
            }
        )

    @classmethod
    def broadcast_for_user(cls, user, thumbnail):
        cls.broadcast_group(
            group=f"user_thumbnails_{user.id}",
            payload={
                "thumbnail": thumbnail,
                "category": thumbnail.category,
                "collection": thumbnail.collection,
                "product_media": thumbnail.product_media,
                "user": user,
                "size": thumbnail.size,
                "format": thumbnail.format,
                "created_at": thumbnail.created_at.isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, thumbnail):
        cls.broadcast_group(
            group="all_thumbnails_created",
            payload={
                "thumbnail": thumbnail,
                "category": thumbnail.category,
                "collection": thumbnail.collection,
                "product_media": thumbnail.product_media,
                "user": thumbnail.user,
                "size": thumbnail.size,
                "format": thumbnail.format,
                "created_at": thumbnail.created_at.isoformat()
            }
        )

class OnThumbnailUpdated(Subscription):
    class Arguments:
        thumbnail_id = graphene.ID(required=True)

    thumbnail = graphene.Field(ThumbnailNode)
    updated_fields = graphene.List(graphene.String)
    old_size = graphene.Int()
    new_size = graphene.Int()
    old_format = graphene.String()
    new_format = graphene.String()
    image_url = graphene.String()
    updated_by = graphene.Field(UserNode)
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, thumbnail_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(thumbnail_id)[1]
        try:
            thumbnail = Thumbnail.objects.get(id=real_id)
            # Check authorization based on thumbnail owner/related object
            if (user.has_perm('thumbnail.manage_thumbnails') or 
                (thumbnail.user and thumbnail.user == user) or
                (thumbnail.category and user.has_perm('product.manage_products')) or
                (thumbnail.collection and user.has_perm('product.manage_products')) or
                (thumbnail.product_media and user.has_perm('product.manage_products'))):
                return [f"thumbnail_updates_{real_id}"]
            else:
                raise Exception("Not authorized to subscribe to this thumbnail")
        except Thumbnail.DoesNotExist:
            raise Exception("Thumbnail not found")

    @staticmethod
    def publish(payload, info, thumbnail_id):
        return OnThumbnailUpdated(
            thumbnail=payload["thumbnail"],
            updated_fields=payload["updated_fields"],
            old_size=payload["old_size"],
            new_size=payload["new_size"],
            old_format=payload["old_format"],
            new_format=payload["new_format"],
            image_url=payload["image_url"],
            updated_by=payload["updated_by"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, thumbnail, updated_fields, old_size, new_size, old_format, new_format, updated_by):
        cls.broadcast_group(
            group=f"thumbnail_updates_{thumbnail.id}",
            payload={
                "thumbnail": thumbnail,
                "updated_fields": updated_fields,
                "old_size": old_size,
                "new_size": new_size,
                "old_format": old_format,
                "new_format": new_format,
                "image_url": thumbnail.image.url if thumbnail.image else "",
                "updated_by": updated_by,
                "updated_at": timezone.now().isoformat()
            }
        )

class OnThumbnailDeleted(Subscription):
    class Arguments:
        category_id = graphene.ID(required=False)
        collection_id = graphene.ID(required=False)
        product_media_id = graphene.ID(required=False)
        user_id = graphene.ID(required=False)

    thumbnail_id = graphene.ID()
    thumbnail_size = graphene.Int()
    thumbnail_format = graphene.String()
    category = graphene.Field(CategoryNode)
    collection = graphene.Field(CollectionNode)
    product_media = graphene.Field(ProductMediaNode)
    user = graphene.Field(UserNode)
    deleted_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, category_id=None, collection_id=None, product_media_id=None, user_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if category_id:
            real_id = from_global_id(category_id)[1]
            return [f"category_thumbnail_deletions_{real_id}"]
        
        elif collection_id:
            real_id = from_global_id(collection_id)[1]
            return [f"collection_thumbnail_deletions_{real_id}"]
        
        elif product_media_id:
            real_id = from_global_id(product_media_id)[1]
            return [f"product_media_thumbnail_deletions_{real_id}"]
        
        elif user_id:
            real_id = from_global_id(user_id)[1]
            if str(user.id) == real_id or user.has_perm('thumbnail.manage_thumbnails'):
                return [f"user_thumbnail_deletions_{real_id}"]
            else:
                raise Exception("Not authorized")
        
        else:
            if user.has_perm('thumbnail.manage_thumbnails'):
                return [f"all_thumbnail_deletions"]
            else:
                raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, category_id=None, collection_id=None, product_media_id=None, user_id=None):
        return OnThumbnailDeleted(
            thumbnail_id=payload["thumbnail_id"],
            thumbnail_size=payload["thumbnail_size"],
            thumbnail_format=payload["thumbnail_format"],
            category=payload["category"],
            collection=payload["collection"],
            product_media=payload["product_media"],
            user=payload["user"],
            deleted_at=payload["deleted_at"]
        )

    @classmethod
    def broadcast_for_category(cls, category, thumbnail):
        cls.broadcast_group(
            group=f"category_thumbnail_deletions_{category.id}",
            payload={
                "thumbnail_id": str(thumbnail.id),
                "thumbnail_size": thumbnail.size,
                "thumbnail_format": thumbnail.format,
                "category": category,
                "collection": None,
                "product_media": None,
                "user": thumbnail.user,
                "deleted_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_for_collection(cls, collection, thumbnail):
        cls.broadcast_group(
            group=f"collection_thumbnail_deletions_{collection.id}",
            payload={
                "thumbnail_id": str(thumbnail.id),
                "thumbnail_size": thumbnail.size,
                "thumbnail_format": thumbnail.format,
                "category": None,
                "collection": collection,
                "product_media": None,
                "user": thumbnail.user,
                "deleted_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_for_product_media(cls, product_media, thumbnail):
        cls.broadcast_group(
            group=f"product_media_thumbnail_deletions_{product_media.id}",
            payload={
                "thumbnail_id": str(thumbnail.id),
                "thumbnail_size": thumbnail.size,
                "thumbnail_format": thumbnail.format,
                "category": None,
                "collection": None,
                "product_media": product_media,
                "user": thumbnail.user,
                "deleted_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_for_user(cls, user, thumbnail):
        cls.broadcast_group(
            group=f"user_thumbnail_deletions_{user.id}",
            payload={
                "thumbnail_id": str(thumbnail.id),
                "thumbnail_size": thumbnail.size,
                "thumbnail_format": thumbnail.format,
                "category": thumbnail.category,
                "collection": thumbnail.collection,
                "product_media": thumbnail.product_media,
                "user": user,
                "deleted_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, thumbnail):
        cls.broadcast_group(
            group="all_thumbnail_deletions",
            payload={
                "thumbnail_id": str(thumbnail.id),
                "thumbnail_size": thumbnail.size,
                "thumbnail_format": thumbnail.format,
                "category": thumbnail.category,
                "collection": thumbnail.collection,
                "product_media": thumbnail.product_media,
                "user": thumbnail.user,
                "deleted_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# 🔄 THUMBNAIL GENERATION SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnThumbnailGenerationStarted(Subscription):
    class Arguments:
        category_id = graphene.ID(required=False)
        collection_id = graphene.ID(required=False)
        product_media_id = graphene.ID(required=False)

    category = graphene.Field(CategoryNode)
    collection = graphene.Field(CollectionNode)
    product_media = graphene.Field(ProductMediaNode)
    sizes = graphene.List(graphene.Int)
    formats = graphene.List(graphene.String)
    started_by = graphene.Field(UserNode)
    started_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, category_id=None, collection_id=None, product_media_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('thumbnail.manage_thumbnails'):
            if category_id:
                real_id = from_global_id(category_id)[1]
                return [f"category_thumbnail_generation_{real_id}"]
            elif collection_id:
                real_id = from_global_id(collection_id)[1]
                return [f"collection_thumbnail_generation_{real_id}"]
            elif product_media_id:
                real_id = from_global_id(product_media_id)[1]
                return [f"product_media_thumbnail_generation_{real_id}"]
            else:
                return [f"all_thumbnail_generation"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, category_id=None, collection_id=None, product_media_id=None):
        return OnThumbnailGenerationStarted(
            category=payload["category"],
            collection=payload["collection"],
            product_media=payload["product_media"],
            sizes=payload["sizes"],
            formats=payload["formats"],
            started_by=payload["started_by"],
            started_at=payload["started_at"]
        )

    @classmethod
    def broadcast_for_category(cls, category, sizes, formats, started_by):
        cls.broadcast_group(
            group=f"category_thumbnail_generation_{category.id}",
            payload={
                "category": category,
                "collection": None,
                "product_media": None,
                "sizes": sizes,
                "formats": formats,
                "started_by": started_by,
                "started_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_for_collection(cls, collection, sizes, formats, started_by):
        cls.broadcast_group(
            group=f"collection_thumbnail_generation_{collection.id}",
            payload={
                "category": None,
                "collection": collection,
                "product_media": None,
                "sizes": sizes,
                "formats": formats,
                "started_by": started_by,
                "started_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_for_product_media(cls, product_media, sizes, formats, started_by):
        cls.broadcast_group(
            group=f"product_media_thumbnail_generation_{product_media.id}",
            payload={
                "category": None,
                "collection": None,
                "product_media": product_media,
                "sizes": sizes,
                "formats": formats,
                "started_by": started_by,
                "started_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, sizes, formats, started_by):
        cls.broadcast_group(
            group="all_thumbnail_generation",
            payload={
                "category": None,
                "collection": None,
                "product_media": None,
                "sizes": sizes,
                "formats": formats,
                "started_by": started_by,
                "started_at": timezone.now().isoformat()
            }
        )

class OnThumbnailGenerationCompleted(Subscription):
    class Arguments:
        category_id = graphene.ID(required=False)
        collection_id = graphene.ID(required=False)
        product_media_id = graphene.ID(required=False)

    category = graphene.Field(CategoryNode)
    collection = graphene.Field(CollectionNode)
    product_media = graphene.Field(ProductMediaNode)
    generated_thumbnails = graphene.List(ThumbnailNode)
    total_generated = graphene.Int()
    failed_generations = graphene.Int()
    completed_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, category_id=None, collection_id=None, product_media_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('thumbnail.manage_thumbnails'):
            if category_id:
                real_id = from_global_id(category_id)[1]
                return [f"category_thumbnail_completion_{real_id}"]
            elif collection_id:
                real_id = from_global_id(collection_id)[1]
                return [f"collection_thumbnail_completion_{real_id}"]
            elif product_media_id:
                real_id = from_global_id(product_media_id)[1]
                return [f"product_media_thumbnail_completion_{real_id}"]
            else:
                return [f"all_thumbnail_completion"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, category_id=None, collection_id=None, product_media_id=None):
        return OnThumbnailGenerationCompleted(
            category=payload["category"],
            collection=payload["collection"],
            product_media=payload["product_media"],
            generated_thumbnails=payload["generated_thumbnails"],
            total_generated=payload["total_generated"],
            failed_generations=payload["failed_generations"],
            completed_at=payload["completed_at"]
        )

    @classmethod
    def broadcast_for_category(cls, category, generated_thumbnails, failed_generations):
        cls.broadcast_group(
            group=f"category_thumbnail_completion_{category.id}",
            payload={
                "category": category,
                "collection": None,
                "product_media": None,
                "generated_thumbnails": generated_thumbnails,
                "total_generated": len(generated_thumbnails),
                "failed_generations": failed_generations,
                "completed_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_for_collection(cls, collection, generated_thumbnails, failed_generations):
        cls.broadcast_group(
            group=f"collection_thumbnail_completion_{collection.id}",
            payload={
                "category": None,
                "collection": collection,
                "product_media": None,
                "generated_thumbnails": generated_thumbnails,
                "total_generated": len(generated_thumbnails),
                "failed_generations": failed_generations,
                "completed_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_for_product_media(cls, product_media, generated_thumbnails, failed_generations):
        cls.broadcast_group(
            group=f"product_media_thumbnail_completion_{product_media.id}",
            payload={
                "category": None,
                "collection": None,
                "product_media": product_media,
                "generated_thumbnails": generated_thumbnails,
                "total_generated": len(generated_thumbnails),
                "failed_generations": failed_generations,
                "completed_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, generated_thumbnails, failed_generations):
        cls.broadcast_group(
            group="all_thumbnail_completion",
            payload={
                "category": None,
                "collection": None,
                "product_media": None,
                "generated_thumbnails": generated_thumbnails,
                "total_generated": len(generated_thumbnails),
                "failed_generations": failed_generations,
                "completed_at": timezone.now().isoformat()
            }
        )

class OnThumbnailGenerationFailed(Subscription):
    class Arguments:
        category_id = graphene.ID(required=False)
        collection_id = graphene.ID(required=False)
        product_media_id = graphene.ID(required=False)

    category = graphene.Field(CategoryNode)
    collection = graphene.Field(CollectionNode)
    product_media = graphene.Field(ProductMediaNode)
    error_message = graphene.String()
    failed_size = graphene.Int()
    failed_format = graphene.String()
    failed_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, category_id=None, collection_id=None, product_media_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('thumbnail.manage_thumbnails'):
            if category_id:
                real_id = from_global_id(category_id)[1]
                return [f"category_thumbnail_failures_{real_id}"]
            elif collection_id:
                real_id = from_global_id(collection_id)[1]
                return [f"collection_thumbnail_failures_{real_id}"]
            elif product_media_id:
                real_id = from_global_id(product_media_id)[1]
                return [f"product_media_thumbnail_failures_{real_id}"]
            else:
                return [f"all_thumbnail_failures"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, category_id=None, collection_id=None, product_media_id=None):
        return OnThumbnailGenerationFailed(
            category=payload["category"],
            collection=payload["collection"],
            product_media=payload["product_media"],
            error_message=payload["error_message"],
            failed_size=payload["failed_size"],
            failed_format=payload["failed_format"],
            failed_at=payload["failed_at"]
        )

    @classmethod
    def broadcast_for_category(cls, category, error_message, failed_size, failed_format):
        cls.broadcast_group(
            group=f"category_thumbnail_failures_{category.id}",
            payload={
                "category": category,
                "collection": None,
                "product_media": None,
                "error_message": error_message,
                "failed_size": failed_size,
                "failed_format": failed_format,
                "failed_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_for_collection(cls, collection, error_message, failed_size, failed_format):
        cls.broadcast_group(
            group=f"collection_thumbnail_failures_{collection.id}",
            payload={
                "category": None,
                "collection": collection,
                "product_media": None,
                "error_message": error_message,
                "failed_size": failed_size,
                "failed_format": failed_format,
                "failed_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_for_product_media(cls, product_media, error_message, failed_size, failed_format):
        cls.broadcast_group(
            group=f"product_media_thumbnail_failures_{product_media.id}",
            payload={
                "category": None,
                "collection": None,
                "product_media": product_media,
                "error_message": error_message,
                "failed_size": failed_size,
                "failed_format": failed_format,
                "failed_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, error_message, failed_size, failed_format):
        cls.broadcast_group(
            group="all_thumbnail_failures",
            payload={
                "category": None,
                "collection": None,
                "product_media": None,
                "error_message": error_message,
                "failed_size": failed_size,
                "failed_format": failed_format,
                "failed_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# 📊 THUMBNAIL ANALYTICS SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnThumbnailStorageUpdated(Subscription):
    class Arguments:
        timeframe = graphene.String(required=False)  # 'daily', 'weekly', 'monthly'

    metrics = graphene.JSONString()
    timeframe = graphene.String()
    total_thumbnails = graphene.Int()
    total_storage_size = graphene.String()
    thumbnails_by_format = graphene.JSONString()
    thumbnails_by_size = graphene.JSONString()
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, timeframe=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('thumbnail.manage_thumbnails'):
            if timeframe:
                return [f"thumbnail_storage_{timeframe}"]
            else:
                return [f"all_thumbnail_storage"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, timeframe=None):
        return OnThumbnailStorageUpdated(
            metrics=payload["metrics"],
            timeframe=payload["timeframe"],
            total_thumbnails=payload["total_thumbnails"],
            total_storage_size=payload["total_storage_size"],
            thumbnails_by_format=payload["thumbnails_by_format"],
            thumbnails_by_size=payload["thumbnails_by_size"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast_for_timeframe(cls, timeframe, metrics, total_thumbnails, total_storage_size, thumbnails_by_format, thumbnails_by_size):
        cls.broadcast_group(
            group=f"thumbnail_storage_{timeframe}",
            payload={
                "metrics": metrics,
                "timeframe": timeframe,
                "total_thumbnails": total_thumbnails,
                "total_storage_size": str(total_storage_size),
                "thumbnails_by_format": thumbnails_by_format,
                "thumbnails_by_size": thumbnails_by_size,
                "updated_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, metrics, timeframe, total_thumbnails, total_storage_size, thumbnails_by_format, thumbnails_by_size):
        cls.broadcast_group(
            group="all_thumbnail_storage",
            payload={
                "metrics": metrics,
                "timeframe": timeframe,
                "total_thumbnails": total_thumbnails,
                "total_storage_size": str(total_storage_size),
                "thumbnails_by_format": thumbnails_by_format,
                "thumbnails_by_size": thumbnails_by_size,
                "updated_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# Root ThumbnailSubscription
# ----------------------------------------------------------------------

class ThumbnailSubscription(graphene.ObjectType):
    # Thumbnail Operations
    on_thumbnail_created = OnThumbnailCreated.Field()
    on_thumbnail_updated = OnThumbnailUpdated.Field()
    on_thumbnail_deleted = OnThumbnailDeleted.Field()
    
    # Thumbnail Generation
    on_thumbnail_generation_started = OnThumbnailGenerationStarted.Field()
    on_thumbnail_generation_completed = OnThumbnailGenerationCompleted.Field()
    on_thumbnail_generation_failed = OnThumbnailGenerationFailed.Field()
    
    # Analytics
    on_thumbnail_storage_updated = OnThumbnailStorageUpdated.Field()
    
    
    
# Example usage in your Django views or signals
from thumbnail.subscriptions import (OnThumbnailCreated, OnThumbnailDeleted,
                                     OnThumbnailGenerationCompleted,
                                     OnThumbnailGenerationStarted,
                                     OnThumbnailStorageUpdated)


# When a new thumbnail is created
def create_thumbnail(image, size, format, category=None, collection=None, product_media=None, user=None):
    thumbnail = Thumbnail.objects.create(
        image=image,
        size=size,
        format=format,
        category=category,
        collection=collection,
        product_media=product_media,
        user=user
    )
    
    if category:
        OnThumbnailCreated.broadcast_for_category(category, thumbnail)
    elif collection:
        OnThumbnailCreated.broadcast_for_collection(collection, thumbnail)
    elif product_media:
        OnThumbnailCreated.broadcast_for_product_media(product_media, thumbnail)
    elif user:
        OnThumbnailCreated.broadcast_for_user(user, thumbnail)
    
    OnThumbnailCreated.broadcast_to_all(thumbnail)

# When thumbnail generation starts
def start_thumbnail_generation(category=None, collection=None, product_media=None, sizes=None, formats=None, user=None):
    sizes = sizes or [32, 64, 128, 256, 512]
    formats = formats or [ThumbnailFormat.WEBP, ThumbnailFormat.JPEG]
    
    if category:
        OnThumbnailGenerationStarted.broadcast_for_category(category, sizes, formats, user)
    elif collection:
        OnThumbnailGenerationStarted.broadcast_for_collection(collection, sizes, formats, user)
    elif product_media:
        OnThumbnailGenerationStarted.broadcast_for_product_media(product_media, sizes, formats, user)
    else:
        OnThumbnailGenerationStarted.broadcast_to_all(sizes, formats, user)

# When thumbnail generation completes
def complete_thumbnail_generation(category=None, collection=None, product_media=None, generated_thumbnails=None, failed_generations=0):
    generated_thumbnails = generated_thumbnails or []
    
    if category:
        OnThumbnailGenerationCompleted.broadcast_for_category(category, generated_thumbnails, failed_generations)
    elif collection:
        OnThumbnailGenerationCompleted.broadcast_for_collection(collection, generated_thumbnails, failed_generations)
    elif product_media:
        OnThumbnailGenerationCompleted.broadcast_for_product_media(product_media, generated_thumbnails, failed_generations)
    else:
        OnThumbnailGenerationCompleted.broadcast_to_all(generated_thumbnails, failed_generations)

# When thumbnail generation fails
def handle_thumbnail_generation_failure(category=None, collection=None, product_media=None, error_message="", failed_size=None, failed_format=None):
    if category:
        OnThumbnailGenerationFailed.broadcast_for_category(category, error_message, failed_size, failed_format)
    elif collection:
        OnThumbnailGenerationFailed.broadcast_for_collection(collection, error_message, failed_size, failed_format)
    elif product_media:
        OnThumbnailGenerationFailed.broadcast_for_product_media(product_media, error_message, failed_size, failed_format)
    else:
        OnThumbnailGenerationFailed.broadcast_to_all(error_message, failed_size, failed_format)

# When a thumbnail is deleted
def delete_thumbnail(thumbnail):
    if thumbnail.category:
        OnThumbnailDeleted.broadcast_for_category(thumbnail.category, thumbnail)
    elif thumbnail.collection:
        OnThumbnailDeleted.broadcast_for_collection(thumbnail.collection, thumbnail)
    elif thumbnail.product_media:
        OnThumbnailDeleted.broadcast_for_product_media(thumbnail.product_media, thumbnail)
    elif thumbnail.user:
        OnThumbnailDeleted.broadcast_for_user(thumbnail.user, thumbnail)
    
    OnThumbnailDeleted.broadcast_to_all(thumbnail)
    thumbnail.delete()

# When thumbnail is updated
def update_thumbnail(thumbnail, updated_fields, old_values, new_values, updated_by):
    OnThumbnailUpdated.broadcast(
        thumbnail=thumbnail,
        updated_fields=updated_fields,
        old_size=old_values.get('size'),
        new_size=new_values.get('size'),
        old_format=old_values.get('format'),
        new_format=new_values.get('format'),
        updated_by=updated_by
    )

# Update thumbnail storage analytics
def update_thumbnail_storage_analytics(timeframe="daily"):
    total_thumbnails = Thumbnail.objects.count()
    total_storage_size = calculate_total_storage_size()
    
    thumbnails_by_format = Thumbnail.objects.values('format').annotate(count=models.Count('id'))
    thumbnails_by_size = Thumbnail.objects.values('size').annotate(count=models.Count('id'))
    
    metrics = {
        'storage_trend': calculate_storage_trend(timeframe),
        'growth_rate': calculate_growth_rate(timeframe),
        'optimization_opportunities': find_optimization_opportunities()
    }
    
    OnThumbnailStorageUpdated.broadcast_for_timeframe(
        timeframe=timeframe,
        metrics=metrics,
        total_thumbnails=total_thumbnails,
        total_storage_size=total_storage_size,
        thumbnails_by_format=thumbnails_by_format,
        thumbnails_by_size=thumbnails_by_size
    )

# Bulk thumbnail operations
def bulk_generate_thumbnails(objects, sizes, formats, user):
    """Generate thumbnails for multiple objects"""
    for obj in objects:
        if isinstance(obj, Category):
            OnThumbnailGenerationStarted.broadcast_for_category(obj, sizes, formats, user)
        elif isinstance(obj, Collection):
            OnThumbnailGenerationStarted.broadcast_for_collection(obj, sizes, formats, user)
        elif isinstance(obj, ProductMedia):
            OnThumbnailGenerationStarted.broadcast_for_product_media(obj, sizes, formats, user)
    
    # Process thumbnails...
    generated_thumbnails = []
    failed_count = 0
    
    for obj in objects:
        try:
            # Generate thumbnails logic
            thumbnails = generate_thumbnails_for_object(obj, sizes, formats)
            generated_thumbnails.extend(thumbnails)
        except Exception as e:
            failed_count += 1
            if isinstance(obj, Category):
                OnThumbnailGenerationFailed.broadcast_for_category(obj, str(e), None, None)
            elif isinstance(obj, Collection):
                OnThumbnailGenerationFailed.broadcast_for_collection(obj, str(e), None, None)
            elif isinstance(obj, ProductMedia):
                OnThumbnailGenerationFailed.broadcast_for_product_media(obj, str(e), None, None)
    
    # Broadcast completion
    OnThumbnailGenerationCompleted.broadcast_to_all(generated_thumbnails, failed_count)'''