# apps/backend/graphq/banking/subscriptions.py
'''import graphene
from django.utils import timezone
from graphql_relay import from_global_id

from banking.models import (Account, AirtimePurchase, ATMCard, ATMTransaction,
                            AuditLog, Balance, BillPayment, Contact,
                            CurrencyExchangeRate, FraudAlert,
                            FraudDetectionRule, LedgerEntry, MoneyTransfer,
                            Notification, PaymentStat, PhoneChangeRequest,
                            Transaction, TransactionLimit, Webhook)
from graphq.accounts.types import UserNode
from graphq.banking.types import (AccountNode, AirtimePurchaseNode,
                                  ATMCardNode, ATMTransactionNode,
                                  AuditLogNode, BalanceNode, BillPaymentNode,
                                  ContactNode, CurrencyExchangeRateNode,
                                  FraudAlertNode, FraudDetectionRuleNode,
                                  LedgerEntryNode, MoneyTransferNode,
                                  NotificationNode, PaymentStatNode,
                                  PhoneChangeRequestNode, TransactionLimitNode,
                                  TransactionNode, WebhookNode)
from graphq.subscriptions.subscription import Subscription

# ----------------------------------------------------------------------
# 💰 ACCOUNT & BALANCE SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnAccountCreated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    account = graphene.Field(AccountNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"account_updates_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnAccountCreated(account=payload)

    @classmethod
    def broadcast(cls, user_id, account):
        cls.broadcast_group(
            group=f"account_updates_{user_id}",
            payload=account,
        )

class OnBalanceUpdated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    balance = graphene.Field(BalanceNode)
    change_type = graphene.String()
    delta = graphene.Float()

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"balance_updates_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnBalanceUpdated(
            balance=payload["balance"],
            change_type=payload["change_type"],
            delta=payload["delta"]
        )

    @classmethod
    def broadcast(cls, user_id, balance, change_type, delta):
        cls.broadcast_group(
            group=f"balance_updates_{user_id}",
            payload={
                "balance": balance,
                "change_type": change_type,
                "delta": delta
            },
        )

class OnLedgerEntryCreated(Subscription):
    class Arguments:
        account_id = graphene.ID(required=True)

    ledger_entry = graphene.Field(LedgerEntryNode)

    @staticmethod
    def subscribe(root, info, account_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(account_id)[1]
        try:
            account = Account.objects.get(id=real_id)
            if account.user != user:
                raise Exception("Not authorized")
            return [f"ledger_entries_{real_id}"]
        except Account.DoesNotExist:
            raise Exception("Account not found")

    @staticmethod
    def publish(payload, info, account_id):
        return OnLedgerEntryCreated(ledger_entry=payload)

    @classmethod
    def broadcast(cls, account_id, ledger_entry):
        cls.broadcast_group(
            group=f"ledger_entries_{account_id}",
            payload=ledger_entry,
        )

# ----------------------------------------------------------------------
# 💸 TRANSACTION SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnTransactionCreated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    transaction = graphene.Field(TransactionNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"transactions_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnTransactionCreated(transaction=payload)

    @classmethod
    def broadcast(cls, user_id, transaction):
        cls.broadcast_group(
            group=f"transactions_{user_id}",
            payload=transaction,
        )

class OnTransactionStatusChanged(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    transaction = graphene.Field(TransactionNode)
    old_status = graphene.String()
    new_status = graphene.String()

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"transaction_status_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnTransactionStatusChanged(
            transaction=payload["transaction"],
            old_status=payload["old_status"],
            new_status=payload["new_status"]
        )

    @classmethod
    def broadcast(cls, user_id, transaction, old_status, new_status):
        cls.broadcast_group(
            group=f"transaction_status_{user_id}",
            payload={
                "transaction": transaction,
                "old_status": old_status,
                "new_status": new_status
            },
        )

# ----------------------------------------------------------------------
# 🔄 MONEY TRANSFER SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnMoneyTransferCreated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    transfer = graphene.Field(MoneyTransferNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"money_transfers_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnMoneyTransferCreated(transfer=payload)

    @classmethod
    def broadcast(cls, user_id, transfer):
        cls.broadcast_group(
            group=f"money_transfers_{user_id}",
            payload=transfer,
        )

class OnMoneyTransferStatusChanged(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    transfer = graphene.Field(MoneyTransferNode)
    status = graphene.String()

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"transfer_status_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnMoneyTransferStatusChanged(
            transfer=payload["transfer"],
            status=payload["status"]
        )

    @classmethod
    def broadcast(cls, user_id, transfer, status):
        cls.broadcast_group(
            group=f"transfer_status_{user_id}",
            payload={
                "transfer": transfer,
                "status": status
            },
        )

# ----------------------------------------------------------------------
# 🧾 BILL PAYMENT SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnBillPaymentCreated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    bill_payment = graphene.Field(BillPaymentNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"bill_payments_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnBillPaymentCreated(bill_payment=payload)

    @classmethod
    def broadcast(cls, user_id, bill_payment):
        cls.broadcast_group(
            group=f"bill_payments_{user_id}",
            payload=bill_payment,
        )

class OnBillPaymentStatusChanged(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    bill_payment = graphene.Field(BillPaymentNode)
    status = graphene.String()

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"bill_payment_status_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnBillPaymentStatusChanged(
            bill_payment=payload["bill_payment"],
            status=payload["status"]
        )

    @classmethod
    def broadcast(cls, user_id, bill_payment, status):
        cls.broadcast_group(
            group=f"bill_payment_status_{user_id}",
            payload={
                "bill_payment": bill_payment,
                "status": status
            },
        )

# ----------------------------------------------------------------------
# 📱 AIRTIME PURCHASE SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnAirtimePurchaseCreated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    airtime_purchase = graphene.Field(AirtimePurchaseNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"airtime_purchases_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnAirtimePurchaseCreated(airtime_purchase=payload)

    @classmethod
    def broadcast(cls, user_id, airtime_purchase):
        cls.broadcast_group(
            group=f"airtime_purchases_{user_id}",
            payload=airtime_purchase,
        )

class OnAirtimePurchaseStatusChanged(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    airtime_purchase = graphene.Field(AirtimePurchaseNode)
    status = graphene.String()

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"airtime_purchase_status_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnAirtimePurchaseStatusChanged(
            airtime_purchase=payload["airtime_purchase"],
            status=payload["status"]
        )

    @classmethod
    def broadcast(cls, user_id, airtime_purchase, status):
        cls.broadcast_group(
            group=f"airtime_purchase_status_{user_id}",
            payload={
                "airtime_purchase": airtime_purchase,
                "status": status
            },
        )

# ----------------------------------------------------------------------
# 🔔 NOTIFICATION SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnBankingNotificationReceived(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    notification = graphene.Field(NotificationNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"banking_notifications_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnBankingNotificationReceived(notification=payload)

    @classmethod
    def broadcast(cls, user_id, notification):
        cls.broadcast_group(
            group=f"banking_notifications_{user_id}",
            payload=notification,
        )

class OnNotificationRead(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    notification = graphene.Field(NotificationNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"notification_read_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnNotificationRead(notification=payload)

    @classmethod
    def broadcast(cls, user_id, notification):
        cls.broadcast_group(
            group=f"notification_read_{user_id}",
            payload=notification,
        )

# ----------------------------------------------------------------------
# 👥 CONTACT SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnContactAdded(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    contact = graphene.Field(ContactNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"contacts_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnContactAdded(contact=payload)

    @classmethod
    def broadcast(cls, user_id, contact):
        cls.broadcast_group(
            group=f"contacts_{user_id}",
            payload=contact,
        )

class OnContactRemoved(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    contact_id = graphene.ID()
    removed_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"contacts_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnContactRemoved(
            contact_id=payload["contact_id"],
            removed_at=payload["removed_at"]
        )

    @classmethod
    def broadcast(cls, user_id, contact_id):
        cls.broadcast_group(
            group=f"contacts_{user_id}",
            payload={
                "contact_id": contact_id,
                "removed_at": timezone.now().isoformat()
            },
        )

# ----------------------------------------------------------------------
# 💳 ATM CARD SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnATMCardCreated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    card = graphene.Field(ATMCardNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"atm_cards_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnATMCardCreated(card=payload)

    @classmethod
    def broadcast(cls, user_id, card):
        cls.broadcast_group(
            group=f"atm_cards_{user_id}",
            payload=card,
        )

class OnATMCardStatusChanged(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    card = graphene.Field(ATMCardNode)
    old_status = graphene.String()
    new_status = graphene.String()

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"atm_card_status_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnATMCardStatusChanged(
            card=payload["card"],
            old_status=payload["old_status"],
            new_status=payload["new_status"]
        )

    @classmethod
    def broadcast(cls, user_id, card, old_status, new_status):
        cls.broadcast_group(
            group=f"atm_card_status_{user_id}",
            payload={
                "card": card,
                "old_status": old_status,
                "new_status": new_status
            },
        )

# ----------------------------------------------------------------------
# 🏧 ATM TRANSACTION SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnATMTransactionCreated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    atm_transaction = graphene.Field(ATMTransactionNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"atm_transactions_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnATMTransactionCreated(atm_transaction=payload)

    @classmethod
    def broadcast(cls, user_id, atm_transaction):
        cls.broadcast_group(
            group=f"atm_transactions_{user_id}",
            payload=atm_transaction,
        )

class OnATMTransactionStatusChanged(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    atm_transaction = graphene.Field(ATMTransactionNode)
    status = graphene.String()

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"atm_transaction_status_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnATMTransactionStatusChanged(
            atm_transaction=payload["atm_transaction"],
            status=payload["status"]
        )

    @classmethod
    def broadcast(cls, user_id, atm_transaction, status):
        cls.broadcast_group(
            group=f"atm_transaction_status_{user_id}",
            payload={
                "atm_transaction": atm_transaction,
                "status": status
            },
        )

# ----------------------------------------------------------------------
# 🔐 SECURITY & COMPLIANCE SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnPhoneChangeRequestCreated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    phone_change_request = graphene.Field(PhoneChangeRequestNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"phone_change_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnPhoneChangeRequestCreated(phone_change_request=payload)

    @classmethod
    def broadcast(cls, user_id, phone_change_request):
        cls.broadcast_group(
            group=f"phone_change_{user_id}",
            payload=phone_change_request,
        )

class OnPhoneChangeOTPSent(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    phone_change_request = graphene.Field(PhoneChangeRequestNode)
    otp_sent_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"phone_change_otp_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnPhoneChangeOTPSent(
            phone_change_request=payload["phone_change_request"],
            otp_sent_at=payload["otp_sent_at"]
        )

    @classmethod
    def broadcast(cls, user_id, phone_change_request):
        cls.broadcast_group(
            group=f"phone_change_otp_{user_id}",
            payload={
                "phone_change_request": phone_change_request,
                "otp_sent_at": phone_change_request.otp_sent_at.isoformat()
            },
        )

class OnFraudAlertCreated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    fraud_alert = graphene.Field(FraudAlertNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"fraud_alerts_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnFraudAlertCreated(fraud_alert=payload)

    @classmethod
    def broadcast(cls, user_id, fraud_alert):
        cls.broadcast_group(
            group=f"fraud_alerts_{user_id}",
            payload=fraud_alert,
        )

class OnFraudAlertStatusChanged(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    fraud_alert = graphene.Field(FraudAlertNode)
    status = graphene.String()

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"fraud_alert_status_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnFraudAlertStatusChanged(
            fraud_alert=payload["fraud_alert"],
            status=payload["status"]
        )

    @classmethod
    def broadcast(cls, user_id, fraud_alert, status):
        cls.broadcast_group(
            group=f"fraud_alert_status_{user_id}",
            payload={
                "fraud_alert": fraud_alert,
                "status": status
            },
        )

# ----------------------------------------------------------------------
# 🌐 SYSTEM & ADMIN SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnCurrencyExchangeRateUpdated(Subscription):
    class Arguments:
        base_currency = graphene.String(required=False)
        target_currency = graphene.String(required=False)

    exchange_rate = graphene.Field(CurrencyExchangeRateNode)

    @staticmethod
    def subscribe(root, info, base_currency=None, target_currency=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if base_currency and target_currency:
            return [f"exchange_rate_{base_currency}_{target_currency}"]
        elif base_currency:
            return [f"exchange_rate_{base_currency}"]
        else:
            return [f"exchange_rate_global"]

    @staticmethod
    def publish(payload, info, base_currency=None, target_currency=None):
        return OnCurrencyExchangeRateUpdated(exchange_rate=payload)

    @classmethod
    def broadcast(cls, exchange_rate):
        # Broadcast to specific currency pair
        cls.broadcast_group(
            group=f"exchange_rate_{exchange_rate.base_currency}_{exchange_rate.target_currency}",
            payload=exchange_rate,
        )
        # Broadcast to base currency subscribers
        cls.broadcast_group(
            group=f"exchange_rate_{exchange_rate.base_currency}",
            payload=exchange_rate,
        )
        # Broadcast to global subscribers
        cls.broadcast_group(
            group="exchange_rate_global",
            payload=exchange_rate,
        )

class OnWebhookTriggered(Subscription):
    class Arguments:
        event_type = graphene.String(required=True)

    webhook_delivery = graphene.JSONString()

    @staticmethod
    def subscribe(root, info, event_type):
        # Only admin users can subscribe to webhook events
        user = info.context.user
        if not user.is_authenticated or not user.is_staff:
            raise Exception("Admin access required")
        
        return [f"webhook_{event_type}"]

    @staticmethod
    def publish(payload, info, event_type):
        return OnWebhookTriggered(webhook_delivery=payload)

    @classmethod
    def broadcast(cls, event_type, webhook_delivery):
        cls.broadcast_group(
            group=f"webhook_{event_type}",
            payload=webhook_delivery,
        )

# ----------------------------------------------------------------------
# 📊 ANALYTICS & REPORTING SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnPaymentStatUpdated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    payment_stat = graphene.Field(PaymentStatNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"payment_stats_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnPaymentStatUpdated(payment_stat=payload)

    @classmethod
    def broadcast(cls, user_id, payment_stat):
        cls.broadcast_group(
            group=f"payment_stats_{user_id}",
            payload=payment_stat,
        )

class OnTransactionLimitUpdated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    transaction_limit = graphene.Field(TransactionLimitNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        if str(user.id) != real_id:
            raise Exception("Not authorized")
        
        return [f"transaction_limits_{real_id}"]

    @staticmethod
    def publish(payload, info, user_id):
        return OnTransactionLimitUpdated(transaction_limit=payload)

    @classmethod
    def broadcast(cls, user_id, transaction_limit):
        cls.broadcast_group(
            group=f"transaction_limits_{user_id}",
            payload=transaction_limit,
        )

# ----------------------------------------------------------------------
# Root BankingSubscription
# ----------------------------------------------------------------------

class BankingSubscription(graphene.ObjectType):
    # Account & Balance
    on_account_created = OnAccountCreated.Field()
    on_balance_updated = OnBalanceUpdated.Field()
    on_ledger_entry_created = OnLedgerEntryCreated.Field()
    
    # Transactions
    on_transaction_created = OnTransactionCreated.Field()
    on_transaction_status_changed = OnTransactionStatusChanged.Field()
    
    # Money Transfers
    on_money_transfer_created = OnMoneyTransferCreated.Field()
    on_money_transfer_status_changed = OnMoneyTransferStatusChanged.Field()
    
    # Bill Payments
    on_bill_payment_created = OnBillPaymentCreated.Field()
    on_bill_payment_status_changed = OnBillPaymentStatusChanged.Field()
    
    # Airtime Purchases
    on_airtime_purchase_created = OnAirtimePurchaseCreated.Field()
    on_airtime_purchase_status_changed = OnAirtimePurchaseStatusChanged.Field()
    
    # Notifications
    on_banking_notification_received = OnBankingNotificationReceived.Field()
    on_notification_read = OnNotificationRead.Field()
    
    # Contacts
    on_contact_added = OnContactAdded.Field()
    on_contact_removed = OnContactRemoved.Field()
    
    # ATM Cards
    on_atm_card_created = OnATMCardCreated.Field()
    on_atm_card_status_changed = OnATMCardStatusChanged.Field()
    
    # ATM Transactions
    on_atm_transaction_created = OnATMTransactionCreated.Field()
    on_atm_transaction_status_changed = OnATMTransactionStatusChanged.Field()
    
    # Security & Compliance
    on_phone_change_request_created = OnPhoneChangeRequestCreated.Field()
    on_phone_change_otp_sent = OnPhoneChangeOTPSent.Field()
    on_fraud_alert_created = OnFraudAlertCreated.Field()
    on_fraud_alert_status_changed = OnFraudAlertStatusChanged.Field()
    
    # System & Admin
    on_currency_exchange_rate_updated = OnCurrencyExchangeRateUpdated.Field()
    on_webhook_triggered = OnWebhookTriggered.Field()
    
    # Analytics & Reporting
    on_payment_stat_updated = OnPaymentStatUpdated.Field()
    on_transaction_limit_updated = OnTransactionLimitUpdated.Field()'''