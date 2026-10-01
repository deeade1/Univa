import graphene
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from ecommerce.models.product import (
    ProductType, 
    Product,
    ProductVariant, 
    ProductTranslation,
    DigitalContent,  
    ProductReview
)

from ecommerce.models.category import Category
from ecommerce.models.collection import (
    Collection,
    CollectionProduct,
)

from graphq.ecommerce.types.product import (
    DigitalContentNode, 
    ProductNode, 
    ProductReviewNode,
    ProductTranslationNode, 
    ProductTypeNode,
    ProductVariantNode,
    
)
from graphq.ecommerce.types.collection import (
    CollectionNode, 
    CollectionProductNode,
    
)
from graphq.ecommerce.types.category import (
    CategoryNode, 
    CategoryTranslationNode,
    CategoryTreeNode
)

def get_object(model, id):
    try:
        return model.objects.get(pk=id)
    except model.DoesNotExist:
        raise GraphQLError(f"{model.__name__} with ID {id} does not exist.")


# ---------------- CATEGORY ----------------
class CreateCategory(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)
        slug = graphene.String(required=True)
        parent_id = graphene.ID(required=False)

    category = graphene.Field(CategoryNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, name, slug, parent_id=None):
        parent = get_object(Category, parent_id) if parent_id else None
        category = Category.objects.create(name=name, slug=slug, parent=parent)
        return CreateCategory(category=category)


class UpdateCategory(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        slug = graphene.String()

    category = graphene.Field(CategoryNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **kwargs):
        category = get_object(Category, id)
        for field, value in kwargs.items():
            setattr(category, field, value)
        category.save()
        return UpdateCategory(category=category)


class DeleteCategory(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        category = get_object(Category, id)
        category.delete()
        return DeleteCategory(ok=True)


# ---------------- PRODUCT ----------------
class CreateProduct(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)
        slug = graphene.String(required=True)
        product_type_id = graphene.ID(required=True)
        category_id = graphene.ID(required=False)

    product = graphene.Field(ProductNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, name, slug, product_type_id, category_id=None):
        product_type = get_object(ProductType, product_type_id)
        category = get_object(Category, category_id) if category_id else None
        product = Product.objects.create(
            name=name, slug=slug, product_type=product_type, category=category
        )
        return CreateProduct(product=product)


class UpdateProduct(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        slug = graphene.String()

    product = graphene.Field(ProductNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **kwargs):
        product = get_object(Product, id)
        for field, value in kwargs.items():
            setattr(product, field, value)
        product.save()
        return UpdateProduct(product=product)


class DeleteProduct(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        product = get_object(Product, id)
        product.delete()
        return DeleteProduct(ok=True)


# ---------------- VARIANT ----------------
class CreateProductVariant(relay.ClientIDMutation):
    class Input:
        product_id = graphene.ID(required=True)
        sku = graphene.String(required=True)
        name = graphene.String(required=False)

    variant = graphene.Field(ProductVariantNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, product_id, sku, name=None):
        product = get_object(Product, product_id)
        variant = ProductVariant.objects.create(product=product, sku=sku, name=name or sku)
        return CreateProductVariant(variant=variant)


class DeleteProductVariant(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        variant = get_object(ProductVariant, id)
        variant.delete()
        return DeleteProductVariant(ok=True)


# ---------------- COLLECTION ----------------
class CreateCollection(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)
        slug = graphene.String(required=True)
        description = graphene.String(required=False)

    collection = graphene.Field(CollectionNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, name, slug, description=None):
        collection = Collection.objects.create(
            name=name, slug=slug, description=description or {}
        )
        return CreateCollection(collection=collection)


class DeleteCollection(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        collection = get_object(Collection, id)
        collection.delete()
        return DeleteCollection(ok=True)


# --- TRANSLATIONS ---
class CreateProductTranslation(relay.ClientIDMutation):
    class Input:
        product_id = graphene.ID(required=True)
        language_code = graphene.String(required=True)
        name = graphene.String(required=False)
        description = graphene.JSONString(required=False)

    product_translation = graphene.Field(ProductTranslationNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, product_id, language_code, name=None, description=None):
        product = get_object(Product, product_id)
        translation = ProductTranslation.objects.create(
            product=product, language_code=language_code, name=name, description=description
        )
        return CreateProductTranslation(product_translation=translation)


class DeleteProductTranslation(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        translation = get_object(ProductTranslation, id)
        translation.delete()
        return DeleteProductTranslation(ok=True)


# --- DIGITAL CONTENT ---
class CreateDigitalContent(relay.ClientIDMutation):
    class Input:
        product_variant_id = graphene.ID(required=True)
        automatic_fulfillment = graphene.Boolean(required=False)
        max_downloads = graphene.Int(required=False)
        url_valid_days = graphene.Int(required=False)

    digital_content = graphene.Field(DigitalContentNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, product_variant_id, **kwargs):
        variant = get_object(ProductVariant, product_variant_id)
        content = DigitalContent.objects.create(product_variant=variant, **kwargs)
        return CreateDigitalContent(digital_content=content)


class DeleteDigitalContent(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        content = get_object(DigitalContent, id)
        content.delete()
        return DeleteDigitalContent(ok=True)


# --- COLLECTION PRODUCT ---
class AddProductToCollection(relay.ClientIDMutation):
    class Input:
        collection_id = graphene.ID(required=True)
        product_id = graphene.ID(required=True)

    collection_product = graphene.Field(CollectionProductNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, collection_id, product_id):
        collection = get_object(Collection, collection_id)
        product = get_object(Product, product_id)
        link, _ = CollectionProduct.objects.get_or_create(collection=collection, product=product)
        return AddProductToCollection(collection_product=link)


class RemoveProductFromCollection(relay.ClientIDMutation):
    class Input:
        collection_id = graphene.ID(required=True)
        product_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, collection_id, product_id):
        CollectionProduct.objects.filter(collection_id=collection_id, product_id=product_id).delete()
        return RemoveProductFromCollection(ok=True)




class CreateProductReview(relay.ClientIDMutation):
    class Input:
        product_id = graphene.ID(required=True)
        rating = graphene.Int(required=True)
        comment = graphene.String(required=False)

    review = graphene.Field(ProductReviewNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Authentication required")

        product_global_id = input.get("product_id")
        rating = input.get("rating")
        comment = input.get("comment", "")

        # ✅ FIX: Use product_global_id, not undefined 'id'
        _, product_id = from_global_id(product_global_id)
        product = Product.objects.get(pk=product_id)

        if product is None:
            raise GraphQLError("Invalid product ID")

        review = ProductReview.objects.create(
            product=product,
            user=user,
            rating=rating,
            comment=comment
        )

        return CreateProductReview(review=review)

# ---------------- ROOT MUTATION ----------------
class ProductMutations(graphene.ObjectType):
    create_category = CreateCategory.Field()
    update_category = UpdateCategory.Field()
    delete_category = DeleteCategory.Field()

    create_product = CreateProduct.Field()
    update_product = UpdateProduct.Field()
    delete_product = DeleteProduct.Field()

    create_variant = CreateProductVariant.Field()
    delete_variant = DeleteProductVariant.Field()

    create_collection = CreateCollection.Field()
    delete_collection = DeleteCollection.Field()

    create_product_translation = CreateProductTranslation.Field()
    delete_product_translation = DeleteProductTranslation.Field()

    create_digital_content = CreateDigitalContent.Field()
    delete_digital_content = DeleteDigitalContent.Field()

    add_product_to_collection = AddProductToCollection.Field()
    remove_product_from_collection = RemoveProductFromCollection.Field()

    product_review = CreateProductReview.Field()
