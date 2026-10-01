# apps/backend/ecommerce/services/checkout/payment_utils.py
"""Payment utilities for checkout."""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import uuid4

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


def process_payment(
    checkout: Any,
    total: Any,
    currency: str,
    user: Any,
) -> Dict[str, Any]:
    """
    Process payment for a checkout.
    
    Args:
        checkout: Checkout object
        total: Total amount to charge
        currency: Currency code
        user: User making the payment
        
    Returns:
        Dict: Payment result with status and details
    """
    try:
        # Get or create payment object
        payment = _create_payment_object(checkout, total, currency, user)
        
        # Process payment based on gateway
        gateway = checkout.gateway if hasattr(checkout, 'gateway') else 'default'
        payment_result = _process_with_gateway(payment, gateway)
        
        # Update payment status
        if payment_result['success']:
            _mark_payment_completed(payment, payment_result)
        else:
            _mark_payment_failed(payment, payment_result)
        
        return {
            'success': payment_result['success'],
            'payment_id': str(payment.id),
            'transaction_id': payment_result.get('transaction_id'),
            'message': payment_result.get('message', 'Payment processed'),
            'status': payment.status if hasattr(payment, 'status') else 'completed',
        }
        
    except Exception as e:
        logger.exception(f"Payment processing failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Payment processing failed',
        }


def _create_payment_object(checkout: Any, total: Any, currency: str, user: Any) -> Any:
    """Create a payment object for the checkout."""
    from payment.models import Payment
    
    # Check if payment already exists
    existing_payment = checkout.get_last_active_payment()
    if existing_payment:
        return existing_payment
    
    # Create new payment
    with transaction.atomic():
        payment = Payment.objects.create(
            checkout=checkout,
            user=user,
            total=total.amount if hasattr(total, 'amount') else Decimal(str(total)),
            currency=currency,
            gateway=_get_gateway(checkout),
            is_active=True,
            charge_status='NOT_CHARGED',
            token=str(uuid4()),
            billing_email=user.email if user else checkout.email,
            billing_first_name=checkout.billing_address.first_name if checkout.billing_address else '',
            billing_last_name=checkout.billing_address.last_name if checkout.billing_address else '',
            billing_address_1=checkout.billing_address.street_address_1 if checkout.billing_address else '',
            billing_city=checkout.billing_address.city if checkout.billing_address else '',
            billing_country_code=checkout.billing_address.country_code if checkout.billing_address else '',
            billing_postal_code=checkout.billing_address.postal_code if checkout.billing_address else '',
            payment_method_type=getattr(checkout, 'payment_method_type', ''),
            customer_ip_address=getattr(checkout, 'customer_ip_address', None),
            return_url=getattr(checkout, 'return_url', ''),
        )
        
        return payment


def _get_gateway(checkout: Any) -> str:
    """Get the payment gateway from checkout."""
    if hasattr(checkout, 'gateway') and checkout.gateway:
        return checkout.gateway
    return getattr(settings, 'DEFAULT_PAYMENT_GATEWAY', 'stripe')


def _process_with_gateway(payment: Any, gateway: str) -> Dict[str, Any]:
    """Process payment with the specified gateway."""
    
    if gateway == 'stripe':
        return _process_stripe_payment(payment)
    elif gateway == 'paystack':
        return _process_paystack_payment(payment)
    elif gateway == 'flutterwave':
        return _process_flutterwave_payment(payment)
    elif gateway == 'paypal':
        return _process_paypal_payment(payment)
    else:
        # Default: mock payment for testing
        return {
            'success': True,
            'transaction_id': f'txn_{uuid4().hex[:12]}',
            'message': 'Payment processed successfully (mock)',
        }


def _process_stripe_payment(payment: Any) -> Dict[str, Any]:
    """Process payment with Stripe."""
    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(payment.total * 100),  # Convert to cents
            currency=payment.currency.lower(),
            metadata={
                'payment_id': str(payment.id),
                'checkout_id': str(payment.checkout_id),
            },
        )
        
        return {
            'success': True,
            'transaction_id': intent.id,
            'client_secret': intent.client_secret,
            'message': 'Payment intent created',
        }
        
    except Exception as e:
        logger.exception(f"Stripe payment failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Stripe payment failed',
        }


def _process_paystack_payment(payment: Any) -> Dict[str, Any]:
    """Process payment with Paystack."""
    try:
        import requests
        
        headers = {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        
        data = {
            'amount': int(payment.total * 100),  # Convert to kobo
            'currency': payment.currency,
            'email': payment.billing_email,
            'metadata': {
                'payment_id': str(payment.id),
                'checkout_id': str(payment.checkout_id),
            },
        }
        
        response = requests.post(
            'https://api.paystack.co/transaction/initialize',
            json=data,
            headers=headers,
        )
        
        result = response.json()
        
        if result.get('status'):
            return {
                'success': True,
                'transaction_id': result['data']['reference'],
                'authorization_url': result['data']['authorization_url'],
                'message': 'Payment initialized',
            }
        else:
            return {
                'success': False,
                'error': result.get('message', 'Paystack error'),
                'message': 'Paystack payment failed',
            }
            
    except Exception as e:
        logger.exception(f"Paystack payment failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Paystack payment failed',
        }


def _process_flutterwave_payment(payment: Any) -> Dict[str, Any]:
    """Process payment with Flutterwave."""
    try:
        import requests
        
        headers = {
            'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        
        data = {
            'tx_ref': f'txn_{uuid4().hex[:12]}',
            'amount': str(payment.total),
            'currency': payment.currency,
            'redirect_url': payment.return_url,
            'payment_options': 'card',
            'meta': {
                'payment_id': str(payment.id),
                'checkout_id': str(payment.checkout_id),
            },
            'customer': {
                'email': payment.billing_email,
                'name': f"{payment.billing_first_name} {payment.billing_last_name}",
            },
            'customizations': {
                'title': 'Payment',
                'description': 'Checkout payment',
            },
        }
        
        response = requests.post(
            'https://api.flutterwave.com/v3/payments',
            json=data,
            headers=headers,
        )
        
        result = response.json()
        
        if result.get('status') == 'success':
            return {
                'success': True,
                'transaction_id': result['data']['tx_ref'],
                'authorization_url': result['data']['link'],
                'message': 'Payment initialized',
            }
        else:
            return {
                'success': False,
                'error': result.get('message', 'Flutterwave error'),
                'message': 'Flutterwave payment failed',
            }
            
    except Exception as e:
        logger.exception(f"Flutterwave payment failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Flutterwave payment failed',
        }


def _process_paypal_payment(payment: Any) -> Dict[str, Any]:
    """Process payment with PayPal."""
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        
        # Get access token
        auth = HTTPBasicAuth(
            settings.PAYPAL_CLIENT_ID,
            settings.PAYPAL_SECRET
        )
        
        token_response = requests.post(
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            auth=auth,
            data={'grant_type': 'client_credentials'},
        )
        
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        
        # Create order
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        data = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {
                    'currency_code': payment.currency,
                    'value': str(payment.total),
                },
                'description': f'Checkout {payment.checkout_id}',
            }],
        }
        
        response = requests.post(
            'https://api-m.sandbox.paypal.com/v2/checkout/orders',
            json=data,
            headers=headers,
        )
        
        result = response.json()
        
        if result.get('id'):
            return {
                'success': True,
                'transaction_id': result['id'],
                'authorization_url': result['links'][1]['href'],
                'message': 'Payment initialized',
            }
        else:
            return {
                'success': False,
                'error': result.get('message', 'PayPal error'),
                'message': 'PayPal payment failed',
            }
            
    except Exception as e:
        logger.exception(f"PayPal payment failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'PayPal payment failed',
        }


def _mark_payment_completed(payment: Any, result: Dict[str, Any]):
    """Mark payment as completed."""
    payment.charge_status = 'FULLY_CHARGED'
    payment.captured_amount = payment.total
    payment.psp_reference = result.get('transaction_id')
    payment.save(update_fields=['charge_status', 'captured_amount', 'psp_reference'])
    
    # Create transaction record
    from payment.models import Transaction, TransactionKind
    
    Transaction.objects.create(
        payment=payment,
        kind=TransactionKind.CAPTURE,
        is_success=True,
        amount=payment.total,
        currency=payment.currency,
        token=result.get('transaction_id', ''),
        gateway_response=result,
    )


def _mark_payment_failed(payment: Any, result: Dict[str, Any]):
    """Mark payment as failed."""
    payment.is_active = False
    payment.save(update_fields=['is_active'])
    
    # Create transaction record
    from payment.models import Transaction, TransactionKind
    
    Transaction.objects.create(
        payment=payment,
        kind=TransactionKind.CAPTURE,
        is_success=False,
        amount=payment.total,
        currency=payment.currency,
        error=result.get('error', 'Payment failed'),
        gateway_response=result,
    )