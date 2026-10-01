'''from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from typing import Dict, Any, Optional
import requests
import json
from ..models.bill_payments import Biller, BillPayment, AirtimePurchase, DataBundlePurchase
from ..models.core import User, Wallet
from ..utils.helpers import generate_reference
from .wallet_service import WalletService
from .notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)

class BillPaymentService:
    """Service for bill payments"""
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    def validate_customer(self, biller_code: str, customer_id: str) -> Dict:
        """Validate customer details with the biller"""
        biller = Biller.objects.get(code=biller_code)
        
        # Call external API to validate customer
        # This is a placeholder - implement actual API call
        validation_data = {
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'customer_phone': '08012345678',
            'is_valid': True
        }
        
        return validation_data
    
    def pay_bill(self, user: User, biller_code: str, customer_id: str,
                 amount: Decimal, metadata: Dict = None) -> BillPayment:
        """Process a bill payment"""
        biller = Biller.objects.get(code=biller_code)
        wallet = user.wallets.filter(is_default=True).first()
        
        if not wallet:
            raise ValueError("User has no default wallet")
        
        if wallet.available_balance < amount:
            raise ValueError(f"Insufficient balance. Available: {wallet.available_balance}")
        
        # Validate customer
        customer_data = self.validate_customer(biller_code, customer_id)
        if not customer_data.get('is_valid'):
            raise ValueError("Invalid customer ID")
        
        # Calculate fees
        total_amount = amount + biller.convenience_fee
        
        with transaction.atomic():
            # Debit wallet
            debit_tx = WalletService.debit_wallet(
                wallet,
                total_amount,
                f"Bill Payment: {biller.name}",
                metadata={
                    'biller_code': biller_code,
                    'customer_id': customer_id,
                    'biller_name': biller.name
                }
            )
            
            # Create bill payment record
            bill_payment = BillPayment.objects.create(
                transaction=debit_tx,
                user=user,
                biller=biller,
                customer_id=customer_id,
                customer_name=customer_data.get('customer_name', ''),
                customer_email=customer_data.get('customer_email', ''),
                customer_phone=customer_data.get('customer_phone', ''),
                amount=amount,
                fee=biller.convenience_fee,
                total_amount=total_amount,
                status='PROCESSING',
                initiated_at=timezone.now()
            )
            
            # Process payment with external API
            try:
                payment_result = self.process_bill_payment(bill_payment)
                bill_payment.status = 'SUCCESS'
                bill_payment.provider_reference = payment_result.get('reference')
                bill_payment.completed_at = timezone.now()
                bill_payment.save()
                
                # Notify user
                self.notification_service.send_bill_payment_notification(
                    user, bill_payment, 'SUCCESS'
                )
                
            except Exception as e:
                bill_payment.status = 'FAILED'
                bill_payment.status_reason = str(e)
                bill_payment.save()
                
                # Reverse transaction
                WalletService.fund_wallet(
                    wallet,
                    total_amount,
                    f"Bill Payment Reversal: {biller.name}",
                    metadata={'original_transaction': debit_tx.reference}
                )
                
                raise
            
            return bill_payment
    
    def process_bill_payment(self, bill_payment: BillPayment) -> Dict:
        """Process bill payment with external provider"""
        # Placeholder for actual API call
        return {
            'status': 'SUCCESS',
            'reference': generate_reference('BILL')
        }
    
    def get_bill_history(self, user: User, limit: int = 20) -> list:
        """Get user's bill payment history"""
        return BillPayment.objects.filter(user=user).order_by('-initiated_at')[:limit]
    
    def get_biller_by_category(self, category_slug: str) -> list:
        """Get billers by category"""
        return Biller.objects.filter(category__slug=category_slug, is_active=True)

class AirtimeService:
    """Service for airtime top-up"""
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    def purchase_airtime(self, user: User, phone_number: str, amount: Decimal,
                         operator: str) -> AirtimePurchase:
        """Purchase airtime"""
        wallet = user.wallets.filter(is_default=True).first()
        
        if not wallet:
            raise ValueError("User has no default wallet")
        
        if wallet.available_balance < amount:
            raise ValueError(f"Insufficient balance. Available: {wallet.available_balance}")
        
        with transaction.atomic():
            # Debit wallet
            debit_tx = WalletService.debit_wallet(
                wallet,
                amount,
                f"Airtime Purchase: {operator}",
                metadata={
                    'phone_number': phone_number,
                    'operator': operator
                }
            )
            
            # Create airtime purchase record
            airtime = AirtimePurchase.objects.create(
                transaction=debit_tx,
                user=user,
                phone_number=phone_number,
                operator=operator,
                amount=amount,
                status='PROCESSING'
            )
            
            # Process with external API
            try:
                result = self.process_airtime_purchase(airtime)
                airtime.status = 'SUCCESS'
                airtime.provider_reference = result.get('reference')
                airtime.bonus_amount = result.get('bonus', 0)
                airtime.completed_at = timezone.now()
                airtime.save()
                
                self.notification_service.send_airtime_notification(
                    user, airtime, 'SUCCESS'
                )
                
            except Exception as e:
                airtime.status = 'FAILED'
                airtime.save()
                
                # Reverse transaction
                WalletService.fund_wallet(
                    wallet,
                    amount,
                    f"Airtime Reversal: {operator}",
                    metadata={'original_transaction': debit_tx.reference}
                )
                
                raise
            
            return airtime
    
    def process_airtime_purchase(self, airtime: AirtimePurchase) -> Dict:
        """Process airtime purchase with external provider"""
        # Placeholder for actual API call
        return {
            'status': 'SUCCESS',
            'reference': generate_reference('AIRTIME'),
            'bonus': Decimal('0.00')
        }

class DataBundleService:
    """Service for data bundle purchases"""
    
    def purchase_data_bundle(self, user: User, phone_number: str,
                            bundle_data: Dict) -> DataBundlePurchase:
        """Purchase data bundle"""
        wallet = user.wallets.filter(is_default=True).first()
        
        if not wallet:
            raise ValueError("User has no default wallet")
        
        amount = Decimal(str(bundle_data.get('price', 0)))
        
        if wallet.available_balance < amount:
            raise ValueError(f"Insufficient balance. Available: {wallet.available_balance}")
        
        with transaction.atomic():
            debit_tx = WalletService.debit_wallet(
                wallet,
                amount,
                f"Data Purchase: {bundle_data.get('operator')}",
                metadata={
                    'phone_number': phone_number,
                    'bundle': bundle_data
                }
            )
            
            data_purchase = DataBundlePurchase.objects.create(
                transaction=debit_tx,
                user=user,
                phone_number=phone_number,
                operator=bundle_data.get('operator'),
                bundle_name=bundle_data.get('name'),
                data_amount=bundle_data.get('data_amount'),
                data_type=bundle_data.get('data_type'),
                price=amount,
                validity_days=bundle_data.get('validity_days', 30),
                status='PROCESSING'
            )
            
            try:
                result = self.process_data_purchase(data_purchase)
                data_purchase.status = 'SUCCESS'
                data_purchase.provider_reference = result.get('reference')
                data_purchase.completed_at = timezone.now()
                data_purchase.save()
                
            except Exception as e:
                data_purchase.status = 'FAILED'
                data_purchase.save()
                
                WalletService.fund_wallet(
                    wallet,
                    amount,
                    f"Data Reversal: {bundle_data.get('operator')}",
                    metadata={'original_transaction': debit_tx.reference}
                )
                
                raise
            
            return data_purchase
    
    def process_data_purchase(self, data_purchase: DataBundlePurchase) -> Dict:
        """Process data purchase with external provider"""
        return {
            'status': 'SUCCESS',
            'reference': generate_reference('DATA')
        }'''