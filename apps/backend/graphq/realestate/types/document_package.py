# apps/backend/graphq/realestate/types/document_package.py

from graphene import Node
from graphene_django import DjangoObjectType

from realestate.models import DocumentPackage


class DocumentPackageNode(DjangoObjectType):
    class Meta:
        model = DocumentPackage
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # ---- Forward FKs (the correct names) ------------------------
            "property": ["exact"],
            "created_by": ["exact"],

            # ---- Traversals into the parent listing ---------------------
            "property__title": ["exact", "icontains"],
            "property__city": ["exact", "icontains"],
            "property__country_code": ["exact"],
            "property__is_published": ["exact"],

            # ---- Traversals into the creator ----------------------------
            "created_by__email": ["exact", "icontains"],
            "created_by__first_name": ["exact", "icontains"],

            # ---- Scalar filters ----------------------------------------
            "title": ["exact", "icontains", "istartswith"],
            "is_completed": ["exact"],

            # ---- Timestamps --------------------------------------------
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
        }