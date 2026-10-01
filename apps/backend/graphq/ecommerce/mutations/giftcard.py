import graphene
from graphene import relay
from graphql_relay import from_global_id

from ecommerce.models.giftcard import GiftCard, GiftCardEvent, GiftCardTag

from graphq.ecommerce.types.giftcard import GiftCardEventNode, GiftCardTagNode, GiftCardNode

# ------------------------
# GiftCardTag Mutations
# ------------------------

class CreateGiftCardTag(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)

    gift_card_tag = graphene.Field(GiftCardTagNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        tag = GiftCardTag.objects.create(name=input["name"])
        return CreateGiftCardTag(gift_card_tag=tag)


class UpdateGiftCardTag(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)

    gift_card_tag = graphene.Field(GiftCardTagNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        tag_id = from_global_id(input["id"])[1]
        tag = GiftCardTag.objects.get(id=tag_id)
        if "name" in input:
            tag.name = input["name"]
        tag.save()
        return UpdateGiftCardTag(gift_card_tag=tag)


class DeleteGiftCardTag(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        tag_id = from_global_id(input["id"])[1]
        GiftCardTag.objects.filter(id=tag_id).delete()
        return DeleteGiftCardTag(success=True)


# ------------------------
# GiftCard Mutations
# ------------------------

class CreateGiftCard(relay.ClientIDMutation):
    class Input:
        code = graphene.String(required=True)
        is_active = graphene.Boolean(required=False)
        currency = graphene.String(required=True)
        initial_balance_amount = graphene.Decimal(required=True)
        current_balance_amount = graphene.Decimal(required=True)
        expiry_date = graphene.Date(required=False)

    gift_card = graphene.Field(GiftCardNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        gift_card = GiftCard.objects.create(
            code=input["code"],
            is_active=input.get("is_active", True),
            currency=input["currency"],
            initial_balance_amount=input["initial_balance_amount"],
            current_balance_amount=input["current_balance_amount"],
            expiry_date=input.get("expiry_date"),
        )
        return CreateGiftCard(gift_card=gift_card)


class UpdateGiftCard(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        is_active = graphene.Boolean(required=False)
        current_balance_amount = graphene.Decimal(required=False)
        expiry_date = graphene.Date(required=False)

    gift_card = graphene.Field(GiftCardNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        gift_card_id = from_global_id(input["id"])[1]
        gift_card = GiftCard.objects.get(id=gift_card_id)
        for field, value in input.items():
            if field != "id" and value is not None:
                setattr(gift_card, field, value)
        gift_card.save()
        return UpdateGiftCard(gift_card=gift_card)


class DeleteGiftCard(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        gift_card_id = from_global_id(input["id"])[1]
        GiftCard.objects.filter(id=gift_card_id).delete()
        return DeleteGiftCard(success=True)


# ------------------------
# GiftCardEvent Mutations
# ------------------------

class CreateGiftCardEvent(relay.ClientIDMutation):
    class Input:
        type = graphene.String(required=True)
        gift_card_id = graphene.ID(required=True)
        order_id = graphene.ID(required=False)

    gift_card_event = graphene.Field(GiftCardEventNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        gift_card = GiftCard.objects.get(id=from_global_id(input["gift_card_id"])[1])
        event = GiftCardEvent.objects.create(
            type=input["type"],
            gift_card=gift_card,
            order_id=from_global_id(input["order_id"])[1]
            if input.get("order_id")
            else None,
            user=info.context.user if info.context.user.is_authenticated else None,
        )
        return CreateGiftCardEvent(gift_card_event=event)


class DeleteGiftCardEvent(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        event_id = from_global_id(input["id"])[1]
        GiftCardEvent.objects.filter(id=event_id).delete()
        return DeleteGiftCardEvent(success=True)


# ------------------------
# Root Mutation
# ------------------------

class GiftCardMutations(graphene.ObjectType):
    create_gift_card_tag = CreateGiftCardTag.Field()
    update_gift_card_tag = UpdateGiftCardTag.Field()
    delete_gift_card_tag = DeleteGiftCardTag.Field()

    create_gift_card = CreateGiftCard.Field()
    update_gift_card = UpdateGiftCard.Field()
    delete_gift_card = DeleteGiftCard.Field()

    create_gift_card_event = CreateGiftCardEvent.Field()
    delete_gift_card_event = DeleteGiftCardEvent.Field()
