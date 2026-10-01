# apps/backend/graphq/banking/signals.py
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from graphq.banking.subscription import TransactionSubscription

from .models import Transaction
from .models.core import AuditLog
from .models.payments import MoneyTransfer, Transaction
from .services.fraud_service import FraudDetectionService
from .services.notification_service import NotificationService


@receiver(post_save, sender=UserProfile)
def create_user_account(sender, instance, created, **kwargs):
    """Automatically create Account and related records for new UserProfile"""
    if created and not hasattr(instance, 'account'):
        with transaction.atomic():
            account = Account.objects.create(user=instance)
            Balance.objects.create(user=instance)
            PaymentStat.objects.create(user=instance)
            
            # Create default transaction limits
            TransactionLimit.objects.create(
                user=instance,
                limit_type=TransactionLimit.DAILY,
                amount=1000.00,
                reset_period='daily'
            )
            TransactionLimit.objects.create(
                user=instance,
                limit_type=TransactionLimit.PER_TRANSACTION,
                amount=500.00,
                reset_period='none'
            )

@receiver(post_save, sender=Transaction)
def transaction_created(sender, instance, created, **kwargs):
    if created:
        TransactionSubscription.broadcast(
            group=f"user_{instance.user.id}",
            payload=instance
        )


@receiver(post_save, sender=Transaction)
def handle_transaction_creation(sender, instance, created, **kwargs):
    """Handle new transaction creation"""
    if created:
        # Real-time update via GraphQL subscription
        TransactionSubscription.broadcast(
            group=f"user_{instance.user.id}",
            payload=instance
        )
        
        # Fraud detection
        fraud_service = FraudDetectionService()
        fraud_risks = fraud_service.analyze_transaction({
            'sender': instance.sender,
            'receiver': instance.recipient,
            'amount': instance.amount,
            'type': instance.transaction_type,
            'reference': instance.reference
        })
        
        # Create audit log
        AuditLog.objects.create(
            user=instance.user,
            action='TRANSACTION',
            resource_type='Transaction',
            resource_id=instance.id,
            description=f"{instance.get_transaction_type_display()} of ${instance.amount}",
            metadata={
                'reference': instance.reference,
                'type': instance.transaction_type,
                'fraud_risks': fraud_risks
            }
        )

@receiver(post_save, sender=MoneyTransfer)
def handle_money_transfer(sender, instance, created, **kwargs):
    """Handle money transfer completion"""
    if instance.status == 'completed' and not created:
        # Send external webhooks
        from .services.webhook_service import WebhookService
        webhook_service = WebhookService()
        webhook_service.send_webhook('transfer.completed', {
            'reference': instance.reference,
            'amount': float(instance.amount),
            'sender': str(instance.sender),
            'receiver': str(instance.receiver),
            'timestamp': instance.created_at.isoformat()
        })

@receiver(pre_save, sender=Account)
def audit_account_changes(sender, instance, **kwargs):
    """Audit account changes"""
    if instance.pk:
        old_instance = Account.objects.get(pk=instance.pk)
        if old_instance.is_active != instance.is_active:
            AuditLog.objects.create(
                user=instance.user,
                action='UPDATE',
                resource_type='Account',
                resource_id=instance.id,
                description=f"Account status changed to {instance.is_active}",
                metadata={
                    'old_status': old_instance.is_active,
                    'new_status': instance.is_active
                }
            )