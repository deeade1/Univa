# apps/backend/graphq/realestate/types/message_attachment.py

from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from realestate.models import MessageAttachment


class MessageAttachmentNode(OptimizedDjangoObjectType):
    class Meta:
        model = MessageAttachment
        fields = "__all__"
        interfaces = (Node,)
        filter_fields = {
            # ---- Forward FK (the correct name) --------------------------
            "message": ["exact"],

            # ---- Scalar filters ----------------------------------------
            "file_name": ["exact", "icontains", "istartswith"],
            "file_type": ["exact", "icontains"],

            # ---- Traversals into the parent message ---------------------
            # Adjust the traversal paths to match whatever fields
            # Message actually has. The two most likely candidates
            # based on the rest of the real-estate domain:
            "message__sender": ["exact"],
            "message__sender__email": ["exact", "icontains"],
            "message__thread": ["exact"],
        }