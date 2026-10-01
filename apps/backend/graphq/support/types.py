from graphene_django.types import DjangoObjectType
from graphene import Node
from support.models.contact import (
    ContactUs
    )

class ContactUsNode(DjangoObjectType):
    class Meta:
        model = ContactUs
        interfaces = ( Node,)
        fields = '__all__'
        filter_fields = ['name', 'email' ]


 

