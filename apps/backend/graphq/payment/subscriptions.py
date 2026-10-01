'''import graphene
from django.db.models import Q
from django.utils import timezone
from graphql.accounts.types import UserNode
from graphql.checkout.types import CheckoutNode
from graphql.order.types import OrderNode
from graphql.payment.types import (PaymentNode, TransactionEventNode,
                                   TransactionItemNode, TransactionNode)
from graphql.subscriptions.subscription import Subscription
from graphql_relay import from_global_id

from checkout.models import Checkout
from order.models import Order
from payment.models import (Payment, Transaction, TransactionEvent,
                            TransactionItem)

from . import (ChargeStatus, StorePaymentMethod, TransactionAction,
               TransactionEventType, TransactionKind)

# ----------------------------------------------------------------------
# 💳 TRANSACTION ITEM SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnTransactionItemCreated(Subscription):
    class Arguments:
        checkout_id = graphene.ID(required=False)
        order_id = graphene.ID(required=False)
        user_id = graphene.ID(required=False)

    transaction_item = graphene.Field(TransactionItemNode)
    checkout = graphene.Field(CheckoutNode)
    order = graphene.Field(OrderNode)
    user = graphene.Field(UserNode)

    @staticmethod
    def subscribe(root, info, checkout_id=None, order_id=None, user_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if checkout_id:
            real_id = from_global_id(checkout_id)[1]
            # Subscribe to transactions for specific checkout
            try:
                checkout = Checkout.objects.get(id=real_id)
                if user.has_perm('payment.handle_payments') or checkout.user == user:
                    return [f"checkout_transactions_{real_id}"]
                else:
                    raise Exception("Not authorized")
            except Checkout.DoesNotExist:
                raise Exception("Checkout not found")
        
        elif order_id:
            real_id = from_global_id(order_id)[1]
            # Subscribe to transactions for specific order
            try:
                order = Order.objects.get(id=real_id)
                if user.has_perm('payment.handle_payments') or order.user == user:
                    return [f"order_transactions_{real_id}"]
                else:
                    raise Exception("Not authorized")
            except Order.DoesNotExist:
                raise Exception("Order not found")
        
        elif user_id:
            real_id = from_global_id(user_id)[1]
            # Subscribe to user's transactions
            if str(user.id) == real_id or user.has_perm('payment.handle_payments'):
                return [f"user_transactions_{real_id}"]
            else:
                raise Exception("Not authorized")
        
        else:
            # Staff can subscribe to all transaction creations
            if user.has_perm('payment.handle_payments'):
                return [f"all_transactions_created"]
            else:
                raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, checkout_id=None, order_id=None, user_id=None):
        return OnTransactionItemCreated(
            transaction_item=payload["transaction_item"],
            checkout=payload["checkout"],
            order=payload["order"],
            user=payload["user"]
        )

    @classmethod
    def broadcast_for_checkout(cls, checkout, transaction_item):
        cls.broadcast_group(
            group=f"checkout_transactions_{checkout.id}",
            payload={
                "transaction_item": transaction_item,
                "checkout": checkout,
                "order": None,
                "user": transaction_item.user
            }
        )

    @classmethod
    def broadcast_for_order(cls, order, transaction_item):
        cls.broadcast_group(
            group=f"order_transactions_{order.id}",
            payload={
                "transaction_item": transaction_item,
                "checkout": None,
                "order": order,
                "user": transaction_item.user
            }
        )

    @classmethod
    def broadcast_for_user(cls, user, transaction_item):
        cls.broadcast_group(
            group=f"user_transactions_{user.id}",
            payload={
                "transaction_item": transaction_item,
                "checkout": transaction_item.checkout,
                "order": transaction_item.order,
                "user": user
            }
        )

    @classmethod
    def broadcast_to_all(cls, transaction_item):
        cls.broadcast_group(
            group="all_transactions_created",
            payload={
                "transaction_item": transaction_item,
                "checkout": transaction_item.checkout,
                "order": transaction_item.order,
                "user": transaction_item.user
            }
        )

class OnTransactionItemStatusChanged(Subscription):
    class Arguments:
        transaction_item_id = graphene.ID(required=True)

    transaction_item = graphene.Field(TransactionItemNode)
    available_actions = graphene.List(graphene.String)
    amount_changes = graphene.JSONString()
    psp_reference = graphene.String()
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, transaction_item_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(transaction_item_id)[1]
        try:
            transaction_item = TransactionItem.objects.get(id=real_id)
            # Check authorization based on associated object
            if transaction_item.checkout:
                if user.has_perm('payment.handle_payments') or transaction_item.checkout.user == user:
                    return [f"transaction_status_{real_id}"]
            elif transaction_item.order:
                if user.has_perm('payment.handle_payments') or transaction_item.order.user == user:
                    return [f"transaction_status_{real_id}"]
            elif transaction_item.user:
                if user.has_perm('payment.handle_payments') or transaction_item.user == user:
                    return [f"transaction_status_{real_id}"]
            else:
                if user.has_perm('payment.handle_payments'):
                    return [f"transaction_status_{real_id}"]
            raise Exception("Not authorized to subscribe to this transaction")
        except TransactionItem.DoesNotExist:
            raise Exception("Transaction item not found")

    @staticmethod
    def publish(payload, info, transaction_item_id):
        return OnTransactionItemStatusChanged(
            transaction_item=payload["transaction_item"],
            available_actions=payload["available_actions"],
            amount_changes=payload["amount_changes"],
            psp_reference=payload["psp_reference"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, transaction_item, old_actions, new_actions, amount_changes, psp_reference):
        cls.broadcast_group(
            group=f"transaction_status_{transaction_item.id}",
            payload={
                "transaction_item": transaction_item,
                "available_actions": new_actions,
                "amount_changes": amount_changes,
                "psp_reference": psp_reference,
                "updated_at": timezone.now().isoformat()
            }
        )

class OnTransactionAmountsUpdated(Subscription):
    class Arguments:
        transaction_item_id = graphene.ID(required=True)

    transaction_item = graphene.Field(TransactionItemNode)
    amount_type = graphene.String()  # 'authorized', 'charged', 'refunded', etc.
    old_amount = graphene.Field(graphene.String)
    new_amount = graphene.Field(graphene.String)
    currency = graphene.String()
    changed_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, transaction_item_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(transaction_item_id)[1]
        try:
            transaction_item = TransactionItem.objects.get(id=real_id)
            if user.has_perm('payment.handle_payments') or (
                transaction_item.user and transaction_item.user == user
            ):
                return [f"transaction_amounts_{real_id}"]
            else:
                raise Exception("Not authorized")
        except TransactionItem.DoesNotExist:
            raise Exception("Transaction item not found")

    @staticmethod
    def publish(payload, info, transaction_item_id):
        return OnTransactionAmountsUpdated(
            transaction_item=payload["transaction_item"],
            amount_type=payload["amount_type"],
            old_amount=payload["old_amount"],
            new_amount=payload["new_amount"],
            currency=payload["currency"],
            changed_at=payload["changed_at"]
        )

    @classmethod
    def broadcast(cls, transaction_item, amount_type, old_amount, new_amount):
        cls.broadcast_group(
            group=f"transaction_amounts_{transaction_item.id}",
            payload={
                "transaction_item": transaction_item,
                "amount_type": amount_type,
                "old_amount": str(old_amount),
                "new_amount": str(new_amount),
                "currency": transaction_item.currency,
                "changed_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# 📊 TRANSACTION EVENT SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnTransactionEventCreated(Subscription):
    class Arguments:
        transaction_item_id = graphene.ID(required=True)

    transaction_event = graphene.Field(TransactionEventNode)
    transaction_item = graphene.Field(TransactionItemNode)
    event_type = graphene.String()
    amount = graphene.Field(graphene.String)
    psp_reference = graphene.String()
    created_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, transaction_item_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(transaction_item_id)[1]
        try:
            transaction_item = TransactionItem.objects.get(id=real_id)
            if user.has_perm('payment.handle_payments') or (
                transaction_item.user and transaction_item.user == user
            ):
                return [f"transaction_events_{real_id}"]
            else:
                raise Exception("Not authorized")
        except TransactionItem.DoesNotExist:
            raise Exception("Transaction item not found")

    @staticmethod
    def publish(payload, info, transaction_item_id):
        return OnTransactionEventCreated(
            transaction_event=payload["transaction_event"],
            transaction_item=payload["transaction_item"],
            event_type=payload["event_type"],
            amount=payload["amount"],
            psp_reference=payload["psp_reference"],
            created_at=payload["created_at"]
        )

    @classmethod
    def broadcast(cls, transaction_item, transaction_event):
        cls.broadcast_group(
            group=f"transaction_events_{transaction_item.id}",
            payload={
                "transaction_event": transaction_event,
                "transaction_item": transaction_item,
                "event_type": transaction_event.type,
                "amount": str(transaction_event.amount),
                "psp_reference": transaction_event.psp_reference,
                "created_at": transaction_event.created_at.isoformat()
            }
        )

class OnTransactionEventStatusChanged(Subscription):
    class Arguments:
        transaction_item_id = graphene.ID(required=True)

    transaction_event = graphene.Field(TransactionEventNode)
    old_include_in_calculations = graphene.Boolean()
    new_include_in_calculations = graphene.Boolean()
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, transaction_item_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(transaction_item_id)[1]
        try:
            transaction_item = TransactionItem.objects.get(id=real_id)
            if user.has_perm('payment.handle_payments'):
                return [f"transaction_event_status_{real_id}"]
            else:
                raise Exception("Not authorized")
        except TransactionItem.DoesNotExist:
            raise Exception("Transaction item not found")

    @staticmethod
    def publish(payload, info, transaction_item_id):
        return OnTransactionEventStatusChanged(
            transaction_event=payload["transaction_event"],
            old_include_in_calculations=payload["old_include_in_calculations"],
            new_include_in_calculations=payload["new_include_in_calculations"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, transaction_item, transaction_event, old_include, new_include):
        cls.broadcast_group(
            group=f"transaction_event_status_{transaction_item.id}",
            payload={
                "transaction_event": transaction_event,
                "old_include_in_calculations": old_include,
                "new_include_in_calculations": new_include,
                "updated_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# 💰 PAYMENT SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnPaymentCreated(Subscription):
    class Arguments:
        checkout_id = graphene.ID(required=False)
        order_id = graphene.ID(required=False)

    payment = graphene.Field(PaymentNode)
    checkout = graphene.Field(CheckoutNode)
    order = graphene.Field(OrderNode)
    gateway = graphene.String()

    @staticmethod
    def subscribe(root, info, checkout_id=None, order_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if checkout_id:
            real_id = from_global_id(checkout_id)[1]
            try:
                checkout = Checkout.objects.get(id=real_id)
                if user.has_perm('payment.handle_payments') or checkout.user == user:
                    return [f"checkout_payments_{real_id}"]
                else:
                    raise Exception("Not authorized")
            except Checkout.DoesNotExist:
                raise Exception("Checkout not found")
        
        elif order_id:
            real_id = from_global_id(order_id)[1]
            try:
                order = Order.objects.get(id=real_id)
                if user.has_perm('payment.handle_payments') or order.user == user:
                    return [f"order_payments_{real_id}"]
                else:
                    raise Exception("Not authorized")
            except Order.DoesNotExist:
                raise Exception("Order not found")
        
        else:
            if user.has_perm('payment.handle_payments'):
                return [f"all_payments_created"]
            else:
                raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, checkout_id=None, order_id=None):
        return OnPaymentCreated(
            payment=payload["payment"],
            checkout=payload["checkout"],
            order=payload["order"],
            gateway=payload["gateway"]
        )

    @classmethod
    def broadcast_for_checkout(cls, checkout, payment):
        cls.broadcast_group(
            group=f"checkout_payments_{checkout.id}",
            payload={
                "payment": payment,
                "checkout": checkout,
                "order": None,
                "gateway": payment.gateway
            }
        )

    @classmethod
    def broadcast_for_order(cls, order, payment):
        cls.broadcast_group(
            group=f"order_payments_{order.id}",
            payload={
                "payment": payment,
                "checkout": None,
                "order": order,
                "gateway": payment.gateway
            }
        )

    @classmethod
    def broadcast_to_all(cls, payment):
        cls.broadcast_group(
            group="all_payments_created",
            payload={
                "payment": payment,
                "checkout": payment.checkout,
                "order": payment.order,
                "gateway": payment.gateway
            }
        )

class OnPaymentStatusChanged(Subscription):
    class Arguments:
        payment_id = graphene.ID(required=True)

    payment = graphene.Field(PaymentNode)
    old_charge_status = graphene.String()
    new_charge_status = graphene.String()
    old_is_active = graphene.Boolean()
    new_is_active = graphene.Boolean()
    captured_amount = graphene.Field(graphene.String)
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, payment_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(payment_id)[1]
        try:
            payment = Payment.objects.get(id=real_id)
            # Check authorization based on associated object
            if payment.checkout:
                if user.has_perm('payment.handle_payments') or payment.checkout.user == user:
                    return [f"payment_status_{real_id}"]
            elif payment.order:
                if user.has_perm('payment.handle_payments') or payment.order.user == user:
                    return [f"payment_status_{real_id}"]
            else:
                if user.has_perm('payment.handle_payments'):
                    return [f"payment_status_{real_id}"]
            raise Exception("Not authorized to subscribe to this payment")
        except Payment.DoesNotExist:
            raise Exception("Payment not found")

    @staticmethod
    def publish(payload, info, payment_id):
        return OnPaymentStatusChanged(
            payment=payload["payment"],
            old_charge_status=payload["old_charge_status"],
            new_charge_status=payload["new_charge_status"],
            old_is_active=payload["old_is_active"],
            new_is_active=payload["new_is_active"],
            captured_amount=payload["captured_amount"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, payment, old_charge_status, new_charge_status, old_is_active, new_is_active):
        cls.broadcast_group(
            group=f"payment_status_{payment.id}",
            payload={
                "payment": payment,
                "old_charge_status": old_charge_status,
                "new_charge_status": new_charge_status,
                "old_is_active": old_is_active,
                "new_is_active": new_is_active,
                "captured_amount": str(payment.get_captured_amount()),
                "updated_at": timezone.now().isoformat()
            }
        )

class OnPaymentAmountUpdated(Subscription):
    class Arguments:
        payment_id = graphene.ID(required=True)

    payment = graphene.Field(PaymentNode)
    old_total = graphene.Field(graphene.String)
    new_total = graphene.Field(graphene.String)
    old_captured_amount = graphene.Field(graphene.String)
    new_captured_amount = graphene.Field(graphene.String)
    currency = graphene.String()
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, payment_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(payment_id)[1]
        try:
            payment = Payment.objects.get(id=real_id)
            if user.has_perm('payment.handle_payments') or (
                payment.order and payment.order.user == user
            ):
                return [f"payment_amounts_{real_id}"]
            else:
                raise Exception("Not authorized")
        except Payment.DoesNotExist:
            raise Exception("Payment not found")

    @staticmethod
    def publish(payload, info, payment_id):
        return OnPaymentAmountUpdated(
            payment=payload["payment"],
            old_total=payload["old_total"],
            new_total=payload["new_total"],
            old_captured_amount=payload["old_captured_amount"],
            new_captured_amount=payload["new_captured_amount"],
            currency=payload["currency"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, payment, old_total, new_total, old_captured, new_captured):
        cls.broadcast_group(
            group=f"payment_amounts_{payment.id}",
            payload={
                "payment": payment,
                "old_total": str(old_total),
                "new_total": str(new_total),
                "old_captured_amount": str(old_captured),
                "new_captured_amount": str(new_captured),
                "currency": payment.currency,
                "updated_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# 🔄 TRANSACTION (LEGACY) SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnTransactionProcessed(Subscription):
    class Arguments:
        payment_id = graphene.ID(required=True)

    transaction = graphene.Field(TransactionNode)
    payment = graphene.Field(PaymentNode)
    transaction_kind = graphene.String()
    is_success = graphene.Boolean()
    amount = graphene.Field(graphene.String)
    gateway_response = graphene.JSONString()
    created_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, payment_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(payment_id)[1]
        try:
            payment = Payment.objects.get(id=real_id)
            if user.has_perm('payment.handle_payments') or (
                payment.order and payment.order.user == user
            ):
                return [f"payment_transactions_{real_id}"]
            else:
                raise Exception("Not authorized")
        except Payment.DoesNotExist:
            raise Exception("Payment not found")

    @staticmethod
    def publish(payload, info, payment_id):
        return OnTransactionProcessed(
            transaction=payload["transaction"],
            payment=payload["payment"],
            transaction_kind=payload["transaction_kind"],
            is_success=payload["is_success"],
            amount=payload["amount"],
            gateway_response=payload["gateway_response"],
            created_at=payload["created_at"]
        )

    @classmethod
    def broadcast(cls, payment, transaction):
        cls.broadcast_group(
            group=f"payment_transactions_{payment.id}",
            payload={
                "transaction": transaction,
                "payment": payment,
                "transaction_kind": transaction.kind,
                "is_success": transaction.is_success,
                "amount": str(transaction.amount),
                "gateway_response": transaction.gateway_response,
                "created_at": transaction.created_at.isoformat()
            }
        )

class OnTransactionActionRequired(Subscription):
    class Arguments:
        payment_id = graphene.ID(required=True)

    transaction = graphene.Field(TransactionNode)
    payment = graphene.Field(PaymentNode)
    action_required_data = graphene.JSONString()
    required_action = graphene.String()
    created_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, payment_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(payment_id)[1]
        try:
            payment = Payment.objects.get(id=real_id)
            if user.has_perm('payment.handle_payments') or (
                payment.order and payment.order.user == user
            ):
                return [f"transaction_actions_{real_id}"]
            else:
                raise Exception("Not authorized")
        except Payment.DoesNotExist:
            raise Exception("Payment not found")

    @staticmethod
    def publish(payload, info, payment_id):
        return OnTransactionActionRequired(
            transaction=payload["transaction"],
            payment=payload["payment"],
            action_required_data=payload["action_required_data"],
            required_action=payload["required_action"],
            created_at=payload["created_at"]
        )

    @classmethod
    def broadcast(cls, payment, transaction):
        cls.broadcast_group(
            group=f"transaction_actions_{payment.id}",
            payload={
                "transaction": transaction,
                "payment": payment,
                "action_required_data": transaction.action_required_data,
                "required_action": transaction.kind,
                "created_at": transaction.created_at.isoformat()
            }
        )

# ----------------------------------------------------------------------
# 🔐 PAYMENT SECURITY & FRAUD SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnPaymentFraudDetected(Subscription):
    class Arguments:
        gateway = graphene.String(required=False)

    payment = graphene.Field(PaymentNode)
    fraud_indicators = graphene.List(graphene.String)
    risk_score = graphene.Float()
    detected_at = graphene.DateTime()
    action_taken = graphene.String()

    @staticmethod
    def subscribe(root, info, gateway=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('payment.handle_payments'):
            if gateway:
                return [f"fraud_detection_{gateway}"]
            else:
                return [f"all_fraud_detection"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, gateway=None):
        return OnPaymentFraudDetected(
            payment=payload["payment"],
            fraud_indicators=payload["fraud_indicators"],
            risk_score=payload["risk_score"],
            detected_at=payload["detected_at"],
            action_taken=payload["action_taken"]
        )

    @classmethod
    def broadcast_for_gateway(cls, gateway, payment, fraud_indicators, risk_score, action_taken):
        cls.broadcast_group(
            group=f"fraud_detection_{gateway}",
            payload={
                "payment": payment,
                "fraud_indicators": fraud_indicators,
                "risk_score": risk_score,
                "detected_at": timezone.now().isoformat(),
                "action_taken": action_taken
            }
        )

    @classmethod
    def broadcast_to_all(cls, payment, fraud_indicators, risk_score, action_taken):
        cls.broadcast_group(
            group="all_fraud_detection",
            payload={
                "payment": payment,
                "fraud_indicators": fraud_indicators,
                "risk_score": risk_score,
                "detected_at": timezone.now().isoformat(),
                "action_taken": action_taken
            }
        )

class OnPaymentMethodUpdated(Subscription):
    class Arguments:
        payment_id = graphene.ID(required=True)

    payment = graphene.Field(PaymentNode)
    old_payment_method = graphene.String()
    new_payment_method = graphene.String()
    store_payment_method = graphene.String()
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, payment_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(payment_id)[1]
        try:
            payment = Payment.objects.get(id=real_id)
            if user.has_perm('payment.handle_payments') or (
                payment.order and payment.order.user == user
            ):
                return [f"payment_method_{real_id}"]
            else:
                raise Exception("Not authorized")
        except Payment.DoesNotExist:
            raise Exception("Payment not found")

    @staticmethod
    def publish(payload, info, payment_id):
        return OnPaymentMethodUpdated(
            payment=payload["payment"],
            old_payment_method=payload["old_payment_method"],
            new_payment_method=payload["new_payment_method"],
            store_payment_method=payload["store_payment_method"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, payment, old_payment_method, new_payment_method):
        cls.broadcast_group(
            group=f"payment_method_{payment.id}",
            payload={
                "payment": payment,
                "old_payment_method": old_payment_method,
                "new_payment_method": new_payment_method,
                "store_payment_method": payment.store_payment_method,
                "updated_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# Root PaymentSubscription
# ----------------------------------------------------------------------

class PaymentSubscription(graphene.ObjectType):
    # Transaction Items
    on_transaction_item_created = OnTransactionItemCreated.Field()
    on_transaction_item_status_changed = OnTransactionItemStatusChanged.Field()
    on_transaction_amounts_updated = OnTransactionAmountsUpdated.Field()
    
    # Transaction Events
    on_transaction_event_created = OnTransactionEventCreated.Field()
    on_transaction_event_status_changed = OnTransactionEventStatusChanged.Field()
    
    # Payments
    on_payment_created = OnPaymentCreated.Field()
    on_payment_status_changed = OnPaymentStatusChanged.Field()
    on_payment_amount_updated = OnPaymentAmountUpdated.Field()
    
    # Legacy Transactions
    on_transaction_processed = OnTransactionProcessed.Field()
    on_transaction_action_required = OnTransactionActionRequired.Field()
    
    # Security & Fraud
    on_payment_fraud_detected = OnPaymentFraudDetected.Field()
    on_payment_method_updated = OnPaymentMethodUpdated.Field()
    
    
    
# Example usage in your Django views or signals
from payment.subscriptions import (OnPaymentFraudDetected,
                                   OnPaymentStatusChanged,
                                   OnTransactionEventCreated,
                                   OnTransactionItemCreated,
                                   OnTransactionProcessed)


# When a new transaction item is created
def create_transaction_item(checkout, amount, currency):
    transaction_item = TransactionItem.objects.create(
        checkout=checkout,
        amount_charged=amount,
        currency=currency,
        user=checkout.user
    )
    
    OnTransactionItemCreated.broadcast_for_checkout(checkout, transaction_item)
    if checkout.user:
        OnTransactionItemCreated.broadcast_for_user(checkout.user, transaction_item)

# When payment status changes
def update_payment_status(payment, new_status):
    old_status = payment.charge_status
    payment.charge_status = new_status
    payment.save()
    
    OnPaymentStatusChanged.broadcast(
        payment=payment,
        old_charge_status=old_status,
        new_charge_status=new_status,
        old_is_active=payment.is_active,
        new_is_active=payment.is_active
    )

# When transaction event is created
def create_transaction_event(transaction_item, event_type, amount, psp_reference):
    transaction_event = TransactionEvent.objects.create(
        transaction=transaction_item,
        type=event_type,
        amount=amount,
        psp_reference=psp_reference,
        currency=transaction_item.currency
    )
    
    OnTransactionEventCreated.broadcast(transaction_item, transaction_event)

# When legacy transaction is processed
def process_transaction(payment, transaction_data):
    transaction = Transaction.objects.create(
        payment=payment,
        **transaction_data
    )
    
    OnTransactionProcessed.broadcast(payment, transaction)

# When fraud is detected
def detect_fraud(payment, fraud_indicators, risk_score, action_taken):
    OnPaymentFraudDetected.broadcast_for_gateway(
        gateway=payment.gateway,
        payment=payment,
        fraud_indicators=fraud_indicators,
        risk_score=risk_score,
        action_taken=action_taken
    )
    
    # Also broadcast to all fraud monitoring systems
    OnPaymentFraudDetected.broadcast_to_all(
        payment=payment,
        fraud_indicators=fraud_indicators,
        risk_score=risk_score,
        action_taken=action_taken
    )

# When transaction amounts are updated
def update_transaction_amounts(transaction_item, amount_type, new_amount):
    old_amount = getattr(transaction_item, f"amount_{amount_type}")
    setattr(transaction_item, f"amount_{amount_type}", new_amount)
    transaction_item.save()
    
    OnTransactionAmountsUpdated.broadcast(
        transaction_item=transaction_item,
        amount_type=amount_type,
        old_amount=old_amount,
        new_amount=new_amount
    )'''