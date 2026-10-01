# apps/backend/banking/api/ussd.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging

from banking.services.ussd_service import USSDService

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def ussd_callback(request):
    """Handle USSD callbacks from telcos"""
    try:
        data = json.loads(request.body)
        
        # Extract USSD parameters (varies by telco)
        phone_number = data.get('msisdn') or data.get('phoneNumber')
        ussd_code = data.get('ussdString') or data.get('input')
        session_id = data.get('sessionId')
        telco = data.get('telco', 'UNKNOWN')
        
        if not phone_number or not ussd_code:
            return JsonResponse({
                'error': 'Missing parameters'
            }, status=400)
        
        # Process USSD request
        ussd_service = USSDService()
        response = ussd_service.process_ussd_request(
            phone_number=phone_number,
            ussd_code=ussd_code,
            session_id=session_id
        )
        
        # Format response for telco
        telco_response = {
            'sessionId': session_id,
            'message': response['response'],
            'continueSession': response['continue_session']
        }
        
        # Add telco-specific fields
        if telco == 'MTN':
            telco_response['ussdServiceOp'] = '2' if response['continue_session'] else '1'
        elif telco == 'AIRTEL':
            telco_response['action'] = 'prompt' if response['continue_session'] else 'end'
        
        return JsonResponse(telco_response)
        
    except Exception as e:
        logger.error(f"USSD callback error: {str(e)}")
        return JsonResponse({
            'error': 'Internal server error'
        }, status=500)
        
        
        
# apps/backend/banking/api/remittance.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
import json
import logging

from banking.services.remittance_service import InternationalRemittanceService

logger = logging.getLogger(__name__)

@login_required
@require_GET
def get_exchange_rate(request):
    """Get exchange rate for currency pair"""
    try:
        source_currency = request.GET.get('from', 'NGN')
        target_currency = request.GET.get('to', 'USD')
        amount = request.GET.get('amount')
        
        service = InternationalRemittanceService()
        
        rate_info = service.get_exchange_rate(
            source_currency=source_currency,
            target_currency=target_currency,
            amount=Decimal(amount) if amount else None
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'source_currency': source_currency,
                'target_currency': target_currency,
                'exchange_rate': str(rate_info['rate']),
                'inverse_rate': str(rate_info['inverse_rate']),
                'fee_percentage': str(rate_info.get('fee_percentage', '0.00')),
                'provider': rate_info.get('provider'),
                'last_updated': rate_info.get('last_updated')
            }
        })
        
    except Exception as e:
        logger.error(f"Exchange rate fetch failed: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
@require_POST
def initiate_international_transfer(request):
    """Initiate international money transfer"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['source_amount', 'target_currency', 'recipient_name', 
                          'recipient_country', 'payout_method']
        
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=400)
        
        # Get exchange rate
        service = InternationalRemittanceService(data.get('provider'))
        
        rate_info = service.get_exchange_rate(
            source_currency=data.get('source_currency', 'NGN'),
            target_currency=data['target_currency'],
            amount=Decimal(data['source_amount'])
        )
        
        # Calculate target amount
        target_amount = Decimal(data['source_amount']) * rate_info['rate']
        
        # Prepare transfer data
        transfer_data = {
            'source_amount': Decimal(data['source_amount']),
            'source_currency': data.get('source_currency', 'NGN'),
            'target_amount': target_amount,
            'target_currency': data['target_currency'],
            'exchange_rate': rate_info['rate'],
            'provider_fee': rate_info.get('fee', Decimal('0.00')),
            'platform_fee': Decimal('0.00'),  # Your platform fee
            'payout_method': data['payout_method'],
            'recipient_name': data['recipient_name'],
            'recipient_phone': data.get('recipient_phone'),
            'recipient_email': data.get('recipient_email'),
            'recipient_country': data['recipient_country'],
            'recipient_bank': data.get('recipient_bank'),
            'recipient_account': data.get('recipient_account'),
            'purpose': data.get('purpose', 'Family Support'),
            'source_of_funds': data.get('source_of_funds', 'Personal Savings')
        }
        
        # Initiate transfer
        transfer = service.initiate_international_transfer(
            sender=request.user.userprofile,
            transfer_data=transfer_data
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'transfer_reference': transfer.reference,
                'external_reference': transfer.external_reference,
                'status': transfer.status,
                'estimated_delivery': transfer.estimated_delivery,
                'source_amount': str(transfer.source_amount),
                'source_currency': transfer.source_currency,
                'target_amount': str(transfer.target_amount),
                'target_currency': transfer.target_currency,
                'exchange_rate': str(transfer.exchange_rate),
                'total_fee': str(transfer.total_fee)
            }
        })
        
    except Exception as e:
        logger.error(f"International transfer failed: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
@require_GET
def track_transfer(request):
    """Track transfer status"""
    try:
        transfer_reference = request.GET.get('reference')
        
        if not transfer_reference:
            return JsonResponse({
                'success': False,
                'error': 'Transfer reference is required'
            }, status=400)
        
        service = InternationalRemittanceService()
        status_info = service.track_transfer_status(transfer_reference)
        
        return JsonResponse({
            'success': True,
            'data': status_info
        })
        
    except Exception as e:
        logger.error(f"Transfer tracking failed: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@csrf_exempt
@require_POST
def remittance_webhook(request, provider):
    """Handle remittance webhooks from providers"""
    try:
        data = json.loads(request.body)
        signature = request.headers.get('X-Webhook-Signature')
        
        # Verify webhook signature
        from ..services.webhook_service import WebhookService
        webhook_service = WebhookService()
        
        # Process based on provider
        service = InternationalRemittanceService(provider.upper())
        
        if provider.lower() == 'flutterwave':
            # Process Flutterwave webhook
            if data.get('event') == 'transfer.completed':
                # Update transfer status
                pass
            elif data.get('event') == 'transfer.failed':
                # Handle failed transfer
                pass
        
        elif provider.lower() == 'wise':
            # Process Wise webhook
            pass
        
        return JsonResponse({'status': 'received'})
        
    except Exception as e:
        logger.error(f"Remittance webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)