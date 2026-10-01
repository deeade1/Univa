import graphene
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.discount import (CheckoutDiscount, CheckoutLineDiscount,
                             OrderDiscount, OrderLineDiscount, Promotion,
                             PromotionRule, Voucher, VoucherCode)
from ecommerce.models.order import Order, OrderLine

from graphq.ecommerce.types.discount import (CheckoutDiscountNode, CheckoutLineDiscountNode,
                    OrderDiscountNode, OrderLineDiscountNode, PromotionNode,
                    PromotionRuleNode, VoucherCodeNode, VoucherNode)


# --- VOUCHER MUTATIONS ---
class CreateVoucher(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)
        code = graphene.String(required=True)
        discount_value_type = graphene.String(required=True)
        discount_value = graphene.Decimal(required=True)
        usage_limit = graphene.Int()
        start_date = graphene.DateTime()
        end_date = graphene.DateTime()
        min_checkout_items_quantity = graphene.Int()
        apply_once_per_order = graphene.Boolean()
        apply_once_per_customer = graphene.Boolean()
        only_for_staff = graphene.Boolean()

    voucher = graphene.Field(VoucherNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input_data):
        voucher = Voucher.objects.create(**input_data)
        return CreateVoucher(voucher=voucher)


class UpdateVoucher(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        code = graphene.String()
        discount_value_type = graphene.String()
        discount_value = graphene.Decimal()
        usage_limit = graphene.Int()
        start_date = graphene.DateTime()
        end_date = graphene.DateTime()
        min_checkout_items_quantity = graphene.Int()
        apply_once_per_order = graphene.Boolean()
        apply_once_per_customer = graphene.Boolean()
        only_for_staff = graphene.Boolean()

    voucher = graphene.Field(VoucherNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **input_data):
        try:
            _, voucher_id = from_global_id(id)
            voucher = Voucher.objects.get(pk=voucher_id)
        except (Exception, Voucher.DoesNotExist):
            raise GraphQLError("Voucher not found")
        
        for field, value in input_data.items():
            if value is not None:
                setattr(voucher, field, value)
        voucher.save()
        
        return UpdateVoucher(voucher=voucher)


class DeleteVoucher(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, voucher_id = from_global_id(id)
            voucher = Voucher.objects.get(pk=voucher_id)
            voucher.delete()
            return DeleteVoucher(success=True)
        except (Exception, Voucher.DoesNotExist):
            raise GraphQLError("Voucher not found")


# --- VOUCHER CODE MUTATIONS ---
class CreateVoucherCode(relay.ClientIDMutation):
    class Input:
        voucher_id = graphene.ID(required=True)
        code = graphene.String(required=True)
        is_active = graphene.Boolean(default=True)

    voucher_code = graphene.Field(VoucherCodeNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, voucher_id, code, is_active=True):
        try:
            _, v_id = from_global_id(voucher_id)
            voucher = Voucher.objects.get(pk=v_id)
        except (Exception, Voucher.DoesNotExist):
            raise GraphQLError("Voucher not found")
        
        voucher_code = VoucherCode.objects.create(
            voucher=voucher, 
            code=code, 
            is_active=is_active
        )
        return CreateVoucherCode(voucher_code=voucher_code)


class DeleteVoucherCode(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, code_id = from_global_id(id)
            voucher_code = VoucherCode.objects.get(pk=code_id)
            voucher_code.delete()
            return DeleteVoucherCode(success=True)
        except (Exception, VoucherCode.DoesNotExist):
            raise GraphQLError("Voucher code not found")


# --- PROMOTION MUTATIONS ---
class CreatePromotion(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)
        description = graphene.String()
        start_date = graphene.DateTime()
        end_date = graphene.DateTime()
        is_active = graphene.Boolean(default=True)

    promotion = graphene.Field(PromotionNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input_data):
        promotion = Promotion.objects.create(**input_data)
        return CreatePromotion(promotion=promotion)


class UpdatePromotion(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        description = graphene.String()
        start_date = graphene.DateTime()
        end_date = graphene.DateTime()
        is_active = graphene.Boolean()

    promotion = graphene.Field(PromotionNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **input_data):
        try:
            _, promotion_id = from_global_id(id)
            promotion = Promotion.objects.get(pk=promotion_id)
        except (Exception, Promotion.DoesNotExist):
            raise GraphQLError("Promotion not found")
        
        for field, value in input_data.items():
            if value is not None:
                setattr(promotion, field, value)
        promotion.save()
        
        return UpdatePromotion(promotion=promotion)


class DeletePromotion(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, promotion_id = from_global_id(id)
            promotion = Promotion.objects.get(pk=promotion_id)
            promotion.delete()
            return DeletePromotion(success=True)
        except (Exception, Promotion.DoesNotExist):
            raise GraphQLError("Promotion not found")


# --- PROMOTION RULE MUTATIONS ---
class CreatePromotionRule(relay.ClientIDMutation):
    class Input:
        promotion_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        description = graphene.String()
        discount_type = graphene.String(required=True)
        discount_value = graphene.Decimal(required=True)
        min_quantity = graphene.Int()
        min_amount = graphene.Decimal()

    rule = graphene.Field(PromotionRuleNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, promotion_id, **input_data):
        try:
            _, p_id = from_global_id(promotion_id)
            promotion = Promotion.objects.get(pk=p_id)
        except (Exception, Promotion.DoesNotExist):
            raise GraphQLError("Invalid promotion ID")
        
        rule = PromotionRule.objects.create(promotion=promotion, **input_data)
        return CreatePromotionRule(rule=rule)


class UpdatePromotionRule(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        description = graphene.String()
        discount_type = graphene.String()
        discount_value = graphene.Decimal()
        min_quantity = graphene.Int()
        min_amount = graphene.Decimal()

    rule = graphene.Field(PromotionRuleNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **input_data):
        try:
            _, rule_id = from_global_id(id)
            rule = PromotionRule.objects.get(pk=rule_id)
        except (Exception, PromotionRule.DoesNotExist):
            raise GraphQLError("Promotion rule not found")
        
        for field, value in input_data.items():
            if value is not None:
                setattr(rule, field, value)
        rule.save()
        
        return UpdatePromotionRule(rule=rule)


class DeletePromotionRule(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, rule_id = from_global_id(id)
            rule = PromotionRule.objects.get(pk=rule_id)
            rule.delete()
            return DeletePromotionRule(success=True)
        except (Exception, PromotionRule.DoesNotExist):
            raise GraphQLError("Promotion rule not found")


# --- CHECKOUT DISCOUNT MUTATIONS ---
class CreateCheckoutDiscount(relay.ClientIDMutation):
    class Input:
        checkout_id = graphene.ID(required=True)
        voucher_id = graphene.ID()
        promotion_rule_id = graphene.ID()
        discount_amount = graphene.Decimal(required=True)
        discount_type = graphene.String(required=True)

    discount = graphene.Field(CheckoutDiscountNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, checkout_id, discount_amount, discount_type, **input_data):
        try:
            _, c_id = from_global_id(checkout_id)
            checkout = Checkout.objects.get(pk=c_id)
        except (Exception, Checkout.DoesNotExist):
            raise GraphQLError("Invalid checkout ID")

        voucher = None
        if 'voucher_id' in input_data:
            try:
                _, v_id = from_global_id(input_data['voucher_id'])
                voucher = Voucher.objects.get(pk=v_id)
            except (Exception, Voucher.DoesNotExist):
                raise GraphQLError("Invalid voucher ID")

        promotion_rule = None
        if 'promotion_rule_id' in input_data:
            try:
                _, pr_id = from_global_id(input_data['promotion_rule_id'])
                promotion_rule = PromotionRule.objects.get(pk=pr_id)
            except (Exception, PromotionRule.DoesNotExist):
                raise GraphQLError("Invalid promotion rule ID")

        discount = CheckoutDiscount.objects.create(
            checkout=checkout,
            voucher=voucher,
            promotion_rule=promotion_rule,
            discount_amount=discount_amount,
            discount_type=discount_type
        )
        return CreateCheckoutDiscount(discount=discount)


class UpdateCheckoutDiscount(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        discount_amount = graphene.Decimal()
        discount_type = graphene.String()

    discount = graphene.Field(CheckoutDiscountNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **input_data):
        try:
            _, discount_id = from_global_id(id)
            discount = CheckoutDiscount.objects.get(pk=discount_id)
        except (Exception, CheckoutDiscount.DoesNotExist):
            raise GraphQLError("Checkout discount not found")

        for field, value in input_data.items():
            if value is not None:
                setattr(discount, field, value)
        discount.save()
        
        return UpdateCheckoutDiscount(discount=discount)


class DeleteCheckoutDiscount(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, discount_id = from_global_id(id)
            discount = CheckoutDiscount.objects.get(pk=discount_id)
            discount.delete()
            return DeleteCheckoutDiscount(success=True)
        except (Exception, CheckoutDiscount.DoesNotExist):
            raise GraphQLError("Checkout discount not found")


# --- CHECKOUT LINE DISCOUNT MUTATIONS ---
class CreateCheckoutLineDiscount(relay.ClientIDMutation):
    class Input:
        line_id = graphene.ID(required=True)
        promotion_rule_id = graphene.ID()
        discount_amount = graphene.Decimal(required=True)
        discount_type = graphene.String(required=True)

    discount = graphene.Field(CheckoutLineDiscountNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, line_id, discount_amount, discount_type, **input_data):
        try:
            _, l_id = from_global_id(line_id)
            line = CheckoutLine.objects.get(pk=l_id)
        except (Exception, CheckoutLine.DoesNotExist):
            raise GraphQLError("Invalid checkout line ID")

        promotion_rule = None
        if 'promotion_rule_id' in input_data:
            try:
                _, pr_id = from_global_id(input_data['promotion_rule_id'])
                promotion_rule = PromotionRule.objects.get(pk=pr_id)
            except (Exception, PromotionRule.DoesNotExist):
                raise GraphQLError("Invalid promotion rule ID")

        discount = CheckoutLineDiscount.objects.create(
            line=line,
            promotion_rule=promotion_rule,
            discount_amount=discount_amount,
            discount_type=discount_type
        )
        return CreateCheckoutLineDiscount(discount=discount)


class UpdateCheckoutLineDiscount(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        discount_amount = graphene.Decimal()
        discount_type = graphene.String()

    discount = graphene.Field(CheckoutLineDiscountNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **input_data):
        try:
            _, discount_id = from_global_id(id)
            discount = CheckoutLineDiscount.objects.get(pk=discount_id)
        except (Exception, CheckoutLineDiscount.DoesNotExist):
            raise GraphQLError("Checkout line discount not found")

        for field, value in input_data.items():
            if value is not None:
                setattr(discount, field, value)
        discount.save()
        
        return UpdateCheckoutLineDiscount(discount=discount)


class DeleteCheckoutLineDiscount(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, discount_id = from_global_id(id)
            discount = CheckoutLineDiscount.objects.get(pk=discount_id)
            discount.delete()
            return DeleteCheckoutLineDiscount(success=True)
        except (Exception, CheckoutLineDiscount.DoesNotExist):
            raise GraphQLError("Checkout line discount not found")


# --- ORDER DISCOUNT MUTATIONS ---
class CreateOrderDiscount(relay.ClientIDMutation):
    class Input:
        order_id = graphene.ID(required=True)
        voucher_id = graphene.ID()
        promotion_rule_id = graphene.ID()
        discount_amount = graphene.Decimal(required=True)
        discount_type = graphene.String(required=True)

    discount = graphene.Field(OrderDiscountNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, order_id, discount_amount, discount_type, **input_data):
        try:
            _, o_id = from_global_id(order_id)
            order = Order.objects.get(pk=o_id)
        except (Exception, Order.DoesNotExist):
            raise GraphQLError("Invalid order ID")

        voucher = None
        if 'voucher_id' in input_data:
            try:
                _, v_id = from_global_id(input_data['voucher_id'])
                voucher = Voucher.objects.get(pk=v_id)
            except (Exception, Voucher.DoesNotExist):
                raise GraphQLError("Invalid voucher ID")

        promotion_rule = None
        if 'promotion_rule_id' in input_data:
            try:
                _, pr_id = from_global_id(input_data['promotion_rule_id'])
                promotion_rule = PromotionRule.objects.get(pk=pr_id)
            except (Exception, PromotionRule.DoesNotExist):
                raise GraphQLError("Invalid promotion rule ID")

        discount = OrderDiscount.objects.create(
            order=order,
            voucher=voucher,
            promotion_rule=promotion_rule,
            discount_amount=discount_amount,
            discount_type=discount_type
        )
        return CreateOrderDiscount(discount=discount)


class UpdateOrderDiscount(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        discount_amount = graphene.Decimal()
        discount_type = graphene.String()

    discount = graphene.Field(OrderDiscountNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **input_data):
        try:
            _, discount_id = from_global_id(id)
            discount = OrderDiscount.objects.get(pk=discount_id)
        except (Exception, OrderDiscount.DoesNotExist):
            raise GraphQLError("Order discount not found")

        for field, value in input_data.items():
            if value is not None:
                setattr(discount, field, value)
        discount.save()
        
        return UpdateOrderDiscount(discount=discount)


class DeleteOrderDiscount(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, discount_id = from_global_id(id)
            discount = OrderDiscount.objects.get(pk=discount_id)
            discount.delete()
            return DeleteOrderDiscount(success=True)
        except (Exception, OrderDiscount.DoesNotExist):
            raise GraphQLError("Order discount not found")


# --- ORDER LINE DISCOUNT MUTATIONS ---
class CreateOrderLineDiscount(relay.ClientIDMutation):
    class Input:
        order_line_id = graphene.ID(required=True)
        promotion_rule_id = graphene.ID()
        discount_amount = graphene.Decimal(required=True)
        discount_type = graphene.String(required=True)

    discount = graphene.Field(OrderLineDiscountNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, order_line_id, discount_amount, discount_type, **input_data):
        try:
            _, ol_id = from_global_id(order_line_id)
            line = OrderLine.objects.get(pk=ol_id)
        except (Exception, OrderLine.DoesNotExist):
            raise GraphQLError("Invalid order line ID")

        promotion_rule = None
        if 'promotion_rule_id' in input_data:
            try:
                _, pr_id = from_global_id(input_data['promotion_rule_id'])
                promotion_rule = PromotionRule.objects.get(pk=pr_id)
            except (Exception, PromotionRule.DoesNotExist):
                raise GraphQLError("Invalid promotion rule ID")

        discount = OrderLineDiscount.objects.create(
            line=line,
            promotion_rule=promotion_rule,
            discount_amount=discount_amount,
            discount_type=discount_type
        )
        return CreateOrderLineDiscount(discount=discount)


class UpdateOrderLineDiscount(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        discount_amount = graphene.Decimal()
        discount_type = graphene.String()

    discount = graphene.Field(OrderLineDiscountNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **input_data):
        try:
            _, discount_id = from_global_id(id)
            discount = OrderLineDiscount.objects.get(pk=discount_id)
        except (Exception, OrderLineDiscount.DoesNotExist):
            raise GraphQLError("Order line discount not found")

        for field, value in input_data.items():
            if value is not None:
                setattr(discount, field, value)
        discount.save()
        
        return UpdateOrderLineDiscount(discount=discount)


class DeleteOrderLineDiscount(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            _, discount_id = from_global_id(id)
            discount = OrderLineDiscount.objects.get(pk=discount_id)
            discount.delete()
            return DeleteOrderLineDiscount(success=True)
        except (Exception, OrderLineDiscount.DoesNotExist):
            raise GraphQLError("Order line discount not found")


# --- Root Mutation ---
class DiscountMutations(graphene.ObjectType):
    # Voucher
    create_voucher = CreateVoucher.Field()
    update_voucher = UpdateVoucher.Field()
    delete_voucher = DeleteVoucher.Field()

    # Voucher Code
    create_voucher_code = CreateVoucherCode.Field()
    delete_voucher_code = DeleteVoucherCode.Field()

    # Promotion
    create_promotion = CreatePromotion.Field()
    update_promotion = UpdatePromotion.Field()
    delete_promotion = DeletePromotion.Field()

    # Promotion Rule
    create_promotion_rule = CreatePromotionRule.Field()
    update_promotion_rule = UpdatePromotionRule.Field()
    delete_promotion_rule = DeletePromotionRule.Field()
    
    # Checkout Discounts
    create_checkout_discount = CreateCheckoutDiscount.Field()
    update_checkout_discount = UpdateCheckoutDiscount.Field()
    delete_checkout_discount = DeleteCheckoutDiscount.Field()

    # Checkout Line Discounts
    create_checkout_line_discount = CreateCheckoutLineDiscount.Field()
    update_checkout_line_discount = UpdateCheckoutLineDiscount.Field()
    delete_checkout_line_discount = DeleteCheckoutLineDiscount.Field()

    # Order Discounts
    create_order_discount = CreateOrderDiscount.Field()
    update_order_discount = UpdateOrderDiscount.Field()
    delete_order_discount = DeleteOrderDiscount.Field()

    # Order Line Discounts
    create_order_line_discount = CreateOrderLineDiscount.Field()
    update_order_line_discount = UpdateOrderLineDiscount.Field()
    delete_order_line_discount = DeleteOrderLineDiscount.Field()