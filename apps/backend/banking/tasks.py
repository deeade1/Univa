'''from __future__ import absolute_import, unicode_literals

import time
from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from accounts.models import UserProfile
from banking.models import (Account, AirtimePurchase, ATMCard, ATMTransaction,
                            Balance, BillPayment, MoneyTransfer, Notification,
                            PaymentStat, Transaction)

logger = get_task_logger(__name__)

# --- Core Banking Tasks ---
@shared_task(bind=True, queue='high_priority', time_limit=300)
def process_money_transfer(self, transfer_id):
    """
    Process money transfer between accounts with transaction safety
    """
    try:
        transfer = MoneyTransfer.objects.select_for_update().get(pk=transfer_id)
        
        if transfer.status != 'pending':
            logger.info(f"Transfer {transfer_id} already processed")
            return {'status': transfer.status}

        with transaction.atomic():
            # Lock sender and recipient balances
            sender_balance = Balance.objects.select_for_update().get(user=transfer.sender)
            recipient_balance = Balance.objects.select_for_update().get(user=transfer.receiver)
            
            # Verify sender has sufficient funds
            if sender_balance.available_balance < (transfer.amount + transfer.fee):
                transfer.status = 'failed'
                transfer.save()
                raise Exception("Insufficient funds")
            
            # Perform transfer
            sender_balance.amount_usd -= (transfer.amount + transfer.fee)
            sender_balance.save()
            
            recipient_balance.amount_usd += transfer.amount
            recipient_balance.save()
            
            # Update transfer status
            transfer.status = 'completed'
            transfer.save()
            
            # Create transaction records
            Transaction.objects.create(
                user=transfer.sender,
                transaction_type='transferred',
                amount=transfer.amount,
                fee=transfer.fee,
                status='completed',
                reference=transfer.reference,
                recipient=transfer.receiver,
                description=f"Transfer to {transfer.receiver_account.account_number}"
            )
            
            Transaction.objects.create(
                user=transfer.receiver,
                transaction_type='received',
                amount=transfer.amount,
                status='completed',
                reference=transfer.reference,
                sender=transfer.sender,
                description=f"Transfer from {transfer.sender_account.account_number}"
            )
            
            # Update payment stats
            update_payment_stats.delay(transfer.sender.id, transfer.amount)
            
            # Send notifications
            send_notification.delay(
                user_id=transfer.sender.id,
                title="Transfer Completed",
                message=f"You sent ${transfer.amount} to {transfer.receiver.user.first_name}",
                notification_type='transfer'
            )
            
            send_notification.delay(
                user_id=transfer.receiver.id,
                title="Money Received",
                message=f"You received ${transfer.amount} from {transfer.sender.user.first_name}",
                notification_type='transfer'
            )
            
            logger.info(f"Completed transfer {transfer_id} of ${transfer.amount}")
            
            return {'status': 'completed'}
            
    except Exception as e:
        logger.error(f"Failed to process transfer {transfer_id}: {str(e)}")
        transfer.status = 'failed'
        transfer.save()
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, queue='high_priority')
def process_interbank_transfer(self, transfer_id):
    """
    Process interbank transfer with external bank API integration
    """
    try:
        transfer = MoneyTransfer.objects.get(pk=transfer_id)
        
        # Mock bank API call - replace with actual integration
        # bank_response = bank_api.transfer(
        #     sender_account=transfer.sender_account.account_number,
        #     recipient_bank=transfer.receiver_account.bank.code,
        #     recipient_account=transfer.receiver_account.account_number,
        #     amount=transfer.amount,
        #     narration=transfer.narration
        # )
        
        # Simulate API delay
        time.sleep(2)
        
        # Mock successful response
        bank_response = {
            'success': True,
            'reference': f"BANK-{timezone.now().timestamp()}",
            'status': 'completed'
        }
        
        if bank_response['success']:
            transfer.provider_reference = bank_response['reference']
            transfer.status = bank_response['status']
            transfer.save()
            
            # Update balances
            with transaction.atomic():
                sender_balance = Balance.objects.select_for_update().get(user=transfer.sender)
                sender_balance.amount_usd -= (transfer.amount + transfer.fee)
                sender_balance.save()
                
            # Create transaction record
            Transaction.objects.create(
                user=transfer.sender,
                transaction_type='transferred',
                amount=transfer.amount,
                fee=transfer.fee,
                status='completed',
                reference=transfer.reference,
                description=f"Transfer to {transfer.receiver_account.bank.name} account"
            )
            
            return {'status': 'completed', 'provider_reference': bank_response['reference']}
        else:
            transfer.status = 'failed'
            transfer.save()
            raise Exception("Bank API transfer failed")
            
    except Exception as e:
        logger.error(f"Interbank transfer failed: {str(e)}")
        transfer.status = 'failed'
        transfer.save()
        raise self.retry(exc=e, countdown=120)

@shared_task(bind=True, queue='high_priority')
def process_atm_withdrawal(self, transaction_id):
    """
    Process ATM withdrawal transaction
    """
    try:
        atm_transaction = ATMTransaction.objects.get(pk=transaction_id)
        card = atm_transaction.card
        
        # Check daily limits
        today_withdrawals = ATMTransaction.objects.filter(
            card=card,
            transaction_type='withdrawal',
            created_at__date=timezone.now().date(),
            status='completed'
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0
        
        if today_withdrawals + atm_transaction.amount > card.daily_withdrawal_limit:
            raise Exception("Daily withdrawal limit exceeded")
        
        with transaction.atomic():
            # Lock account balance
            balance = Balance.objects.select_for_update().get(user=card.account.user)
            
            if balance.available_balance < atm_transaction.amount:
                raise Exception("Insufficient funds")
            
            # Process withdrawal
            balance.amount_usd -= atm_transaction.amount
            balance.save()
            
            atm_transaction.status = 'completed'
            atm_transaction.save()
            
            # Create transaction record
            Transaction.objects.create(
                user=card.account.user,
                transaction_type='withdrawal',
                amount=atm_transaction.amount,
                status='completed',
                reference=atm_transaction.reference,
                description=f"ATM Withdrawal at {atm_transaction.location}"
            )
            
            # Send notification
            send_notification.delay(
                user_id=card.account.user.id,
                title="ATM Withdrawal",
                message=f"${atm_transaction.amount} withdrawn from your account",
                notification_type='atm'
            )
            
            logger.info(f"Processed ATM withdrawal {transaction_id}")
            
            return {'status': 'completed'}
            
    except Exception as e:
        logger.error(f"ATM withdrawal failed: {str(e)}")
        atm_transaction.status = 'failed'
        atm_transaction.save()
        raise self.retry(exc=e, countdown=30)

# --- Bill Payment and Airtime Tasks ---
@shared_task(bind=True, queue='bill_payments')
def process_bill_payment(self, payment_id):
    """
    Process bill payment to external providers
    """
    try:
        payment = BillPayment.objects.get(pk=payment_id)
        
        # Mock bill payment API call
        # provider_response = bill_api.pay(
        #     customer_ref=payment.customer_reference,
        #     amount=payment.amount,
        #     provider=payment.provider,
        #     bill_type=payment.bill_type
        # )
        
        # Simulate API delay
        time.sleep(1.5)
        
        # Mock successful response
        provider_response = {
            'success': True,
            'reference': f"BILL-{timezone.now().timestamp()}",
            'status': 'completed'
        }
        
        if provider_response['success']:
            with transaction.atomic():
                # Lock balance
                balance = Balance.objects.select_for_update().get(user=payment.user)
                
                if balance.available_balance < payment.amount:
                    raise Exception("Insufficient funds")
                
                # Deduct payment
                balance.amount_usd -= payment.amount
                balance.save()
                
                payment.status = 'completed'
                payment.provider_reference = provider_response['reference']
                payment.save()
                
                # Create transaction record
                Transaction.objects.create(
                    user=payment.user,
                    transaction_type='bill_payment',
                    amount=payment.amount,
                    status='completed',
                    reference=payment.reference,
                    description=f"{payment.get_bill_type_display()} payment to {payment.provider}"
                )
                
                # Send notification
                send_notification.delay(
                    user_id=payment.user.id,
                    title="Bill Payment",
                    message=f"Your {payment.get_bill_type_display()} payment of ${payment.amount} was successful",
                    notification_type='bill'
                )
                
                return {'status': 'completed'}
        else:
            payment.status = 'failed'
            payment.save()
            raise Exception("Bill payment failed")
            
    except Exception as e:
        logger.error(f"Bill payment failed: {str(e)}")
        payment.status = 'failed'
        payment.save()
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, queue='airtime')
def process_airtime_purchase(self, purchase_id):
    """
    Process airtime purchase transaction
    """
    try:
        purchase = AirtimePurchase.objects.get(pk=purchase_id)
        
        # Mock airtime API call
        # provider_response = airtime_api.purchase(
        #     phone_number=purchase.user.user.phone_number,
        #     network=purchase.network,
        #     amount=purchase.amount
        # )
        
        # Simulate API delay
        time.sleep(1)
        
        # Mock successful response
        provider_response = {
            'success': True,
            'reference': f"AIR-{timezone.now().timestamp()}",
            'status': 'completed'
        }
        
        if provider_response['success']:
            with transaction.atomic():
                # Lock balance
                balance = Balance.objects.select_for_update().get(user=purchase.user)
                
                if balance.available_balance < purchase.amount:
                    raise Exception("Insufficient funds")
                
                # Deduct payment
                balance.amount_usd -= purchase.amount
                balance.save()
                
                purchase.status = 'completed'
                purchase.provider_reference = provider_response['reference']
                purchase.save()
                
                # Create transaction record
                Transaction.objects.create(
                    user=purchase.user,
                    transaction_type='airtime',
                    amount=purchase.amount,
                    status='completed',
                    reference=purchase.reference,
                    description=f"{purchase.get_network_display()} airtime purchase"
                )
                
                # Send notification
                send_notification.delay(
                    user_id=purchase.user.id,
                    title="Airtime Purchase",
                    message=f"Your {purchase.get_network_display()} airtime purchase of ${purchase.amount} was successful",
                    notification_type='airtime'
                )
                
                return {'status': 'completed'}
        else:
            purchase.status = 'failed'
            purchase.save()
            raise Exception("Airtime purchase failed")
            
    except Exception as e:
        logger.error(f"Airtime purchase failed: {str(e)}")
        purchase.status = 'failed'
        purchase.save()
        raise self.retry(exc=e, countdown=30)

# --- Account Management Tasks ---
@shared_task(queue='accounts')
def create_user_account(user_id, account_type, pin):
    """
    Create a new bank account for a user
    """
    try:
        user = UserProfile.objects.get(pk=user_id)
        
        with transaction.atomic():
            account = Account.objects.create(
                user=user,
                account_type=account_type,
                pin=pin  # Note: In production, hash this pin
            )
            
            Balance.objects.create(user=user, amount_usd=0.00)
            PaymentStat.objects.create(user=user)
            
            logger.info(f"Created {account_type} account for user {user_id}")
            
            return {'account_id': account.id}
            
    except Exception as e:
        logger.error(f"Failed to create account for user {user_id}: {str(e)}")
        raise

@shared_task(queue='accounts')
def update_account_limits(user_id, daily_limit=None, monthly_limit=None):
    """
    Update user's transaction limits
    """
    try:
        stats = PaymentStat.objects.get(user_id=user_id)
        
        if daily_limit is not None:
            stats.daily_limit = daily_limit
        if monthly_limit is not None:
            stats.monthly_limit = monthly_limit
            
        stats.save()
        
        logger.info(f"Updated limits for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to update limits for user {user_id}: {str(e)}")
        raise

# --- Notification Tasks ---
@shared_task(queue='notifications')
def send_notification(user_id, title, message, notification_type, related_transaction_id=None):
    """
    Create and send a notification to a user
    """
    try:
        notification = Notification.objects.create(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            related_transaction_id=related_transaction_id
        )
        
        # In a real implementation, also send push/email/SMS here
        logger.info(f"Sent notification to user {user_id}: {title}")
        
        return {'notification_id': notification.id}
        
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_id}: {str(e)}")
        raise

# --- Stats and Reporting Tasks ---
@shared_task(queue='reports')
def update_payment_stats(user_id, amount):
    """
    Update user's payment statistics after a transaction
    """
    try:
        stats = PaymentStat.objects.get(user_id=user_id)
        
        with transaction.atomic():
            stats.number_of_payments += 1
            stats.total_payments_amount += amount
            stats.last_transaction_amount = amount
            stats.last_transaction_date = timezone.now()
            stats.save()
            
        logger.info(f"Updated payment stats for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to update payment stats for user {user_id}: {str(e)}")
        raise

@shared_task(queue='reports')
def generate_monthly_statement(user_id, month, year):
    """
    Generate monthly account statement for a user
    """
    try:
        user = UserProfile.objects.get(pk=user_id)
        start_date = timezone.datetime(year, month, 1)
        end_date = start_date + timedelta(days=32)
        end_date = end_date.replace(day=1) - timedelta(days=1)
        
        transactions = Transaction.objects.filter(
            user=user,
            created_at__range=(start_date, end_date)
        ).order_by('created_at')
        
        # Generate PDF statement (mock implementation)
        # statement = generate_pdf_statement(user, transactions, month, year)
        # send_statement_to_user(user, statement)
        
        logger.info(f"Generated monthly statement for user {user_id}")
        
        return {'success': True, 'transaction_count': transactions.count()}
        
    except Exception as e:
        logger.error(f"Failed to generate statement for user {user_id}: {str(e)}")
        raise

# --- GraphQL Mutation Tasks ---
@shared_task(bind=True, queue='high_priority')
def async_transfer_money(self, sender_id, recipient_data, amount, narration, pin):
    """
    Handle money transfer from GraphQL mutation asynchronously
    """
    try:
        sender = UserProfile.objects.get(pk=sender_id)
        sender_account = sender.accounts.first()
        
        # Verify PIN
        if not sender_account.check_pin(pin):
            return {'success': False, 'error': 'Invalid PIN'}
        
        # Find recipient account
        try:
            if recipient_data.get('bank_code'):
                recipient_account = Account.objects.get(
                    account_number=recipient_data['account_number'],
                    bank__code=recipient_data['bank_code']
                )
                fee = recipient_account.bank.transfer_fee
            else:
                recipient_account = Account.objects.get(
                    account_number=recipient_data['account_number']
                )
                fee = 0.00
        except Account.DoesNotExist:
            return {'success': False, 'error': 'Recipient account not found'}
        
        # Create transfer record
        transfer = MoneyTransfer.objects.create(
            sender=sender,
            receiver=recipient_account.user,
            sender_account=sender_account,
            receiver_account=recipient_account,
            amount=amount,
            fee=fee,
            narration=narration,
            status='pending'
        )
        
        # Process transfer
        if recipient_data.get('bank_code'):
            process_interbank_transfer.delay(transfer.id)
        else:
            process_money_transfer.delay(transfer.id)
        
        return {
            'success': True,
            'transfer_id': transfer.id,
            'reference': transfer.reference
        }
        
    except Exception as e:
        logger.error(f"Async money transfer failed: {str(e)}")
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, queue='high_priority')
def async_bill_payment(self, user_id, bill_type, provider, amount, customer_reference):
    """
    Handle bill payment from GraphQL mutation asynchronously
    """
    try:
        user = UserProfile.objects.get(pk=user_id)
        
        # Create bill payment record
        payment = BillPayment.objects.create(
            user=user,
            bill_type=bill_type,
            provider=provider,
            amount=amount,
            customer_reference=customer_reference,
            status='pending'
        )
        
        # Process payment
        process_bill_payment.delay(payment.id)
        
        return {
            'success': True,
            'payment_id': payment.id,
            'reference': payment.reference
        }
        
    except Exception as e:
        logger.error(f"Async bill payment failed: {str(e)}")
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, queue='high_priority')
def async_airtime_purchase(self, user_id, network, amount):
    """
    Handle airtime purchase from GraphQL mutation asynchronously
    """
    try:
        user = UserProfile.objects.get(pk=user_id)
        
        # Create airtime purchase record
        purchase = AirtimePurchase.objects.create(
            user=user,
            network=network,
            amount=amount,
            status='pending'
        )
        
        # Process purchase
        process_airtime_purchase.delay(purchase.id)
        
        return {
            'success': True,
            'purchase_id': purchase.id,
            'reference': purchase.reference
        }
        
    except Exception as e:
        logger.error(f"Async airtime purchase failed: {str(e)}")
        raise self.retry(exc=e, countdown=30)

# --- Security Tasks ---
@shared_task(queue='security')
def check_fraudulent_activity():
    """
    Scan recent transactions for potential fraud patterns
    """
    try:
        # Get suspicious transactions (mock implementation)
        # suspicious = Transaction.objects.filter(
        #     created_at__gte=timezone.now() - timedelta(hours=1),
        #     amount__gte=1000
        # ).exclude(user__in=verified_users)
        
        # for tx in suspicious:
        #     create_fraud_alert(tx)
        
        logger.info("Completed fraud detection scan")
        return {'checked': 0, 'flagged': 0}  # Replace with actual counts
        
    except Exception as e:
        logger.error(f"Fraud detection failed: {str(e)}")
        raise

@shared_task(queue='security')
def block_compromised_accounts():
    """
    Automatically block accounts with suspicious activity
    """
    try:
        # Get accounts with multiple failed login attempts
        # compromised = get_compromised_accounts()
        # for account in compromised:
        #     account.is_active = False
        #     account.save()
        #     send_security_alert(account.user)
        
        logger.info("Completed compromised account check")
        return {'checked': 0, 'blocked': 0}  # Replace with actual counts
        
    except Exception as e:
        logger.error(f"Compromised account check failed: {str(e)}")
        raise'''