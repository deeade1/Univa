import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

logger = logging.getLogger(__name__)

class PropertyValuationService:
    """Service for property valuation calculations"""
    
    @staticmethod
    def calculate_mortgage(principal, annual_rate, years):
        """
        Calculate mortgage details
        """
        try:
            if principal <= 0 or annual_rate <= 0 or years <= 0:
                raise ValidationError("All parameters must be positive")
                
            monthly_rate = Decimal(annual_rate) / Decimal(100) / Decimal(12)
            num_payments = Decimal(years) * Decimal(12)
            
            if monthly_rate == 0:
                monthly_payment = principal / num_payments
            else:
                monthly_payment = (
                    principal * 
                    (monthly_rate * (1 + monthly_rate) ** num_payments) / 
                    ((1 + monthly_rate) ** num_payments - 1)
                )
            
            total_payment = monthly_payment * num_payments
            total_interest = total_payment - principal
            
            return {
                'monthly_payment': round(monthly_payment, 2),
                'total_interest': round(total_interest, 2),
                'total_payment': round(total_payment, 2),
                'num_payments': int(num_payments)
            }
            
        except Exception as e:
            logger.error(f"Mortgage calculation error: {e}")
            raise ValidationError(f"Mortgage calculation failed: {e}")

    @staticmethod
    def calculate_roi(purchase_price, down_payment, interest_rate, loan_term,
                     monthly_rent, annual_appreciation, expenses_percent, years=5):
        """
        Calculate investment ROI
        """
        try:
            # Basic ROI calculation
            loan_amount = purchase_price - down_payment
            monthly_expenses = (monthly_rent * expenses_percent) / 100
            
            # Simple cash flow calculation
            monthly_cash_flow = monthly_rent - monthly_expenses
            
            # Appreciation
            future_value = purchase_price * ((1 + annual_appreciation/100) ** years)
            
            # Total return
            total_rent_income = monthly_cash_flow * 12 * years
            appreciation_gain = future_value - purchase_price
            
            total_return = total_rent_income + appreciation_gain
            roi_percentage = (total_return / down_payment) * 100
            
            return {
                'cash_flow_monthly': round(monthly_cash_flow, 2),
                'total_rent_income': round(total_rent_income, 2),
                'appreciation_gain': round(appreciation_gain, 2),
                'total_return': round(total_return, 2),
                'roi_percentage': round(roi_percentage, 2),
                'future_value': round(future_value, 2)
            }
            
        except Exception as e:
            logger.error(f"ROI calculation error: {e}")
            raise ValidationError(f"ROI calculation failed: {e}")