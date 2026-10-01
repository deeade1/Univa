import graphene
from graphene import relay
from graphene.types.generic import GenericScalar
from graphql_relay import from_global_id

from  ecommerce.models.attribute import (
    Attribute,
    AssignedProductAttributeValue,
    AttributeProduct,
    AssignedVariantAttributeValue,
    AssignedVariantAttribute,
    AttributeVariant,
    
)
from graphq.ecommerce.types.attribute import (
    AssignedProductAttributeValueNode,
    AssignedVariantAttributeNode,
    AssignedVariantAttributeValueNode,
    AttributeNode, 
    AttributeProductNode,
    AttributeValueNode, 
    AttributeVariantNode
)


# -------------------------
# Attribute CRUD write query for this
# -------------------------
class CreateAttribute(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)
        slug = graphene.String(required=True)
        type = graphene.String(required=True)  # choices auto-enum
        input_type = graphene.String()
        entity_type = graphene.String()
        unit = graphene.String()
        value_required = graphene.Boolean()
        is_variant_only = graphene.Boolean()
        visible_in_storefront = graphene.Boolean()
        filterable_in_storefront = graphene.Boolean()
        filterable_in_dashboard = graphene.Boolean()
        storefront_search_position = graphene.Int()
        available_in_grid = graphene.Boolean()
        max_sort_order = graphene.Int()

    attribute = graphene.Field(lambda: AttributeNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        attribute = Attribute.objects.create(
            name=input["name"],
            slug=input["slug"],
            type=input["type"],
            input_type=input.get("input_type"),
            entity_type=input.get("entity_type"),
            unit=input.get("unit"),
            value_required=input.get("value_required", False),
            is_variant_only=input.get("is_variant_only", False),
            visible_in_storefront=input.get("visible_in_storefront", True),
            filterable_in_storefront=input.get("filterable_in_storefront", False),
            filterable_in_dashboard=input.get("filterable_in_dashboard", False),
            storefront_search_position=input.get("storefront_search_position", 0),
            available_in_grid=input.get("available_in_grid", False),
            max_sort_order=input.get("max_sort_order"),
        )
        return CreateAttribute(attribute=attribute)


class UpdateAttribute(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        slug = graphene.String()
        type = graphene.String()
        input_type = graphene.String()
        entity_type = graphene.String()
        unit = graphene.String()
        value_required = graphene.Boolean()
        is_variant_only = graphene.Boolean()
        visible_in_storefront = graphene.Boolean()
        filterable_in_storefront = graphene.Boolean()
        filterable_in_dashboard = graphene.Boolean()
        storefront_search_position = graphene.Int()
        available_in_grid = graphene.Boolean()
        max_sort_order = graphene.Int()

    attribute = graphene.Field(lambda: AttributeNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        attribute = Attribute.objects.get(pk=pk)
        for field in [
            "name",
            "slug",
            "type",
            "input_type",
            "entity_type",
            "unit",
            "value_required",
            "is_variant_only",
            "visible_in_storefront",
            "filterable_in_storefront",
            "filterable_in_dashboard",
            "storefront_search_position",
            "available_in_grid",
            "max_sort_order",
        ]:
            if field in input and input[field] is not None:
                setattr(attribute, field, input[field])
        attribute.save()
        return UpdateAttribute(attribute=attribute)


class DeleteAttribute(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_attribute_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            attribute = Attribute.objects.get(pk=pk)
        except Attribute.DoesNotExist:
            raise Exception("Attribute not found.")
        deleted_id = input["id"]
        attribute.delete()
        return DeleteAttribute(ok=True, deleted_attribute_id=deleted_id)


# -------------------------
# AttributeValue CRUD
# -------------------------
class CreateAttributeValue(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)
        value = graphene.String()
        slug = graphene.String(required=True)
        file_url = graphene.String()
        content_type = graphene.String()
        attribute_id = graphene.ID(required=True)
        rich_text = GenericScalar()
        plain_text = graphene.String()
        boolean = graphene.Boolean()
        date_time = graphene.DateTime()
        reference_product_id = graphene.ID()
        reference_variant_id = graphene.ID()
        sort_order = graphene.Int()

    attribute_value = graphene.Field(lambda: AttributeValueNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        attribute_pk = from_global_id(input["attribute_id"])[1]
        kwargs = {
            "name": input["name"],
            "value": input.get("value", ""),
            "slug": input["slug"],
            "file_url": input.get("file_url"),
            "content_type": input.get("content_type"),
            "attribute_id": attribute_pk,
            "rich_text": input.get("rich_text", {}),
            "plain_text": input.get("plain_text"),
            "boolean": input.get("boolean"),
            "date_time": input.get("date_time"),
            "sort_order": input.get("sort_order"),
        }

        # optional relations
        if input.get("reference_product_id"):
            kwargs["reference_product_id"] = from_global_id(input["reference_product_id"])[1]
        if input.get("reference_variant_id"):
            kwargs["reference_variant_id"] = from_global_id(input["reference_variant_id"])[1]

        av = AttributeValue.objects.create(**kwargs)
        return CreateAttributeValue(attribute_value=av)


class UpdateAttributeValue(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        value = graphene.String()
        slug = graphene.String()
        file_url = graphene.String()
        content_type = graphene.String()
        attribute_id = graphene.ID()
        rich_text = GenericScalar()
        plain_text = graphene.String()
        boolean = graphene.Boolean()
        date_time = graphene.DateTime()
        reference_product_id = graphene.ID()
        reference_variant_id = graphene.ID()
        sort_order = graphene.Int()

    attribute_value = graphene.Field(lambda: AttributeValueNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        av = AttributeValue.objects.get(pk=pk)
        for field in [
            "name",
            "value",
            "slug",
            "file_url",
            "content_type",
            "rich_text",
            "plain_text",
            "boolean",
            "date_time",
            "sort_order",
        ]:
            if field in input and input[field] is not None:
                setattr(av, field, input[field])

        if input.get("attribute_id"):
            av.attribute_id = from_global_id(input["attribute_id"])[1]

        if input.get("reference_product_id"):
            av.reference_product_id = from_global_id(input["reference_product_id"])[1]
        if input.get("reference_variant_id"):
            av.reference_variant_id = from_global_id(input["reference_variant_id"])[1]

        av.save()
        return UpdateAttributeValue(attribute_value=av)


class DeleteAttributeValue(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_attribute_value_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            av = AttributeValue.objects.get(pk=pk)
        except AttributeValue.DoesNotExist:
            raise Exception("AttributeValue not found.")
        deleted_id = input["id"]
        av.delete()
        return DeleteAttributeValue(ok=True, deleted_attribute_value_id=deleted_id)


# -------------------------
# AssignedProductAttributeValue CRUD
# -------------------------
class CreateAssignedProductAttributeValue(relay.ClientIDMutation):
    class Input:
        value_id = graphene.ID(required=True)
        product_id = graphene.ID(required=True)

    assigned = graphene.Field(lambda: AssignedProductAttributeValueNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        value_pk = from_global_id(input["value_id"])[1]
        product_pk = from_global_id(input["product_id"])[1]
        assigned = AssignedProductAttributeValue.objects.create(
            value_id=value_pk, product_id=product_pk
        )
        return CreateAssignedProductAttributeValue(assigned=assigned)


class DeleteAssignedProductAttributeValue(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            obj = AssignedProductAttributeValue.objects.get(pk=pk)
        except AssignedProductAttributeValue.DoesNotExist:
            raise Exception("AssignedProductAttributeValue not found.")
        deleted_id = input["id"]
        obj.delete()
        return DeleteAssignedProductAttributeValue(ok=True, deleted_id=deleted_id)


# -------------------------
# AttributeProduct (m2m through) CRUD
# -------------------------
class CreateAttributeProduct(relay.ClientIDMutation):
    class Input:
        attribute_id = graphene.ID(required=True)
        product_type_id = graphene.ID(required=True)

    attribute_product = graphene.Field(lambda: AttributeProductNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        attribute_pk = from_global_id(input["attribute_id"])[1]
        product_type_pk = from_global_id(input["product_type_id"])[1]
        ap = AttributeProduct.objects.create(
            attribute_id=attribute_pk, product_type_id=product_type_pk
        )
        return CreateAttributeProduct(attribute_product=ap)


class DeleteAttributeProduct(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            obj = AttributeProduct.objects.get(pk=pk)
        except AttributeProduct.DoesNotExist:
            raise Exception("AttributeProduct not found.")
        deleted_id = input["id"]
        obj.delete()
        return DeleteAttributeProduct(ok=True, deleted_id=deleted_id)


# -------------------------
# AssignedVariantAttributeValue CRUD
# -------------------------
class CreateAssignedVariantAttributeValue(relay.ClientIDMutation):
    class Input:
        value_id = graphene.ID(required=True)
        assignment_id = graphene.ID(required=True)
        sort_order = graphene.Int()

    assigned = graphene.Field(lambda: AssignedVariantAttributeValueNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        value_pk = from_global_id(input["value_id"])[1]
        assignment_pk = from_global_id(input["assignment_id"])[1]
        kwargs = {"value_id": value_pk, "assignment_id": assignment_pk}
        if "sort_order" in input:
            kwargs["sort_order"] = input["sort_order"]
        assigned = AssignedVariantAttributeValue.objects.create(**kwargs)
        return CreateAssignedVariantAttributeValue(assigned=assigned)


class UpdateAssignedVariantAttributeValue(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        sort_order = graphene.Int()

    assigned = graphene.Field(lambda: AssignedVariantAttributeValueNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        obj = AssignedVariantAttributeValue.objects.get(pk=pk)
        if "sort_order" in input and input["sort_order"] is not None:
            obj.sort_order = input["sort_order"]
        obj.save()
        return UpdateAssignedVariantAttributeValue(assigned=obj)


class DeleteAssignedVariantAttributeValue(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            obj = AssignedVariantAttributeValue.objects.get(pk=pk)
        except AssignedVariantAttributeValue.DoesNotExist:
            raise Exception("AssignedVariantAttributeValue not found.")
        deleted_id = input["id"]
        obj.delete()
        return DeleteAssignedVariantAttributeValue(ok=True, deleted_id=deleted_id)


# -------------------------
# AssignedVariantAttribute CRUD
# -------------------------
class CreateAssignedVariantAttribute(relay.ClientIDMutation):
    class Input:
        variant_id = graphene.ID(required=True)
        assignment_id = graphene.ID(required=True)
        value_ids = graphene.List(graphene.ID)

    assigned_variant_attribute = graphene.Field(lambda: AssignedVariantAttributeNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        variant_pk = from_global_id(input["variant_id"])[1]
        assignment_pk = from_global_id(input["assignment_id"])[1]
        ava = AssignedVariantAttribute.objects.create(
            variant_id=variant_pk, assignment_id=assignment_pk
        )
        # attach values if provided
        if input.get("value_ids"):
            value_pks = [from_global_id(v)[1] for v in input["value_ids"]]
            ava.values.set(value_pks)
        return CreateAssignedVariantAttribute(assigned_variant_attribute=ava)


class UpdateAssignedVariantAttribute(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        value_ids = graphene.List(graphene.ID)

    assigned_variant_attribute = graphene.Field(lambda: AssignedVariantAttributeNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        ava = AssignedVariantAttribute.objects.get(pk=pk)
        if "value_ids" in input and input["value_ids"] is not None:
            value_pks = [from_global_id(v)[1] for v in input["value_ids"]]
            ava.values.set(value_pks)
        ava.save()
        return UpdateAssignedVariantAttribute(assigned_variant_attribute=ava)


class DeleteAssignedVariantAttribute(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            obj = AssignedVariantAttribute.objects.get(pk=pk)
        except AssignedVariantAttribute.DoesNotExist:
            raise Exception("AssignedVariantAttribute not found.")
        deleted_id = input["id"]
        obj.delete()
        return DeleteAssignedVariantAttribute(ok=True, deleted_id=deleted_id)


# -------------------------
# AttributeVariant CRUD
# -------------------------
class CreateAttributeVariant(relay.ClientIDMutation):
    class Input:
        attribute_id = graphene.ID(required=True)
        product_type_id = graphene.ID(required=True)
        variant_selection = graphene.Boolean()

    attribute_variant = graphene.Field(lambda: AttributeVariantNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        attribute_pk = from_global_id(input["attribute_id"])[1]
        product_type_pk = from_global_id(input["product_type_id"])[1]
        av = AttributeVariant.objects.create(
            attribute_id=attribute_pk,
            product_type_id=product_type_pk,
            variant_selection=input.get("variant_selection", False),
        )
        return CreateAttributeVariant(attribute_variant=av)


class UpdateAttributeVariant(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        variant_selection = graphene.Boolean()
        sort_order = graphene.Int()

    attribute_variant = graphene.Field(lambda: AttributeVariantNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        av = AttributeVariant.objects.get(pk=pk)
        if "variant_selection" in input and input["variant_selection"] is not None:
            av.variant_selection = input["variant_selection"]
        if "sort_order" in input and hasattr(av, "sort_order") and input["sort_order"] is not None:
            av.sort_order = input["sort_order"]
        av.save()
        return UpdateAttributeVariant(attribute_variant=av)


class DeleteAttributeVariant(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            obj = attribute_models.AttributeVariant.objects.get(pk=pk)
        except AttributeVariant.DoesNotExist:
            raise Exception("AttributeVariant not found.")
        deleted_id = input["id"]
        obj.delete()
        return DeleteAttributeVariant(ok=True, deleted_id=deleted_id)


# -------------------------
# Root Mutations Export
# -------------------------
class AttributeMutations(graphene.ObjectType):
    # Attribute
    create_attribute = CreateAttribute.Field()
    update_attribute = UpdateAttribute.Field()
    delete_attribute = DeleteAttribute.Field()

    # AttributeValue
    create_attribute_value = CreateAttributeValue.Field()
    update_attribute_value = UpdateAttributeValue.Field()
    delete_attribute_value = DeleteAttributeValue.Field()

    # AssignedProductAttributeValue
    create_assigned_product_attribute_value = CreateAssignedProductAttributeValue.Field()
    delete_assigned_product_attribute_value = DeleteAssignedProductAttributeValue.Field()

    # AttributeProduct (m2m through)
    create_attribute_product = CreateAttributeProduct.Field()
    delete_attribute_product = DeleteAttributeProduct.Field()

    # AssignedVariantAttributeValue
    create_assigned_variant_attribute_value = CreateAssignedVariantAttributeValue.Field()
    update_assigned_variant_attribute_value = UpdateAssignedVariantAttributeValue.Field()
    delete_assigned_variant_attribute_value = DeleteAssignedVariantAttributeValue.Field()

    # AssignedVariantAttribute
    create_assigned_variant_attribute = CreateAssignedVariantAttribute.Field()
    update_assigned_variant_attribute = UpdateAssignedVariantAttribute.Field()
    delete_assigned_variant_attribute = DeleteAssignedVariantAttribute.Field()

    # AttributeVariant
    create_attribute_variant = CreateAttributeVariant.Field()
    update_attribute_variant = UpdateAttributeVariant.Field()
    delete_attribute_variant = DeleteAttributeVariant.Field()
