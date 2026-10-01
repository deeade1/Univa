    
class InternationalRemittanceService:
    """Handle international money transfers"""
    
    def __init__(self, provider_code=None):
        from ..models.remittance import RemittanceProvider
        self.provider = self._get_provider(provider_code)
        self.session = requests.Session()
    
    def _get_provider(self, provider_code=None):
        """Get remittance provider"""
        from ..models.remittance import RemittanceProvider
        
        if provider_code:
            return RemittanceProvider.objects.filter(
                provider_code=provider_code,
                is_active=True
            ).first()
        
        # Get default provider
        return RemittanceProvider.objects.filter(is_active=True).first()
    
    def get_exchange_rate(self, source_currency: str, target_currency: str, amount: Decimal = None) -> Dict:
        """Get exchange rate for currency pair"""
        
        if source_currency == target_currency:
            return {
                'rate': Decimal('1.000000'),
                'inverse_rate': Decimal('1.000000'),
                'fee_percentage': Decimal('0.00'),
                'provider_margin': Decimal('0.00')
            }
        
        # Try to get rate from database
        from ..models.remittance import ExchangeRate
        exchange_rate = ExchangeRate.objects.filter(
            base_currency=source_currency,
            target_currency=target_currency,
            is_active=True
        ).order_by('-last_updated').first()
        
        if not exchange_rate:
            # Fetch live rate from provider
            return self._fetch_live_rate(source_currency, target_currency, amount)
        
        # Calculate applicable rate
        if amount:
            # Apply tiered rates based on amount
            rate = self._calculate_tiered_rate(exchange_rate, amount)
        else:
            rate = exchange_rate.sell_rate if source_currency == 'NGN' else exchange_rate.buy_rate
        
        return {
            'rate': rate,
            'inverse_rate': Decimal('1.000000') / rate,
            'provider': exchange_rate.provider.name if exchange_rate.provider else 'SYSTEM',
            'last_updated': exchange_rate.last_updated,
            'fee_percentage': self._calculate_fee_percentage(amount, source_currency),
            'provider_margin': exchange_rate.provider.exchange_margin if exchange_rate.provider else Decimal('0.00')
        }
    
    def _fetch_live_rate(self, source_currency: str, target_currency: str, amount: Decimal = None) -> Dict:
        """Fetch live exchange rate from provider"""
        
        # Try different providers in order
        providers = ['WISE', 'FLUTTERWAVE', 'PAYSTACK']
        
        for provider_code in providers:
            try:
                if provider_code == 'WISE':
                    return self._fetch_wise_rate(source_currency, target_currency, amount)
                elif provider_code == 'FLUTTERWAVE':
                    return self._fetch_flutterwave_rate(source_currency, target_currency)
                elif provider_code == 'PAYSTACK':
                    return self._fetch_paystack_rate(source_currency, target_currency)
            except Exception as e:
                logger.warning(f"Failed to fetch rate from {provider_code}: {str(e)}")
                continue
        
        # Fallback to fixed rate
        return self._get_fallback_rate(source_currency, target_currency)
    
    def _fetch_wise_rate(self, source_currency: str, target_currency: str, amount: Decimal) -> Dict:
        """Fetch rate from Wise API"""
        url = "https://api.transferwise.com/v3/quotes"
        
        headers = {
            'Authorization': f'Bearer {settings.WISE_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "sourceCurrency": source_currency,
            "targetCurrency": target_currency,
            "sourceAmount": float(amount) if amount else 1000.00,
            "targetAmount": None,
            "payOut": "BANK_TRANSFER",
            "preferredPayIn": "BANK_TRANSFER"
        }
        
        response = self.session.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        return {
            'rate': Decimal(str(data['rate'])),
            'fee': Decimal(str(data['fee']['total'])),
            'provider': 'WISE',
            'provider_reference': data['id']
        }
    
    def _fetch_flutterwave_rate(self, source_currency: str, target_currency: str) -> Dict:
        """Fetch rate from Flutterwave"""
        url = f"https://api.flutterwave.com/v3/rates"
        
        headers = {
            'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'from': source_currency,
            'to': target_currency,
            'amount': 1
        }
        
        response = self.session.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'success':
            return {
                'rate': Decimal(str(data['data']['rate'])),
                'provider': 'FLUTTERWAVE'
            }
        
        raise ValueError("Failed to fetch rate from Flutterwave")
    
    def initiate_international_transfer(self, sender, transfer_data: Dict):
        """Initiate international money transfer"""
        
        with db_transaction.atomic():
            # Create transfer record
            from ..models.remittance import InternationalTransfer
            
            transfer = InternationalTransfer.objects.create(
                sender=sender,
                transfer_type='SEND',
                provider=self.provider,
                source_amount=transfer_data['source_amount'],
                source_currency=transfer_data['source_currency'],
                target_amount=transfer_data['target_amount'],
                target_currency=transfer_data['target_currency'],
                exchange_rate=transfer_data['exchange_rate'],
                provider_fee=transfer_data.get('provider_fee', Decimal('0.00')),
                platform_fee=transfer_data.get('platform_fee', Decimal('0.00')),
                payout_method=transfer_data['payout_method'],
                recipient_name=transfer_data['recipient_name'],
                recipient_phone=transfer_data['recipient_phone'],
                recipient_country=transfer_data['recipient_country'],
                purpose_of_remittance=transfer_data.get('purpose', 'Family Support'),
                source_of_funds=transfer_data.get('source_of_funds', 'Personal Savings'),
                status='PENDING'
            )
            
            # Deduct funds from sender
            from ..services.payment_service import PaymentService
            payment_service = PaymentService()
            
            # Total to deduct = source amount + fees
            total_debit = transfer.source_amount + transfer.total_fee
            
            # Check sender balance
            sender_account = sender.account
            if sender_account.balance.available_balance < total_debit:
                transfer.status = 'FAILED'
                transfer.save()
                raise ValueError("Insufficient funds for transfer")
            
            try:
                # Process through provider
                if self.provider.provider_code == 'WISE':
                    result = self._process_wise_transfer(transfer, transfer_data)
                elif self.provider.provider_code == 'FLUTTERWAVE':
                    result = self._process_flutterwave_transfer(transfer, transfer_data)
                elif self.provider.provider_code == 'WESTERN_UNION':
                    result = self._process_western_union_transfer(transfer, transfer_data)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider.provider_code}")
                
                # Update transfer with provider response
                transfer.external_reference = result.get('provider_reference')
                transfer.status = 'PROCESSING'
                transfer.initiated_at = timezone.now()
                transfer.estimated_delivery = result.get('estimated_delivery')
                transfer.save()
                
                # Deduct from sender account
                sender_account.balance.debit(
                    total_debit,
                    f"International transfer to {transfer_data['recipient_country']}"
                )
                
                # Send notifications
                from ..services.notification_service import NotificationService
                notification_service = NotificationService()
                notification_service._create_notification(
                    user=sender,
                    title="International Transfer Initiated",
                    message=f"Your transfer of {transfer_data['source_currency']} {transfer_data['source_amount']} to {transfer_data['recipient_name']} has been initiated",
                    notification_type='remittance_sent'
                )
                
                return transfer
                
            except Exception as e:
                transfer.status = 'FAILED'
                transfer.save()
                logger.error(f"International transfer failed: {str(e)}")
                raise
    
    def _process_wise_transfer(self, transfer, transfer_data):
        """Process transfer via Wise"""
        url = "https://api.transferwise.com/v1/transfers"
        
        headers = {
            'Authorization': f'Bearer {settings.WISE_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "targetAccount": transfer_data['recipient_account'],
            "quote": transfer_data['quote_id'],  # From earlier quote
            "customerTransactionId": transfer.reference,
            "details": {
                "reference": f"Transfer to {transfer_data['recipient_name']}",
                "transferPurpose": transfer.purpose_of_remittance,
                "sourceOfFunds": transfer.source_of_funds
            }
        }
        
        response = self.session.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        return {
            'provider_reference': data['id'],
            'estimated_delivery': data.get('estimatedDelivery'),
            'status': data['status']
        }
    
    def _process_flutterwave_transfer(self, transfer, transfer_data):
        """Process transfer via Flutterwave Send"""
        url = "https://api.flutterwave.com/v3/transfers"
        
        headers = {
            'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "account_bank": transfer_data['recipient_bank_code'],
            "account_number": transfer_data['recipient_account'],
            "amount": float(transfer.target_amount),
            "narration": f"International transfer to {transfer_data['recipient_name']}",
            "currency": transfer.target_currency,
            "reference": transfer.reference,
            "callback_url": f"{settings.BASE_URL}/api/remittance/callback",
            "debit_currency": transfer.source_currency,
            "beneficiary_name": transfer_data['recipient_name'],
            "meta": {
                "sender": transfer.sender.user.get_full_name(),
                "sender_country": "NG",
                "recipient_country": transfer_data['recipient_country']
            }
        }
        
        response = self.session.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'success':
            return {
                'provider_reference': data['data']['id'],
                'estimated_delivery': None,
                'status': data['data']['status']
            }
        
        raise ValueError(data.get('message', 'Transfer failed'))
    
    def track_transfer_status(self, transfer_reference: str) -> Dict:
        """Track transfer status with provider"""
        
        transfer = InternationalTransfer.objects.get(reference=transfer_reference)
        
        if not transfer.external_reference:
            return {'status': 'PENDING', 'message': 'Transfer not yet initiated with provider'}
        
        try:
            if self.provider.provider_code == 'WISE':
                status = self._track_wise_transfer(transfer.external_reference)
            elif self.provider.provider_code == 'FLUTTERWAVE':
                status = self._track_flutterwave_transfer(transfer.external_reference)
            else:
                status = {'status': 'UNKNOWN', 'message': 'Tracking not available'}
            
            # Update local status
            if status['status'] in ['COMPLETED', 'DELIVERED']:
                transfer.status = 'COMPLETED'
                transfer.delivered_at = timezone.now()
                transfer.completed_at = timezone.now()
                transfer.save()
            elif status['status'] in ['FAILED', 'CANCELLED']:
                transfer.status = 'FAILED'
                transfer.save()
            
            return status
            
        except Exception as e:
            logger.error(f"Transfer tracking failed: {str(e)}")
            return {'status': 'ERROR', 'message': str(e)}
    
    def receive_international_transfer(self, sender_data: Dict, recipient_data: Dict, amount: Decimal):
        """Handle incoming international transfer"""
        
        with db_transaction.atomic():
            from ..models.remittance import InternationalTransfer
            
            # Create receive transfer record
            transfer = InternationalTransfer.objects.create(
                sender=None,  # External sender
                recipient=recipient_data.get('user'),
                transfer_type='RECEIVE',
                provider=self.provider,
                source_amount=amount,
                source_currency=sender_data.get('currency', 'USD'),
                target_amount=self._calculate_receive_amount(amount, sender_data.get('currency')),
                target_currency='NGN',
                exchange_rate=self.get_exchange_rate(
                    sender_data.get('currency', 'USD'),
                    'NGN',
                    amount
                )['rate'],
                recipient_name=recipient_data.get('name'),
                recipient_phone=recipient_data.get('phone'),
                recipient_country='NG',
                status='PROCESSING',
                payout_method='BANK_DEPOSIT'
            )
            
            try:
                # Credit recipient account
                if recipient_data.get('user'):
                    recipient_account = recipient_data['user'].account
                    recipient_account.balance.credit(
                        transfer.target_amount,
                        f"International transfer from {sender_data.get('name')}"
                    )
                
                # Update status
                transfer.status = 'COMPLETED'
                transfer.delivered_at = timezone.now()
                transfer.completed_at = timezone.now()
                transfer.save()
                
                # Send notification
                if recipient_data.get('user'):
                    from ..services.notification_service import NotificationService
                    notification_service = NotificationService()
                    notification_service._create_notification(
                        user=recipient_data['user'],
                        title="International Transfer Received",
                        message=f"You received {transfer.source_currency} {transfer.source_amount} from {sender_data.get('name')}",
                        notification_type='remittance_received'
                    )
                
                return transfer
                
            except Exception as e:
                transfer.status = 'FAILED'
                transfer.save()
                logger.error(f"Incoming transfer processing failed: {str(e)}")
                raise
    
    def _calculate_receive_amount(self, amount: Decimal, source_currency: str) -> Decimal:
        """Calculate amount to credit in NGN"""
        rate_info = self.get_exchange_rate(source_currency, 'NGN', amount)
        return amount * rate_info['rate']
    
    def get_supported_corridors(self):
        """Get supported send/receive corridors"""
        corridors = []
        
        # Common corridors for Nigeria
        common_corridors = [
            {'from': 'NG', 'to': 'US', 'currencies': ['NGN→USD'], 'providers': ['WISE', 'FLUTTERWAVE']},
            {'from': 'NG', 'to': 'GB', 'currencies': ['NGN→GBP'], 'providers': ['WISE', 'WORLDREMIT']},
            {'from': 'NG', 'to': 'EU', 'currencies': ['NGN→EUR'], 'providers': ['WISE', 'REMITLY']},
            {'from': 'US', 'to': 'NG', 'currencies': ['USD→NGN'], 'providers': ['WISE', 'WORLDREMIT', 'MONEYGRAM']},
            {'from': 'GB', 'to': 'NG', 'currencies': ['GBP→NGN'], 'providers': ['WISE', 'WORLDREMIT']},
            {'from': 'EU', 'to': 'NG', 'currencies': ['EUR→NGN'], 'providers': ['WISE', 'REMITLY']},
            {'from': 'NG', 'to': 'GH', 'currencies': ['NGN→GHS'], 'providers': ['FLUTTERWAVE']},
            {'from': 'NG', 'to': 'KE', 'currencies': ['NGN→KES'], 'providers': ['FLUTTERWAVE']},
        ]
        
        return corridors + common_corridors