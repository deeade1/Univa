import logging

import graphene
from graphene import relay, Boolean, String, Field, ID, Decimal, Int
from django.contrib.auth import get_user_model
from django.db import transaction
from graphql import GraphQLError
from graphql_relay import from_global_id
from graphq.realestate.types.ar_model import ARModelNode  

from realestate.models import ARModel 

logger = logging.getLogger(__name__)
User = get_user_model()

# -------------------------
# ARModel Mutation
# -------------------------
class CreateARModelMutation(relay.ClientIDMutation):
    class Input:
        id = ID(required=False)
        property_id = ID(required=True)
        model_url = String(required=True)
        scale = Decimal(required=False)
        anchor_type = String(required=True)
        

    ar_model = Field(ARModelNode)
    success = Boolean()
    message = String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        preview_image = info.context.FILES
        property_obj = relay.Node.get_node_from_global_id(info, input.pop('property_id'))
        if not property_obj:
            raise GraphQLError("Property not found")
        input['property'] = property_obj

        ar_id = input.pop('id', None)
        if ar_id:
            ar_model = ArModel.objects.get(pk=from_global_id(ar_id)[1])
            if not ar_model:
                raise GraphQLError("ARModel not found")
            for k, v in input.items():
                setattr(ar_model, k, v)
            ar_model.save()
            message = "ARModel updated successfully"
        else:
            ar_model = ARModel.objects.create(**input)
            message = "ARModel created successfully"

        return cls(ar_model=ar_model, success=True, message=message)


# -------------------------
# Update ARModel Mutation
# -------------------------
class UpdateARModelMutation(relay.ClientIDMutation):
    class Input:
        id = ID(required=True)
        property_id = ID(required=False)
        model_url = String(required=False)
        scale = Decimal(required=False)
        anchor_type = String(required=False)

    ar_model = Field(ARModelNode)
    success = Boolean()
    message = String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # Get the AR model instance
        ar_id = input.pop('id')
        ar_model = ARModel.objects.get(pk=from_global_id(ar_id)[1])
        
        if not ar_model:
            raise GraphQLError("ARModel not found")

        # Update property if provided
        if 'property_id' in input and input['property_id']:
            property_obj = relay.Node.get_node_from_global_id(info, input.pop('property_id'))
            if not property_obj:
                raise GraphQLError("Property not found")
            ar_model.property = property_obj

        # Update remaining fields
        for k, v in input.items():
            if v is not None:  # Only update if value is provided
                setattr(ar_model, k, v)
        
        ar_model.save()
        
        return cls(
            ar_model=ar_model, 
            success=True, 
            message="ARModel updated successfully"
        )


# -------------------------
# Delete ARModel Mutation
# -------------------------
class DeleteARModelMutation(relay.ClientIDMutation):
    class Input:
        id = ID(required=True)

    success = Boolean()
    message = String()
    deleted_id = ID()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        ar_id = input.get('id')
        
        try:
            ar_model = ARModel.objects.get(pk=from_global_id(ar_id)[1])
            ar_model.delete()
            
            return cls(
                success=True,
                message="ARModel deleted successfully",
                deleted_id=ar_id
            )
        except ARModel.DoesNotExist:
            raise GraphQLError("ARModel not found")
        except Exception as e:
            raise GraphQLError(f"Error deleting ARModel: {str(e)}")


# -------------------------
# Optional: Batch Delete ARModel Mutation
# -------------------------
class BatchDeleteARModelMutation(relay.ClientIDMutation):
    class Input:
        ids = graphene.List(ID, required=True)

    success = Boolean()
    message = String()
    deleted_count = Int()
    deleted_ids = graphene.List(ID)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        ids = input.get('ids', [])
        deleted_ids = []
        deleted_count = 0
        
        for global_id in ids:
            try:
                ar_model = ARModel.objects.get(pk=from_global_id(global_id)[1])
                ar_model.delete()
                deleted_ids.append(global_id)
                deleted_count += 1
            except ARModel.DoesNotExist:
                # Skip if not found, or you could raise an error
                continue
            except Exception as e:
                raise GraphQLError(f"Error deleting ARModel {global_id}: {str(e)}")
        
        return cls(
            success=True,
            message=f"{deleted_count} ARModel(s) deleted successfully",
            deleted_count=deleted_count,
            deleted_ids=deleted_ids
        )


# -------------------------
# Optional: Update ARModel with File Upload
# -------------------------
class UpdateARModelWithFileMutation(relay.ClientIDMutation):
    class Input:
        id = ID(required=True)
        model_url = String(required=False)
        scale = Decimal(required=False)
        anchor_type = String(required=False)

    ar_model = Field(ARModelNode)
    success = Boolean()
    message = String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # Get the AR model instance
        ar_id = input.pop('id')
        ar_model = ARModel.objects.get(pk=from_global_id(ar_id)[1])
        
        if not ar_model:
            raise GraphQLError("ARModel not found")

        # Handle file upload if present
        preview_image = info.context.FILES.get('preview_image')
        if preview_image:
            # Process the uploaded file
            # Save the file and update model_url or create thumbnail
            # Example: ar_model.preview_image = preview_image
            pass

        # Update remaining fields
        for k, v in input.items():
            if v is not None:
                setattr(ar_model, k, v)
        
        ar_model.save()
        
        return cls(
            ar_model=ar_model, 
            success=True, 
            message="ARModel updated successfully"
        )
        
class ARModelMutations(graphene.ObjectType):
    create_ar_model = CreateARModelMutation.Field()
    update_ar_model = UpdateARModelMutation.Field()
    delete_ar_model = DeleteARModelMutation.Field()
    batch_delete_ar_model = BatchDeleteARModelMutation.Field()
    update_ar_model_with_file = UpdateARModelWithFileMutation.Field()