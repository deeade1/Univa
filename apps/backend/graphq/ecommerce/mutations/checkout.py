# graphq/checkout/mutations.py
import graphene
from django.db import transaction
from graphene import DateTime, relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from ecommerce.models.checkout import Checkout, CheckoutLine
from core.exceptions import InsufficientStock
from univa_jwt.decorators import login_required

from ecommerce.services.warehouse.services import WarehouseService 
from graphq.ecommerce.types.checkout import CheckoutLineNode, CheckoutNode
from graphq.ecommerce.types.order import OrderNode

# --- Checkout Mutations ---
class CreateCheckout(relay.ClientIDMutation):
    class Input:
        created_at = DateTime(required=False) 
        last_change = DateTime(required=False)
        completing_started_at = DateTime(required=False)
        last_transaction_modified_at = DateTime(required=False)
        automatically_refundable = graphene.Boolean(required=False)
        user = graphene.ID(required=False)
        email = graphene.ID(required=False)
        token = graphene.String(required=False)
        channel = graphene.ID(required=False)
        billing_address = graphene.ID(required=False)
        shipping_address = graphene.ID(required=False)
        shipping_method = graphene.ID(required=False)
        collection_point = graphene.ID(required=False)
        note = graphene.String(required=False)
        currency = graphene.String(required=False)
        country = graphene.String(required=False)
        total_net_amount = graphene.Float(required=False)
        total_gross_amount = graphene.Float(required=False)
        total = graphene.Float(required=False)
        base_total_amount = graphene.Float(required=False)
        base_total = graphene.Float(required=False)

        subtotal_net_amount = graphene.Float(required=False)
        subtotal_gross_amount = graphene.Float(required=False)
        subtotal = graphene.Float(required=False)
        
        base_subtotal = graphene.Float(required=False)
        shipping_price_net_amount = graphene.Float(required=False)
        shipping_price_gross_amount = graphene.Float(required=False)
        shipping_price = graphene.Float(required=False)
        shipping_tax_rate = graphene.Float(required=False)
        authorize_status = graphene.String(required=False)
        charge_status = graphene.String(required=False)
        price_expiration = DateTime(required=False)
        discount_amount = graphene.Float(required=False)
        discount = graphene.Float(required=False)
        discount_name = graphene.String(required=False)
        translated_discount_name = graphene.String(required=False)
        gift_cards = graphene.List(graphene.ID, required=False)
        voucher_code = graphene.String(required=False)
        is_voucher_usage_increased = graphene.Boolean(required=False)
        redirect_url = graphene.String(required=False)
        tracking_code = graphene.String(required=False)
        language_code = graphene.String(required=False)
        tax_exemption = graphene.Boolean(required=False)
        tax_error = graphene.String(required=False)


    checkout = graphene.Field(CheckoutNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        # Decode global IDs
        user_id = None
        channel_id = None
        
        if input.get('user'):
            user_id = from_global_id(input['user'])[1]
        if input.get('channel'):
            channel_id = from_global_id(input['channel'])[1]
        
        # Handle optional relationships
        user = User.objects.get(pk=user_id) if user_id else None
        channel = Channel.objects.get(pk=channel_id) if channel_id else None
        
        # Handle address IDs
        billing_address = None
        shipping_address = None
        shipping_method = None
        collection_point = None
        
        if input.get('billing_address'):
            billing_address = from_global_id(input['billing_address'])[1]
        if input.get('shipping_address'):
            shipping_address = from_global_id(input['shipping_address'])[1]
        if input.get('shipping_method'):
            shipping_method = from_global_id(input['shipping_method'])[1]
        if input.get('collection_point'):
            collection_point = from_global_id(input['collection_point'])[1]
        
        # Handle gift cards
        gift_cards = []
        if input.get('gift_cards'):
            gift_cards = [from_global_id(gc)[1] for gc in input['gift_cards']]

        checkout = Checkout.objects.create(
            created_at=input.get('created_at'),
            last_change=input.get('last_change'),
            completing_started_at=input.get('completing_started_at'),
            last_transaction_modified_at=input.get('last_transaction_modified_at'),
            automatically_refundable=input.get('automatically_refundable', False),
            user=user,
            email=input.get('email'),
            token=input.get('token'),
            channel=channel,
            billing_address_id=billing_address,
            shipping_address_id=shipping_address,
            shipping_method_id=shipping_method,
            collection_point_id=collection_point,
            note=input.get('note', ''),
            currency=input.get('currency'),
            country=input.get('country'),
            total_net_amount=input.get('total_net_amount', 0),
            total_gross_amount=input.get('total_gross_amount', 0),
            total=input.get('total', 0),
            base_total_amount=input.get('base_total_amount', 0),
            base_total=input.get('base_total', 0),
            subtotal_net_amount=input.get('subtotal_net_amount', 0),
            subtotal_gross_amount=input.get('subtotal_gross_amount', 0),
            subtotal=input.get('subtotal', 0),
            base_subtotal=input.get('base_subtotal', 0),
            shipping_price_net_amount=input.get('shipping_price_net_amount', 0),
            shipping_price_gross_amount=input.get('shipping_price_gross_amount', 0),
            shipping_price=input.get('shipping_price', 0),
            shipping_tax_rate=input.get('shipping_tax_rate', 0),
            authorize_status=input.get('authorize_status', 'none'),
            charge_status=input.get('charge_status', 'none'),
            price_expiration=input.get('price_expiration'),
            discount_amount=input.get('discount_amount', 0),
            discount=input.get('discount', 0),
            discount_name=input.get('discount_name'),
            translated_discount_name=input.get('translated_discount_name'),
            voucher_code=input.get('voucher_code'),
            is_voucher_usage_increased=input.get('is_voucher_usage_increased', False),
            redirect_url=input.get('redirect_url'),
            tracking_code=input.get('tracking_code'),
            language_code=input.get('language_code', 'en'),
            tax_exemption=input.get('tax_exemption', False),
            tax_error=input.get('tax_error')
        )
        
        # Handle many-to-many gift cards
        if gift_cards:
            checkout.gift_cards.set(gift_cards)
        
        return CreateCheckout(checkout=checkout)

class UpdateCheckout(relay.ClientIDMutation):
    class Input:
        created_at = DateTime(required=False) 
        last_change = DateTime(required=False)
        completing_started_at = DateTime(required=False)
        last_transaction_modified_at = DateTime(required=False)
        automatically_refundable = graphene.Boolean(required=False)
        user = graphene.ID(required=False)
        email = graphene.ID(required=False)
        token = graphene.String(required=False)
        channel = graphene.ID(required=False)
        billing_address = graphene.ID(required=False)
        shipping_address = graphene.ID(required=False)
        shipping_method = graphene.ID(required=False)
        collection_point = graphene.ID(required=False)
        note = graphene.String(required=False)
        currency = graphene.String(required=False)
        country = graphene.String(required=False)
        total_net_amount = graphene.Float(required=False)
        total_gross_amount = graphene.Float(required=False)
        total = graphene.Float(required=False)
        base_total_amount = graphene.Float(required=False)
        base_total = graphene.Float(required=False)

        subtotal_net_amount = graphene.Float(required=False)
        subtotal_gross_amount = graphene.Float(required=False)
        subtotal = graphene.Float(required=False)
        
        base_subtotal = graphene.Float(required=False)
        shipping_price_net_amount = graphene.Float(required=False)
        shipping_price_gross_amount = graphene.Float(required=False)
        shipping_price = graphene.Float(required=False)
        shipping_tax_rate = graphene.Float(required=False)
        authorize_status = graphene.String(required=False)
        charge_status = graphene.String(required=False)
        price_expiration = DateTime(required=False)
        discount_amount = graphene.Float(required=False)
        discount = graphene.Float(required=False)
        discount_name = graphene.String(required=False)
        translated_discount_name = graphene.String(required=False)
        gift_cards = graphene.List(graphene.ID, required=False)
        voucher_code = graphene.String(required=False)
        is_voucher_usage_increased = graphene.Boolean(required=False)
        redirect_url = graphene.String(required=False)
        tracking_code = graphene.String(required=False)
        language_code = graphene.String(required=False)
        tax_exemption = graphene.Boolean(required=False)
        tax_error = graphene.String(required=False)

    checkout = graphene.Field(CheckoutNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **input):
        try:
            checkout = Checkout.objects.get(pk=id)
        except Checkout.DoesNotExist:
            raise GraphQLError("Checkout not found")

        for field, value in input.items():
            setattr(checkout, field, value)
        checkout.save()
        return UpdateCheckout(checkout=checkout)


class DeleteCheckout(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            Checkout.objects.get(pk=id).delete()
            return DeleteCheckout(success=True)
        except Checkout.DoesNotExist:
            return DeleteCheckout(success=False)


class DeleteCheckoutLine(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            CheckoutLine.objects.get(pk=id).delete()
            return DeleteCheckoutLine(success=True)
        except CheckoutLine.DoesNotExist:
            return DeleteCheckoutLine(success=False)


# --- Enhanced CheckoutLine Mutations with Stock Validation ---
class CreateCheckoutLine(relay.ClientIDMutation):
    class Input:
        id = graphene.UUID()
        created_at = DateTime(required=True)
        checkout_id = graphene.ID()
        variant_id = graphene.ID()
        quantity = graphene.Int()
        is_gift = graphene.Boolean()
        price_override = graphene.String()
        currency = graphene.String()
        total_price_net_amount = graphene.Int()
        total_price_gross_amount = graphene.Int()
        total_price = graphene.Int()
        tax_rate = graphene.Int()

    line = graphene.Field(CheckoutLineNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            checkout_id = from_global_id(input.get('checkout_id'))[1]
            variant_id = from_global_id(input.get('variant_id'))[1]
            
            checkout = Checkout.objects.get(pk=checkout_id)
            variant = ProductVariant.objects.get(pk=variant_id)
            quantity = input.get('quantity', 1)

            # ✅ Use WarehouseService instead of direct imports
            WarehouseService.check_stock_and_preorder_quantity(
                variant=variant,
                country_code=checkout.country or settings.DEFAULT_COUNTRY,
                channel_slug=checkout.channel.slug,
                quantity=quantity,
                checkout_lines=checkout.lines.all(),
                check_reservations=True
            )

            # Create checkout line
            line = CheckoutLine.objects.create(
                created_at=input.get('created_at'),
                checkout_id=checkout_id,
                variant_id=variant_id,
                quantity=quantity,
                is_gift=input.get('is_gift', False),
                price_override=input.get('price_override'),
                currency=input.get('currency', checkout.currency),
                total_price_net_amount=input.get('total_price_net_amount', 0),
                total_price_gross_amount=input.get('total_price_gross_amount', 0),
                total_price=input.get('total_price', 0),
                tax_rate=input.get('tax_rate', 0),
            )

            # ✅ Reserve stock using WarehouseService
            WarehouseService.reserve_stocks_and_preorders(
                checkout_lines=[line],
                lines_to_update_reservation_time=[],
                variants=[variant],
                country_code=checkout.country or settings.DEFAULT_COUNTRY,
                channel=checkout.channel,
                length_in_minutes=get_reservation_length(info.context.site, info.context.user),
                replace=False
            )

            return CreateCheckoutLine(line=line)

        except InsufficientStock as e:
            raise GraphQLError(f"Insufficient stock: {str(e)}")
        except Exception as e:
            raise GraphQLError(f"Failed to create checkout line: {str(e)}")


class UpdateCheckoutLine(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        quantity = graphene.Int()

    line = graphene.Field(CheckoutLineNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, **input):
        try:
            line = CheckoutLine.objects.get(pk=id)
            checkout = line.checkout
            new_quantity = input.get('quantity')

            if new_quantity is not None and new_quantity != line.quantity:
                # ✅ Check stock availability using WarehouseService
                WarehouseService.check_stock_and_preorder_quantity(
                    variant=line.variant,
                    country_code=checkout.country or settings.DEFAULT_COUNTRY,
                    channel_slug=checkout.channel.slug,
                    quantity=new_quantity,
                    checkout_lines=checkout.lines.all(),
                    check_reservations=True
                )

                line.quantity = new_quantity
                line.save()

                # ✅ Update reservations using WarehouseService
                WarehouseService.reserve_stocks_and_preorders(
                    checkout_lines=[line],
                    lines_to_update_reservation_time=[line],
                    variants=[line.variant],
                    country_code=checkout.country or settings.DEFAULT_COUNTRY,
                    channel=checkout.channel,
                    length_in_minutes=get_reservation_length(info.context.site, info.context.user),
                    replace=True
                )

            return UpdateCheckoutLine(line=line)

        except InsufficientStock as e:
            raise GraphQLError(f"Insufficient stock: {str(e)}")
        except CheckoutLine.DoesNotExist:
            raise GraphQLError("Checkout line not found")


class CompleteCheckout(relay.ClientIDMutation):
    class Input:
        checkout_id = graphene.ID(required=True)
        redirect_url = graphene.String(required=False)

    order = graphene.Field(OrderNode)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, checkout_id, **input):
        try:
            checkout = Checkout.objects.get(pk=from_global_id(checkout_id)[1])
            lines = list(checkout.lines.all())
            variants = [line.variant for line in lines]
            quantities = [line.quantity for line in lines]

            # --- Bulk stock + preorder check using WarehouseService ---
            try:
                WarehouseService.check_stock_and_preorder_quantity_bulk(
                    variants=variants,
                    quantities=quantities,
                    country_code=checkout.country or settings.DEFAULT_COUNTRY,
                    channel_slug=checkout.channel.slug,
                    existing_lines=lines,
                    check_reservations=True,
                    replace=True
                )
            except InsufficientStock as e:
                errors = [
                    f"Insufficient stock for {stock.variant.name}: {stock.available_quantity}"
                    for stock in e.insufficient_stock_data
                ]
                return CompleteCheckout(order=None, success=False, errors=errors)

            # --- Complete checkout using existing logic ---
            from apps.backend.checkout.complete_checkout import complete_checkout

            order, action_required, action_data = complete_checkout(
                manager=info.context.plugins,
                checkout_info=info.context.checkout_info,
                lines=lines,
                payment_data={},
                store_source=False,
                user=info.context.user,
                redirect_url=input.get("redirect_url"),
            )

            if order:
                return CompleteCheckout(order=order, success=True, errors=[])
            else:
                return CompleteCheckout(
                    order=None,
                    success=False,
                    errors=["Checkout completion failed"]
                )

        except Checkout.DoesNotExist:
            return CompleteCheckout(
                order=None,
                success=False,
                errors=["Checkout not found"]
            )
        except Exception as e:
            return CompleteCheckout(
                order=None,
                success=False,
                errors=[f"Checkout completion failed: {str(e)}"]
            )


class ValidateCheckoutStock(relay.ClientIDMutation):
    class Input:
        checkout_id = graphene.ID(required=True)

    is_valid = graphene.Boolean()
    available_quantities = graphene.JSONString()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate_and_get_payload(cls, root, info, checkout_id):
        try:
            checkout = Checkout.objects.get(pk=from_global_id(checkout_id)[1])
            lines = list(checkout.lines.all())

            if not lines:
                return ValidateCheckoutStock(
                    is_valid=True,
                    available_quantities={},
                    errors=[]
                )

            variants = [line.variant for line in lines]
            quantities = [line.quantity for line in lines]

            # ✅ Use WarehouseService for bulk check
            try:
                available_quantities = WarehouseService.check_bulk_availability(
                    variants=variants,
                    quantities=quantities,
                    channel=checkout.channel,
                    country_code=checkout.country or settings.DEFAULT_COUNTRY
                )

                is_valid = all(qty['sufficient'] for qty in available_quantities.values())
                return ValidateCheckoutStock(
                    is_valid=is_valid,
                    available_quantities=available_quantities,
                    errors=[] if is_valid else ["Some items are out of stock"]
                )

            except InsufficientStock as e:
                # Collect unavailable quantities per variant
                available_quantities = {
                    stock.variant.id: stock.available_quantity
                    for stock in e.insufficient_stock_data
                }
                errors = [
                    f"Insufficient stock for {stock.variant.name}: {stock.available_quantity}"
                    for stock in e.insufficient_stock_data
                ]
                return ValidateCheckoutStock(
                    is_valid=False,
                    available_quantities=available_quantities,
                    errors=errors
                )

        except Checkout.DoesNotExist:
            return ValidateCheckoutStock(
                is_valid=False,
                available_quantities={},
                errors=["Checkout not found"]
            )
        except Exception as e:
            raise GraphQLError(f"Error validating checkout stock: {str(e)}")


# --- Reservation Management ---
class RefreshCheckoutReservations(relay.ClientIDMutation):
    class Input:
        checkout_id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, checkout_id):
        try:
            checkout = Checkout.objects.get(pk=from_global_id(checkout_id)[1])
            lines = checkout.lines.all()
            variants = [line.variant for line in lines]

            # ✅ Refresh reservations using WarehouseService
            WarehouseService.reserve_stocks_and_preorders(
                checkout_lines=lines,
                lines_to_update_reservation_time=lines,
                variants=variants,
                country_code=checkout.country or settings.DEFAULT_COUNTRY,
                channel=checkout.channel,
                length_in_minutes=get_reservation_length(info.context.site, info.context.user),
                replace=True
            )

            return RefreshCheckoutReservations(success=True)

        except Exception as e:
            raise GraphQLError(f"Failed to refresh reservations: {str(e)}")


class CheckoutMutations(graphene.ObjectType):
    create_checkout = CreateCheckout.Field()
    update_checkout = UpdateCheckout.Field()   
    delete_checkout = DeleteCheckout.Field()

    create_checkout_line = CreateCheckoutLine.Field()
    update_checkout_line = UpdateCheckoutLine.Field()
    delete_checkout_line = DeleteCheckoutLine.Field()
    
    # New enhanced mutations
    complete_checkout = CompleteCheckout.Field()
    validate_checkout_stock = ValidateCheckoutStock.Field()
    refresh_checkout_reservations = RefreshCheckoutReservations.Field()