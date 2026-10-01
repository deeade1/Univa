# apps/backend/payment/discounts.py

from django.db import models
from decimal import Decimal

class UnivaDiscount(models.Model):
    """Model to manage Univa payment discounts"""
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    min_transaction_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    
    def calculate_discount(self, amount):
        """Calculate discount for given amount"""
        if amount < self.min_transaction_amount:
            return Decimal('0.00')
        
        discount = (self.discount_percentage / 100) * amount
        if discount > self.max_discount_amount:
            discount = self.max_discount_amount
        return discount

def apply_univa_discount(transaction_amount, user=None):
    """Apply discount when user uses Univa payment"""
    try:
        discount_config = UnivaDiscount.objects.get(is_active=True)
        discount_amount = discount_config.calculate_discount(transaction_amount)
        return {
            'discount': discount_amount,
            'final_amount': transaction_amount - discount_amount,
            'savings': discount_amount
        }
    except UnivaDiscount.DoesNotExist:
        return {
            'discount': Decimal('0.00'),
            'final_amount': transaction_amount,
            'savings': Decimal('0.00')
        }