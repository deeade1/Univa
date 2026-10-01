import graphene
from graphene import relay
from graphql import GraphQLError

from thumbnail import models

from .types import ThumbnailType


# ---------- Helper ----------
def get_object(model, id):
    try:
        return model.objects.get(pk=id)
    except model.DoesNotExist:
        raise GraphQLError(f"{model.__name__} with ID {id} does not exist.")


# ---------- CREATE ----------
class CreateThumbnail(relay.ClientIDMutation):
    class Input:
        image = graphene.String(required=True)  # Base64 or file URL
        size = graphene.Int(required=True)
        format = graphene.String(required=False)
        category_id = graphene.ID(required=False)
        collection_id = graphene.ID(required=False)
        product_media_id = graphene.ID(required=False)
        user_id = graphene.ID(required=False)

    thumbnail = graphene.Field(ThumbnailType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, image, size, **kwargs):
        from accounts.models import UserProfile
        from product.models import Category, Collection, ProductMedia

        # Resolve related fields
        category = get_object(Category, kwargs["category_id"]) if kwargs.get("category_id") else None
        collection = get_object(Collection, kwargs["collection_id"]) if kwargs.get("collection_id") else None
        product_media = get_object(ProductMedia, kwargs["product_media_id"]) if kwargs.get("product_media_id") else None
        user = get_object(UserProfile, kwargs["user_id"]) if kwargs.get("user_id") else None

        obj = models.Thumbnail.objects.create(
            image=image,
            size=size,
            format=kwargs.get("format"),
            category=category,
            collection=collection,
            product_media=product_media,
            user=user,
        )
        return CreateThumbnail(thumbnail=obj)


# ---------- UPDATE ----------
class UpdateThumbnail(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        image = graphene.String(required=False)
        size = graphene.Int(required=False)
        format = graphene.String(required=False)
        category_id = graphene.ID(required=False)
        collection_id = graphene.ID(required=False)
        product_media_id = graphene.ID(required=False)
        user_id = graphene.ID(required=False)

    thumbnail = graphene.Field(ThumbnailType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **kwargs):
        from accounts.models import UserProfile
        from product.models import Category, Collection, ProductMedia

        obj = get_object(models.Thumbnail, id)

        # Update foreign keys
        if "category_id" in kwargs:
            obj.category = get_object(Category, kwargs["category_id"]) if kwargs["category_id"] else None
        if "collection_id" in kwargs:
            obj.collection = get_object(Collection, kwargs["collection_id"]) if kwargs["collection_id"] else None
        if "product_media_id" in kwargs:
            obj.product_media = get_object(ProductMedia, kwargs["product_media_id"]) if kwargs["product_media_id"] else None
        if "user_id" in kwargs:
            obj.user = get_object(UserProfile, kwargs["user_id"]) if kwargs["user_id"] else None

        # Update regular fields
        for key in ["image", "size", "format"]:
            if key in kwargs and kwargs[key] is not None:
                setattr(obj, key, kwargs[key])

        obj.save()
        return UpdateThumbnail(thumbnail=obj)


# ---------- DELETE ----------
class DeleteThumbnail(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        obj = get_object(models.Thumbnail, id)
        obj.delete()
        return DeleteThumbnail(ok=True)


# ---------- ROOT ----------
class ThumbnailMutations(graphene.ObjectType):
    create_thumbnail = CreateThumbnail.Field()
    update_thumbnail = UpdateThumbnail.Field()
    delete_thumbnail = DeleteThumbnail.Field()
