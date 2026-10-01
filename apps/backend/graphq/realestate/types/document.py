# apps/backend/graphq/realestate/types/document.py

from graphene import Node
from graphene_django import DjangoObjectType

from realestate.models import Document


class DocumentNode(DjangoObjectType):
    class Meta:
        model = Document
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # ---- Forward FK (the correct name) --------------------------
            "package": ["exact"],

            # ---- Traversals into the parent package ---------------------
            "package__title": ["exact", "icontains"],
            "package__property": ["exact"],
            "package__property__title": ["exact", "icontains"],
            "package__property__city": ["exact", "icontains"],
            "package__created_by": ["exact"],
            "package__is_completed": ["exact"],

            # ---- Scalar filters ----------------------------------------
            "title": ["exact", "icontains", "istartswith"],  # no leading space
            "requires_signature": ["exact"],
            "order": ["exact", "gte", "lte", "lt", "gt"],
        }