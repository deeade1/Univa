# payment/services/payment_service.py

from decimal import Decimal
from typing import Optional, Dict, Any

from django.db import transaction as db_transaction
from django.utils import timezone

from payment.models import Payment, Transaction, PaymentMethod
from payment.gateways import get_gateway
from banking.services.banking_orchestrator import BankingOrchestrator


class PaymentService:
    """
    Canonical payment orchestrator for Univa.
    
    This service orchestrates all payments across Univa domains:
    - Ecommerce purchases
    - Transport rides
    - Real estate bookings
    - Any other domain that needs payment
    """
    
    @classmethod
    def create_payment(
        cls,
        user,
        amount: Decimal,
        currency: str = "NGN",
        gateway: str = "paystack",
        payment_method: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Payment:
        """
        Create a payment and initiate the payment flow.
        
        This is the entry point for all payments in Univa.
        """
        # Create payment record
        payment = Payment.objects.create(
            user=user,
            amount=amount,
            currency=currency,
            status="PENDING",
            gateway=gateway,
            payment_method=payment_method,
            metadata=metadata or {},
        )
        
        # Create transaction
        transaction = Transaction.objects.create(
            payment=payment,
            amount=amount,
            currency=currency,
            status="PENDING",
            gateway=gateway,
        )
        
        # Get gateway and initiate payment
        gateway_instance = get_gateway(gateway)
        result = gateway_instance.initiate_payment(
            payment=payment,
            transaction=transaction,
            amount=amount,
            currency=currency,
        )
        
        if result.get("success"):
            payment.status = "AUTHORIZED"
            payment.gateway_reference = result.get("reference")
            payment.save()
            
            transaction.status = "AUTHORIZED"
            transaction.gateway_reference = result.get("reference")
            transaction.save()
        
        return payment