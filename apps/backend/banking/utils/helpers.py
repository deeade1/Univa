# apps/backend/banking/utils/helpers.py
'''import re
from decimal import Decimal

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_minimum_balance_for_type(account_type, currency='NGN'):
    """Get minimum balance requirement for account type"""
    minimums = {
        'SAVINGS': Decimal('500.00'),
        'CURRENT': Decimal('1000.00'),
        'BUSINESS': Decimal('5000.00'),
        'DOMICILIARY': Decimal('100.00'),  # In USD
    }
    
    min_amount = minimums.get(account_type, Decimal('0.00'))
    
    # Convert to currency if needed
    if currency == 'USD' and account_type != 'DOMICILIARY':
        # Rough conversion (would use actual rates in production)
        min_amount = min_amount / Decimal('750.00')
    
    return min_amount

def validate_nigerian_phone(phone_number):
    """Validate Nigerian phone number format"""
    # Remove all non-digits
    cleaned = re.sub(r'\D', '', phone_number)
    
    # Check if it's a valid Nigerian number
    if cleaned.startswith('234'):
        if len(cleaned) == 13:  # 234 + 10 digits
            return True
    elif cleaned.startswith('0'):
        if len(cleaned) == 11:  # 0 + 10 digits
            return True
    
    return False

def generate_transaction_reference(prefix='TX'):
    """Generate unique transaction reference"""
    import uuid
    from django.utils import timezone
    
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # Millisecond precision
    unique_id = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{timestamp}-{unique_id}'''