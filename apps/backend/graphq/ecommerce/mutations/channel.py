import graphene
from django.utils.text import slugify
from graphene import relay
from graphql_relay import from_global_id

from ecommerce.models.channel import Channel

from graphq.ecommerce.types.channel import ChannelNode


class CreateChannel(relay.ClientIDMutation):
    """Mutation to create a new channel."""
    class Input:
        name = graphene.String(required=True)
        slug = graphene.String(required=True)
        currency_code = graphene.String(required=True)
        default_country = graphene.String(required=True)

    channel = graphene.Field(ChannelNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        channel = Channel.objects.create(
            name=input["name"],
            slug=slugify(input["slug"]),
            currency_code=input["currency_code"],
            default_country=input["default_country"],
        )
        return CreateChannel(channel=channel)


class UpdateChannel(relay.ClientIDMutation):
    """Mutation to update an existing channel."""
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        slug = graphene.String()
        currency_code = graphene.String()
        default_country = graphene.String()

    channel = graphene.Field(ChannelNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        channel = Channel.objects.get(pk=pk)

        for field in ["name", "slug", "currency_code", "default_country"]:
            if field in input and input[field] is not None:
                value = input[field]
                if field == "slug":
                    value = slugify(value)
                setattr(channel, field, value)

        channel.save()
        return UpdateChannel(channel=channel)


class DeleteChannel(relay.ClientIDMutation):
    """Mutation to delete an existing channel."""
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_channel_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            channel = Channel.objects.get(pk=pk)
        except Channel.DoesNotExist:
            raise Exception("Channel not found.")

        deleted_id = input["id"]
        channel.delete()
        return DeleteChannel(ok=True, deleted_channel_id=deleted_id)


class ChannelMutations(graphene.ObjectType):
    create_channel = CreateChannel.Field()
    update_channel = UpdateChannel.Field()
    delete_channel = DeleteChannel.Field()
