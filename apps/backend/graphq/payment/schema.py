import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from .types import (PaymentNode, TransactionEventNode, TransactionItemNode,
                    TransactionNode, PaymentMethodNode)




class PaymentQueries(graphene.ObjectType):
    payment = relay.Node.Field(PaymentNode)
    all_payments = DjangoFilterConnectionField(PaymentNode)

    transaction = relay.Node.Field(TransactionNode)
    all_transactions = DjangoFilterConnectionField(TransactionNode)

    transaction_event = relay.Node.Field(TransactionEventNode)
    all_transaction_events = DjangoFilterConnectionField(TransactionEventNode)

    transaction_item = relay.Node.Field(TransactionItemNode)
    all_transaction_items = DjangoFilterConnectionField(TransactionItemNode)
    
    payment_method = relay.Node.Field(PaymentMethodNode)
    all_payment_methods = DjangoFilterConnectionField(PaymentMethodNode)
    
    def resolve_all_payment_methods(self, info, **kwargs):
        user = info.context.user
        if not user.is_authenticated:
            return PaymentMethod.objects.none()
        return PaymentMethod.objects.filter(user=user, is_active=True)


