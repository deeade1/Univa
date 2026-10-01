from typing import Dict, cast

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from graphene import relay
from graphql_relay import from_global_id
from graphql import GraphQLError
from ecommerce.models.order import Order
from core import JobStatus

from invoice.models import Invoice
from graphq.ecommerce.types.order import OrderNode
from accounts.models import User
from graphq.invoice.types import InvoiceNode
from invoice import models

User = get_user_model()


def validate_order(order):
    if order.is_draft() or order.is_unconfirmed() or order.is_expired():
        raise ValidationError({
            "orderId": ValidationError(
                "Cannot perform operation on draft, unconfirmed or expired order.",
                code=InvoiceErrorCode.INVALID_STATUS.value,
            )
        })
    if not order.billing_address:
        raise ValidationError({
            "orderId": ValidationError(
                "Order must have a billing address.",
                code=InvoiceErrorCode.NOT_READY.value,
            )
        })


def validate_invoice_ready(invoice):
    errors = {}
    if invoice.status != JobStatus.SUCCESS:
        errors["invoice"] = ValidationError(
            "Invoice is not ready to be sent.",
            code=InvoiceErrorCode.NOT_READY.value,
        )
    if not invoice.url:
        errors["url"] = ValidationError(
            "Invoice must have a URL.",
            code=InvoiceErrorCode.URL_NOT_SET.value,
        )
    if not invoice.number:
        errors["number"] = ValidationError(
            "Invoice must have a number.",
            code=InvoiceErrorCode.NUMBER_NOT_SET.value,
        )
    if not invoice.order.get_customer_email():
        errors["order"] = ValidationError(
            "Order must have a customer email.",
            code=InvoiceErrorCode.EMAIL_NOT_SET.value,
        )
    if errors:
        raise ValidationError(errors)


# --- Mutations ---

class InvoiceRequest(relay.ClientIDMutation):
    class Input:
        order_id = graphene.ID(required=True)
        number = graphene.String()

    invoice = graphene.Field(InvoiceNode)
    order = graphene.Field(OrderNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **data):
        order = Order.objects.get(pk=from_global_id(data["order_id"])[1])
        validate_order(order)

        number = data.get("number")
        invoice = models.Invoice.objects.create(order=order, number=number)

        invoice = info.context.user.invoice_request(order, invoice, number)
        if invoice.status == JobStatus.SUCCESS:
            order_events.invoice_generated_event(order, info.context.user, invoice.number)
        
        return InvoiceRequest(invoice=invoice, order=order)


class InvoiceCreate(relay.ClientIDMutation):
    class Input:
        order_id = graphene.ID(required=True)
        number = graphene.String(required=True)
        url = graphene.String(required=True)
        metadata = graphene.List(graphene.String)
        private_metadata = graphene.List(graphene.String)

    invoice = graphene.Field(InvoiceNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **data):
        # ✅ FIX: Properly get order
        _, order_pk = from_global_id(data["order_id"])
        order = Order.objects.get(pk=order_pk)
        validate_order(order)

        invoice = models.Invoice(
            order=order,
            number=data["number"],
            external_url=data["url"],
            status=JobStatus.SUCCESS
        )
        invoice.save()

        return InvoiceCreate(invoice=invoice)




class InvoiceRequestDelete(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    invoice = graphene.Field(InvoiceNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, invoice_id = from_global_id(id)
            invoice = Invoice.objects.get(pk=invoice_id)
        except Invoice.DoesNotExist:
            raise GraphQLError("Invoice not found")
        except Exception:
            raise GraphQLError("Invalid invoice ID")

        invoice.status = JobStatus.PENDING
        invoice.save(update_fields=["status", "updated_at"])

        return InvoiceRequestDelete(invoice=invoice)



class InvoiceDelete(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    invoice = graphene.Field(InvoiceNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, invoice_id = from_global_id(id)
            invoice = Invoice.objects.get(pk=invoice_id)
        except Invoice.DoesNotExist:
            raise GraphQLError("Invoice not found")
        except Exception:
            raise GraphQLError("Invalid invoice ID")

        invoice.delete()

        return InvoiceDelete(invoice=None)


class InvoiceUpdate(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        number = graphene.String()
        url = graphene.String()
        metadata = graphene.List(graphene.String)
        private_metadata = graphene.List(graphene.String)

    invoice = graphene.Field(InvoiceNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **data):
        # ✅ FIX: Properly get invoice
        _, invoice_pk = from_global_id(data["id"])
        invoice = models.Invoice.objects.get(pk=invoice_pk)

        if data.get("number"):
            invoice.number = data["number"]
        if data.get("url"):
            invoice.external_url = data["url"]
        if data.get("metadata"):
            invoice.metadata = data["metadata"]
        if data.get("private_metadata"):
            invoice.private_metadata = data["private_metadata"]

        invoice.status = JobStatus.SUCCESS
        invoice.save()

        return InvoiceUpdate(invoice=invoice)

class InvoiceSendNotification(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    invoice = graphene.Field(InvoiceNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, invoice_id = from_global_id(id)
            invoice = Invoice.objects.get(pk=invoice_id)
        except Invoice.DoesNotExist:
            raise GraphQLError("Invoice not found")
        except Exception:
            raise GraphQLError("Invalid invoice ID")

        validate_invoice_ready(invoice)

        manager = get_plugin_manager_promise(info.context).get()

        send_invoice(
            invoice=invoice,
            staff_user=cast(User, info.context.user),
            manager=manager,
        )

        return InvoiceSendNotification(invoice=invoice)


class InvoiceMutations(graphene.ObjectType):
    invoice_request = InvoiceRequest.Field()
    invoice_request_delete = InvoiceRequestDelete.Field()
    invoice_create = InvoiceCreate.Field()
    invoice_delete = InvoiceDelete.Field()
    invoice_update = InvoiceUpdate.Field()
    invoice_send_notification = InvoiceSendNotification.Field()