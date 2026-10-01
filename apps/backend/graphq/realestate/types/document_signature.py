# apps/backend/graphq/realestate/types/document_signature.py

from graphene_django import DjangoObjectType
from graphene import Node

from realestate.models import DocumentSignature


class DocumentSignatureNode(DjangoObjectType):
    class Meta:
        model = DocumentSignature
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # ---- Forward FKs (the correct names) ------------------------
            "document": ["exact"],
            "user": ["exact"],

            # ---- Traversals into the parent document --------------------
            "document__title": ["exact", "icontains"],
            "document__package": ["exact"],
            "document__package__property": ["exact"],
            "document__package__property__title": ["exact", "icontains"],

            # ---- Traversals into the signer -----------------------------
            "user__email": ["exact", "icontains"],
            "user__first_name": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "signed_at": ["exact", "gte", "lte", "lt", "gt"],
        }