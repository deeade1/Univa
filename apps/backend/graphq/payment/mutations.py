import graphene
from graphene import relay
from graphql import GraphQLError

from graphq.payment.types import (PaymentNode, TransactionEventNode,
                                  TransactionItemNode, TransactionNode, PaymentMethodNode)
from payment.models import (Payment, Transaction, TransactionEvent,
                            TransactionItem)


# ---------- BASE HELPER ----------
def get_object(model, id):
    try:
        return model.objects.get(pk=id)
    except model.DoesNotExist:
        raise GraphQLError(f"{model.__name__} with ID {id} does not exist.")


# ---------- PAYMENT ----------
class CreatePayment(relay.ClientIDMutation):
    class Input:
        gateway = graphene.String(required=True)
        currency = graphene.String(required=True)
        order_id = graphene.ID(required=False)
        checkout_id = graphene.ID(required=False)
        total = graphene.Decimal(required=False)

    payment = graphene.Field(PaymentNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        payment = Payment.objects.create(**input)
        return CreatePayment(payment=payment)


class UpdatePayment(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        is_active = graphene.Boolean(required=False)
        charge_status = graphene.String(required=False)
        total = graphene.Decimal(required=False)

    payment = graphene.Field(PaymentNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        payment = get_object(Payment, input.pop("id"))
        for key, value in input.items():
            setattr(payment, key, value)
        payment.save()
        return UpdatePayment(payment=payment)


class DeletePayment(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        payment = get_object(Payment, input["id"])
        payment.delete()
        return DeletePayment(ok=True)


# ---------- TRANSACTION ----------
class CreateTransaction(relay.ClientIDMutation):
    class Input:
        payment_id = graphene.ID(required=True)
        kind = graphene.String(required=True)
        currency = graphene.String(required=True)
        amount = graphene.Decimal(required=True)
        is_success = graphene.Boolean(required=False)

    transaction = graphene.Field(TransactionNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        payment = get_object(Payment, input.pop("payment_id"))
        txn = Transaction.objects.create(payment=payment, **input)
        return CreateTransaction(transaction=txn)


class UpdateTransaction(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        is_success = graphene.Boolean(required=False)
        error = graphene.String(required=False)
        already_processed = graphene.Boolean(required=False)

    transaction = graphene.Field(TransactionNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        txn = get_object(Transaction, input.pop("id"))
        for key, value in input.items():
            setattr(txn, key, value)
        txn.save()
        return UpdateTransaction(transaction=txn)


class DeleteTransaction(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        txn = get_object(Transaction, input["id"])
        txn.delete()
        return DeleteTransaction(ok=True)


# ---------- TRANSACTION ITEM ----------
class CreateTransactionItem(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=False)
        currency = graphene.String(required=True)
        order_id = graphene.ID(required=False)
        message = graphene.String(required=False)

    transaction_item = graphene.Field(TransactionItemNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        txn_item = TransactionItem.objects.create(**input)
        return CreateTransactionItem(transaction_item=txn_item)


class UpdateTransactionItem(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        message = graphene.String(required=False)
        currency = graphene.String(required=False)

    transaction_item = graphene.Field(TransactionItemNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        txn_item = get_object(TransactionItem, input.pop("id"))
        for key, value in input.items():
            setattr(txn_item, key, value)
        txn_item.save()
        return UpdateTransactionItem(transaction_item=txn_item)


class DeleteTransactionItem(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        txn_item = get_object(TransactionItem, input["id"])
        txn_item.delete()
        return DeleteTransactionItem(ok=True)


# ---------- TRANSACTION EVENT ----------
class CreateTransactionEvent(relay.ClientIDMutation):
    class Input:
        transaction_id = graphene.ID(required=True)
        type = graphene.String(required=True)
        currency = graphene.String(required=True)
        amount_value = graphene.Decimal(required=True)
        message = graphene.String(required=False)

    transaction_event = graphene.Field(TransactionEventNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        txn = get_object(TransactionItem, input.pop("transaction_id"))
        event = TransactionEvent.objects.create(transaction=txn, **input)
        return CreateTransactionEvent(transaction_event=event)


class UpdateTransactionEvent(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        message = graphene.String(required=False)
        include_in_calculations = graphene.Boolean(required=False)

    transaction_event = graphene.Field(TransactionEventNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        event = get_object(TransactionEvent, input.pop("id"))
        for key, value in input.items():
            setattr(event, key, value)
        event.save()
        return UpdateTransactionEvent(transaction_event=event)


class DeleteTransactionEvent(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        event = get_object(TransactionEvent, input["id"])
        event.delete()
        return DeleteTransactionEvent(ok=True)

# apps/backend/graphq/payment/mutations.py

class CreatePaymentMethod(relay.ClientIDMutation):
    class Input:
        type = graphene.String(required=True)
        name = graphene.String(required=True)
        gateway_token = graphene.String(required=True)
        gateway = graphene.String(required=True)
        is_default = graphene.Boolean()
        cc_last_digits = graphene.String()
        cc_brand = graphene.String()
        cc_exp_month = graphene.Int()
        cc_exp_year = graphene.Int()
        billing_address_id = graphene.ID()

    payment_method = graphene.Field(PaymentMethodNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        # If this is the first payment method, make it default
        if not PaymentMethod.objects.filter(user=user).exists():
            input['is_default'] = True
        
        # If setting as default, remove default from others
        if input.get('is_default'):
            PaymentMethod.objects.filter(user=user, is_default=True).update(is_default=False)
        
        payment_method = PaymentMethod.objects.create(
            user=user,
            **input
        )
        
        return CreatePaymentMethod(payment_method=payment_method)


class DeletePaymentMethod(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        payment_method = get_object(PaymentMethod, id)
        
        # Ensure user owns this payment method
        if payment_method.user != user:
            raise GraphQLError("You don't own this payment method")
        
        payment_method.delete()
        return DeletePaymentMethod(ok=True)


class SetDefaultPaymentMethod(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    payment_method = graphene.Field(PaymentMethodNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        payment_method = get_object(PaymentMethod, id)
        
        if payment_method.user != user:
            raise GraphQLError("You don't own this payment method")
        
        # Remove default from all others
        PaymentMethod.objects.filter(user=user, is_default=True).update(is_default=False)
        
        # Set this as default
        payment_method.is_default = True
        payment_method.save()
        
        return SetDefaultPaymentMethod(payment_method=payment_method)
    


'''import graphene
from graphene import relay
from graphql import GraphQLError
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone
from payment.models import Transaction, UnivaDiscount, UnivaUser, UnivaPromotion
from payment.services import UnivaPaymentService
from .types import (
    UnivaDiscountType, UnivaUserType, UnivaTransactionType,
    UnivaPromotionType, UnivaUserBenefits
)

User = get_user_model()

class InitiateUnivaPayment(relay.ClientIDMutation):
    class Input:
        amount = graphene.Decimal(required=True)
        currency = graphene.String(default_value="USD")
        description = graphene.String()
        source = graphene.String(description="Payment source or card ID")
        client_mutation_id = graphene.String(required=True)
    
    # Output fields
    status = graphene.String()
    transaction = graphene.Field(UnivaTransactionType)
    original_amount = graphene.Decimal()
    discount = graphene.Decimal()
    final_amount = graphene.Decimal()
    cashback = graphene.Decimal()
    formatted_discount = graphene.String()
    formatted_final = graphene.String()
    payment_intent = graphene.JSONString()
    requires_action = graphene.Boolean()
    action_data = graphene.JSONString()
    errors = graphene.JSONString()
    client_mutation_id = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        client_mutation_id = input.get('client_mutation_id')
        
        if not user.is_authenticated:
            return cls(
                status='error',
                errors={'authentication': 'Authentication required'},
                client_mutation_id=client_mutation_id
            )
        
        # Check if user has Univa card
        univa_user = UnivaUser.objects.filter(user_id=user.id).first()
        if not univa_user or not univa_user.is_active:
            return cls(
                status='error',
                errors={'univa_card': 'No active Univa card found'},
                client_mutation_id=client_mutation_id
            )
        
        try:
            # Initialize payment service
            payment_service = UnivaPaymentService(user)
            
            # Process payment
            result = payment_service.initiate_payment(
                amount=input['amount'],
                currency=input.get('currency', 'USD'),
                description=input.get('description'),
                source=input.get('source')
            )
            
            if not result['success']:
                return cls(
                    status='error',
                    errors={'payment': result.get('error', 'Payment initiation failed')},
                    client_mutation_id=client_mutation_id
                )
            
            # Create transaction record
            transaction = Transaction.objects.create(
                user=user,
                transaction_id=result['transaction_id'],
                amount=result['final_amount'],
                original_amount=input['amount'],
                discount_applied=result['discount'],
                cashback_earned=result['cashback'],
                status='pending',
                payment_method='univa',
                gateway_transaction_id=result.get('gateway_id'),
                univa_user_id=univa_user.user_id
            )
            
            # Update user totals
            univa_user.total_savings += result['discount'] + result['cashback']
            univa_user.total_cashback += result['cashback']
            univa_user.loyalty_points += int(result['cashback'] * 10)
            univa_user.save()
            
            return cls(
                status='success',
                transaction=transaction,
                original_amount=input['amount'],
                discount=result['discount'],
                final_amount=result['final_amount'],
                cashback=result['cashback'],
                formatted_discount=f"${result['discount']:.2f}",
                formatted_final=f"${result['final_amount']:.2f}",
                payment_intent=result.get('payment_intent'),
                requires_action=result.get('requires_action', False),
                action_data=result.get('action_data'),
                errors=None,
                client_mutation_id=client_mutation_id
            )
        except Exception as e:
            return cls(
                status='error',
                errors={'server': str(e)},
                client_mutation_id=client_mutation_id
            )

class ConfirmUnivaPayment(relay.ClientIDMutation):
    class Input:
        transaction_id = graphene.ID(required=True)
        confirmation_data = graphene.JSONString()
        client_mutation_id = graphene.String(required=True)
    
    status = graphene.String()
    transaction = graphene.Field(UnivaTransactionType)
    original_amount = graphene.Decimal()
    discount = graphene.Decimal()
    final_amount = graphene.Decimal()
    cashback = graphene.Decimal()
    formatted_discount = graphene.String()
    formatted_final = graphene.String()
    errors = graphene.JSONString()
    client_mutation_id = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        client_mutation_id = input.get('client_mutation_id')
        
        if not user.is_authenticated:
            return cls(
                status='error',
                errors={'authentication': 'Authentication required'},
                client_mutation_id=client_mutation_id
            )
        
        try:
            transaction = Transaction.objects.get(
                id=input['transaction_id'], 
                user=user,
                payment_method='univa'
            )
        except Transaction.DoesNotExist:
            return cls(
                status='error',
                errors={'transaction': 'Transaction not found'},
                client_mutation_id=client_mutation_id
            )
        
        try:
            payment_service = UnivaPaymentService(user)
            result = payment_service.confirm_payment(
                transaction.transaction_id,
                input.get('confirmation_data')
            )
            
            if result['success']:
                transaction.status = 'completed'
                transaction.completed_at = result.get('completed_at')
                transaction.save()
                
                return cls(
                    status='completed',
                    transaction=transaction,
                    original_amount=transaction.original_amount,
                    discount=transaction.discount_applied,
                    final_amount=transaction.amount,
                    cashback=transaction.cashback_earned,
                    formatted_discount=f"${transaction.discount_applied:.2f}",
                    formatted_final=f"${transaction.amount:.2f}",
                    errors=None,
                    client_mutation_id=client_mutation_id
                )
            else:
                return cls(
                    status='error',
                    errors={'confirmation': result.get('error', 'Payment confirmation failed')},
                    client_mutation_id=client_mutation_id
                )
        except Exception as e:
            return cls(
                status='error',
                errors={'server': str(e)},
                client_mutation_id=client_mutation_id
            )

class ApplyUnivaDiscount(relay.ClientIDMutation):
    class Input:
        amount = graphene.Decimal(required=True)
        client_mutation_id = graphene.String(required=True)
    
    discount = graphene.Field(UnivaDiscountType)
    discount_amount = graphene.Decimal()
    final_amount = graphene.Decimal()
    formatted_discount = graphene.String()
    formatted_final = graphene.String()
    is_eligible = graphene.Boolean()
    errors = graphene.JSONString()
    client_mutation_id = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        client_mutation_id = input.get('client_mutation_id')
        
        if not user.is_authenticated:
            return cls(
                is_eligible=False,
                errors={'authentication': 'Authentication required'},
                client_mutation_id=client_mutation_id
            )
        
        try:
            discount = UnivaDiscount.objects.filter(is_active=True).first()
            if not discount:
                return cls(
                    is_eligible=False,
                    errors={'discount': 'No active discount available'},
                    client_mutation_id=client_mutation_id
                )
            
            # Check if user has Univa card
            has_univa_card = UnivaUser.objects.filter(
                user_id=user.id,
                is_active=True
            ).exists()
            
            if not has_univa_card:
                return cls(
                    is_eligible=False,
                    errors={'user': 'User not eligible for discount'},
                    client_mutation_id=client_mutation_id
                )
            
            amount = input['amount']
            discount_amount = discount.calculate_discount(amount)
            final_amount = amount - discount_amount
            
            return cls(
                discount=discount,
                discount_amount=discount_amount,
                final_amount=final_amount,
                formatted_discount=f"${discount_amount:.2f}",
                formatted_final=f"${final_amount:.2f}",
                is_eligible=True,
                errors=None,
                client_mutation_id=client_mutation_id
            )
        except Exception as e:
            return cls(
                is_eligible=False,
                errors={'server': str(e)},
                client_mutation_id=client_mutation_id
            )

class GetUserBenefits(relay.ClientIDMutation):
    class Input:
        user_id = graphene.ID()
        client_mutation_id = graphene.String(required=True)
    
    benefits = graphene.Field(UnivaUserBenefits)
    errors = graphene.JSONString()
    client_mutation_id = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        client_mutation_id = input.get('client_mutation_id')
        
        if not user.is_authenticated:
            return cls(
                errors={'authentication': 'Authentication required'},
                client_mutation_id=client_mutation_id
            )
        
        if input.get('user_id') and user.id != int(input['user_id']):
            return cls(
                errors={'permission': 'Permission denied'},
                client_mutation_id=client_mutation_id
            )
        
        try:
            univa_user, created = UnivaUser.objects.get_or_create(
                user_id=user.id,
                defaults={'email': user.email, 'is_active': True}
            )
            
            # Get active promotion
            active_promotion = UnivaPromotion.objects.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            ).first()
            
            next_tier = max(0, 1000 - univa_user.loyalty_points)
            
            transaction_count = Transaction.objects.filter(
                user=user,
                payment_method='univa',
                status='completed'
            ).count()
            
            benefits = UnivaUserBenefits(
                cashback_rate="2%",
                discount_rate="2%",
                min_transaction=Decimal('50.00'),
                max_discount=Decimal('1000.00'),
                loyalty_points=univa_user.loyalty_points,
                total_savings=univa_user.total_savings,
                total_transactions=transaction_count,
                next_tier_points=next_tier,
                has_active_promotion=bool(active_promotion),
                formatted_savings=f"${univa_user.total_savings:.2f}"
            )
            
            return cls(
                benefits=benefits,
                errors=None,
                client_mutation_id=client_mutation_id
            )
        except Exception as e:
            return cls(
                errors={'server': str(e)},
                client_mutation_id=client_mutation_id
            )

class UpdateUnivaPreferences(relay.ClientIDMutation):
    class Input:
        enable_notifications = graphene.Boolean()
        auto_apply_discount = graphene.Boolean()
        client_mutation_id = graphene.String(required=True)
    
    user = graphene.Field(UnivaUserType)
    errors = graphene.JSONString()
    client_mutation_id = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        client_mutation_id = input.get('client_mutation_id')
        
        if not user.is_authenticated:
            return cls(
                errors={'authentication': 'Authentication required'},
                client_mutation_id=client_mutation_id
            )
        
        try:
            univa_user, _ = UnivaUser.objects.get_or_create(user_id=user.id)
            
            if 'enable_notifications' in input:
                univa_user.enable_notifications = input['enable_notifications']
            if 'auto_apply_discount' in input:
                univa_user.auto_apply_discount = input['auto_apply_discount']
                
            univa_user.save()
            
            return cls(
                user=univa_user,
                errors=None,
                client_mutation_id=client_mutation_id
            )
        except Exception as e:
            return cls(
                errors={'server': str(e)},
                client_mutation_id=client_mutation_id
            )'''

# ---------- ROOT MUTATION ----------
class PaymentMutations(graphene.ObjectType):
    # Payment
    create_payment = CreatePayment.Field()
    update_payment = UpdatePayment.Field()
    delete_payment = DeletePayment.Field()

    # Transaction
    create_transaction = CreateTransaction.Field()
    update_transaction = UpdateTransaction.Field()
    delete_transaction = DeleteTransaction.Field()

    # Transaction Item
    create_transaction_item = CreateTransactionItem.Field()
    update_transaction_item = UpdateTransactionItem.Field()
    delete_transaction_item = DeleteTransactionItem.Field()

    # Transaction Event
    create_transaction_event = CreateTransactionEvent.Field()
    update_transaction_event = UpdateTransactionEvent.Field()
    delete_transaction_event = DeleteTransactionEvent.Field()
    
    # Payment Method mutations
    create_payment_method = CreatePaymentMethod.Field()
    delete_payment_method = DeletePaymentMethod.Field()
    set_default_payment_method = SetDefaultPaymentMethod.Field()
    
    '''initiate_univa_payment = InitiateUnivaPayment.Field()
    confirm_univa_payment = ConfirmUnivaPayment.Field()
    apply_univa_discount = ApplyUnivaDiscount.Field()
    get_user_benefits = GetUserBenefits.Field()
    update_univa_preferences = UpdateUnivaPreferences.Field()'''


