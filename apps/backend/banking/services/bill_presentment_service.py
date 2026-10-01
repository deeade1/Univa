   
class BillPresentmentService:
    """Automated bill fetching, reminders, and payments"""
    
    def __init__(self):
        self.session = requests.Session()
    
    def fetch_customer_bills(self, bill_account) -> List[Dict]:
        """Fetch bills from provider for a customer account"""
        
        provider = bill_account.provider
        
        if not provider.api_endpoint:
            raise ValueError(f"Provider {provider.name} has no API endpoint configured")
        
        # Different providers have different APIs
        if provider.provider_type == 'ELECTRICITY':
            return self._fetch_electricity_bills(provider, bill_account)
        elif provider.provider_type == 'WATER':
            return self._fetch_water_bills(provider, bill_account)
        elif provider.provider_type == 'INTERNET':
            return self._fetch_internet_bills(provider, bill_account)
        else:
            raise ValueError(f"Unsupported provider type: {provider.provider_type}")
    
    def _fetch_electricity_bills(self, provider, bill_account) -> List[Dict]:
        """Fetch electricity bills (DISCOs)"""
        
        url = f"{provider.api_endpoint}/bill-inquiry"
        
        payload = {
            "meter_number": bill_account.account_number,
            "customer_reference": bill_account.validation_reference,
            "service_type": "electricity",
            "amount": "",  # For validation
            "request_id": f"BILL-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        headers = {
            'Authorization': f'Bearer {provider.api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'success':
                bills_data = data.get('data', {}).get('bills', [])
                
                processed_bills = []
                for bill_data in bills_data:
                    processed_bills.append({
                        'provider_reference': bill_data.get('bill_id'),
                        'total_amount': Decimal(bill_data.get('amount', 0)),
                        'outstanding_amount': Decimal(bill_data.get('outstanding', 0)),
                        'billing_period': bill_data.get('period'),
                        'due_date': datetime.strptime(bill_data.get('due_date'), '%Y-%m-%d').date(),
                        'breakdown': {
                            'energy_charge': Decimal(bill_data.get('energy_charge', 0)),
                            'fixed_charge': Decimal(bill_data.get('fixed_charge', 0)),
                            'meter_charge': Decimal(bill_data.get('meter_charge', 0)),
                            'tax': Decimal(bill_data.get('tax', 0)),
                            'arrears': Decimal(bill_data.get('arrears', 0)),
                        }
                    })
                
                return processed_bills
            else:
                raise ValueError(data.get('message', 'Bill fetch failed'))
                
        except Exception as e:
            logger.error(f"Electricity bill fetch failed: {str(e)}")
            raise
    
    def _fetch_internet_bills(self, provider, bill_account) -> List[Dict]:
        """Fetch internet service provider bills"""
        # Similar implementation for ISPs
        pass
    
    def sync_user_bills(self, user) -> Dict:
        """Sync all bills for a user"""
        from ..models.bills import BillAccount, Bill
        
        results = {
            'total_accounts': 0,
            'bills_fetched': 0,
            'bills_created': 0,
            'bills_updated': 0,
            'errors': []
        }
        
        bill_accounts = BillAccount.objects.filter(
            user=user,
            provider__is_active=True
        )
        
        results['total_accounts'] = bill_accounts.count()
        
        for bill_account in bill_accounts:
            try:
                # Fetch bills from provider
                bills_data = self.fetch_customer_bills(bill_account)
                
                for bill_data in bills_data:
                    # Check if bill already exists
                    bill, created = Bill.objects.update_or_create(
                        bill_account=bill_account,
                        provider_reference=bill_data['provider_reference'],
                        defaults={
                            'total_amount': bill_data['total_amount'],
                            'outstanding_amount': bill_data['outstanding_amount'],
                            'billing_period_start': bill_data['billing_period']['start'],
                            'billing_period_end': bill_data['billing_period']['end'],
                            'due_date': bill_data['due_date'],
                            'breakdown': bill_data['breakdown'],
                            'status': 'PENDING' if bill_data['outstanding_amount'] > 0 else 'PAID'
                        }
                    )
                    
                    if created:
                        results['bills_created'] += 1
                    else:
                        results['bills_updated'] += 1
                    
                    results['bills_fetched'] += 1
                    
            except Exception as e:
                results['errors'].append({
                    'account': bill_account.account_number,
                    'error': str(e)
                })
                logger.error(f"Bill sync failed for {bill_account}: {str(e)}")
        
        return results
    
    def send_bill_reminders(self):
        """Send bill payment reminders"""
        from ..models.bills import Bill
        from ..services.notification_service import NotificationService
        
        notification_service = NotificationService()
        today = timezone.now().date()
        
        # Bills due in 3 days
        reminder_date = today + timedelta(days=3)
        
        bills_due = Bill.objects.filter(
            due_date=reminder_date,
            status='PENDING',
            reminder_sent=False
        ).select_related('bill_account__user')
        
        for bill in bills_due:
            try:
                user = bill.bill_account.user
                
                # Send notification
                notification_service._create_notification(
                    user=user,
                    title=f"Bill Reminder: {bill.bill_account.provider.name}",
                    message=f"Your {bill.bill_account.provider.name} bill of ₦{bill.total_amount:,.2f} is due on {bill.due_date.strftime('%b %d, %Y')}",
                    notification_type='bill_reminder'
                )
                
                # Send SMS
                self._send_sms_reminder(user, bill)
                
                # Send email
                self._send_email_reminder(user, bill)
                
                # Update reminder status
                bill.reminder_sent = True
                bill.last_reminder_sent = timezone.now()
                bill.save()
                
                logger.info(f"Reminder sent for bill {bill.bill_reference}")
                
            except Exception as e:
                logger.error(f"Reminder sending failed for bill {bill.bill_reference}: {str(e)}")
        
        return bills_due.count()
    
    def process_auto_payments(self):
        """Process automatic bill payments"""
        from ..models.bills import Bill, BillAccount
        
        today = timezone.now().date()
        
        # Find bills eligible for auto-pay
        auto_pay_bills = Bill.objects.filter(
            due_date=today,
            status='PENDING',
            bill_account__auto_pay_enabled=True,
            bill_account__auto_pay_source_account__isnull=False
        ).select_related('bill_account__user', 'bill_account__auto_pay_source_account')
        
        successful_payments = 0
        failed_payments = []
        
        for bill in auto_pay_bills:
            try:
                with db_transaction.atomic():
                    user = bill.bill_account.user
                    source_account = bill.bill_account.auto_pay_source_account
                    
                    # Check if threshold is met
                    if bill.total_amount < bill.bill_account.auto_pay_threshold:
                        logger.info(f"Auto-pay skipped for {bill.bill_reference}: below threshold")
                        continue
                    
                    # Check account balance
                    if source_account.balance.available_balance < bill.total_amount:
                        logger.warning(f"Insufficient balance for auto-pay: {bill.bill_reference}")
                        failed_payments.append({
                            'bill': bill.bill_reference,
                            'reason': 'Insufficient balance'
                        })
                        continue
                    
                    # Process payment
                    from ..services.payment_service import PaymentService
                    payment_service = PaymentService()
                    
                    payment_service.transfer_funds_external(
                        sender=user,
                        sender_account=source_account,
                        recipient_account_number=bill.bill_account.account_number,
                        recipient_bank_code=bill.bill_account.provider.provider_code,
                        recipient_name=bill.bill_account.provider.name,
                        amount=bill.total_amount,
                        narration=f"Auto-pay: {bill.bill_account.provider.name} bill"
                    )
                    
                    # Update bill status
                    bill.status = 'PAID'
                    bill.amount_paid = bill.total_amount
                    bill.outstanding_amount = Decimal('0.00')
                    bill.paid_at = timezone.now()
                    bill.is_auto_paid = True
                    bill.save()
                    
                    successful_payments += 1
                    
                    # Send notification
                    from ..services.notification_service import NotificationService
                    notification_service = NotificationService()
                    notification_service._create_notification(
                        user=user,
                        title=f"Auto-payment Successful",
                        message=f"Your {bill.bill_account.provider.name} bill of ₦{bill.total_amount:,.2f} was paid automatically",
                        notification_type='auto_payment'
                    )
                    
                    logger.info(f"Auto-payment successful for {bill.bill_reference}")
                    
            except Exception as e:
                failed_payments.append({
                    'bill': bill.bill_reference,
                    'reason': str(e)
                })
                logger.error(f"Auto-payment failed for {bill.bill_reference}: {str(e)}")
        
        return {
            'successful': successful_payments,
            'failed': len(failed_payments),
            'failures': failed_payments
        }
    
    def _send_sms_reminder(self, user, bill):
        """Send SMS reminder"""
        # Integrate with SMS provider (Twilio, Termii, etc.)
        pass
    
    def _send_email_reminder(self, user, bill):
        """Send email reminder"""
        # Integrate with email service
        pass
    
