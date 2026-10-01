import graphene
from graphene import relay, Boolean, String, Field, ID, Int
from django.db import transaction
from graphene_gis.scalars import LineStringScalar
from graphql import GraphQLError
from graphql_relay import from_global_id
from graphq.realestate.types.document import DocumentNode
from realestate.models import DocumentPackage, Document
from univa_jwt.decorators import login_required

class CreateDocument(relay.ClientIDMutation):
    class Input:
        package_id = graphene.ID(required=True)
        title = graphene.String(required=True)
        requires_signature = graphene.Boolean(default_value=False)
        order = graphene.Int(default_value=0)
    
    document = graphene.Field(DocumentNode)
    
    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            package_id = from_global_id(input['package_id'])[1]
            package = DocumentPackage.objects.get(id=package_id)
            
            # Check permission
            if package.created_by != info.context.user and not info.context.user.is_staff:
                raise GraphQLError("Permission denied")
            
            file_obj = info.context.FILES.get('file')
            if not file_obj:
                raise GraphQLError("File is required")
            
            document = Document.objects.create(
                package=package,
                title=input['title'],
                file=file_obj,
                requires_signature=input['requires_signature'],
                order=input['order']
            )
            
            return cls(document=document)
        except Exception as e:
            logger.error(f"Error creating Document: {e}")
            raise GraphQLError("Failed to create document")

class UpdateDocument(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        title = graphene.String()
        requires_signature = graphene.Boolean()
        order = graphene.Int()
    
    document = graphene.Field(DocumentNode)
    
    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            document_id = from_global_id(input['id'])[1]
            document = Document.objects.get(id=document_id)
            
            # Check permission
            if document.package.created_by != info.context.user and not info.context.user.is_staff:
                raise GraphQLError("Permission denied")
            
            if 'title' in input:
                document.title = input['title']
            if 'requires_signature' in input:
                document.requires_signature = input['requires_signature']
            if 'order' in input:
                document.order = input['order']
            
            document.save()
            return cls(document=document)
        except Exception as e:
            logger.error(f"Error updating Document: {e}")
            raise GraphQLError("Failed to update document")

class DeleteDocument(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
    
    success = graphene.Boolean()
    
    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            document_id = from_global_id(input['id'])[1]
            document = Document.objects.get(id=document_id)
            
            # Check permission
            if document.package.created_by != info.context.user and not info.context.user.is_staff:
                raise GraphQLError("Permission denied")
            
            document.delete()
            return cls(success=True)
        except Exception as e:
            logger.error(f"Error deleting Document: {e}")
            raise GraphQLError("Failed to delete document")
  

class DocumentMutations(graphene.ObjectType):
    create_document = CreateDocument.Field()
    update_document = UpdateDocument.Field()
    delete_document = DeleteDocument.Field()