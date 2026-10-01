import graphene
from graphene import relay
from .types import ContactUsNode
from accounts.models import ContactUs

class SendContactMessageMutation(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        message = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    contact_us = graphene.Field(ContactUsNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        contact_us = ContactUs.objects.create(
            name=input["name"],
            email=input["email"],
            message=input["message"]
        )
        return SendContactMessageMutation(
            success=True,
            message="Your message has been received.",
            contact_us=contact_us,
        )

class ReplyToContactMessageMutation(relay.ClientIDMutation):
    """Admin reply mutation"""

    class Input:
        contact_id = graphene.ID(required=True)
        reply_message = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    contact_us = graphene.Field(ContactUsNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, contact_id, reply_message):
        user = info.context.user
        if not user.is_authenticated or not user.is_staff:
            raise GraphQLError("Permission denied. Admin only.")

        contact_us = ContactUs.objects.get(pk=from_global_id(contact_id)[1])
        if not contact_us:
            raise GraphQLError("Contact message not found.")

        if contact_us.replied:
            raise GraphQLError("This message has already been replied to.")

        contact_us.replied = True
        contact_us.reply_message = reply_message
        contact_us.replied_by = user
        contact_us.replied_at = timezone.now()
        contact_us.save()

        try:
            send_mail(
                subject=f"Reply to your inquiry, {contact_us.name}",
                message=reply_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[contact_us.email],
                fail_silently=False,
            )
            mail_msg = "Reply sent successfully."
        except Exception as e:
            mail_msg = f"Reply saved but email sending failed: {str(e)}"

        return cls(
            success=True,
            message=mail_msg,
            contact_us=contact_us
        )



class SupportMutation(graphene.ObjectType):
    send_contact_message = SendContactMessageMutation.Field()
    reply_to_contact_message = ReplyToContactMessageMutation.Field()
    