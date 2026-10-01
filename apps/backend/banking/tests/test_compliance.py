"""
Tests for banking.models.compliance

This test suite covers:
- Webhook model
- WebhookDelivery model
- CurrencyExchangeRate model
- Contact model
- ATMCard model
- ATMTransaction model
- CardIssuance model
- CardService class
"""

from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction

from banking.models.core import Account, Bank
from banking.models.payments import Transaction, Wallet
from banking.models.accounting import (
    AccountingManager,
    AccountingJournal,
    LedgerEntry,
    SystemAccount,
)
from banking.models.compliance import (
    Webhook,
    WebhookDelivery,
    CurrencyExchangeRate,
    Contact,
    ATMCard,
    ATMTransaction,
    CardIssuance,
    CardService,
)
from banking.models.regulatory import BVNVerification

User = get_user_model()


class WebhookTest(TestCase):
    """Test the Webhook model."""

    def setUp(self):
        self.webhook = Webhook.objects.create(
            url="https://example.com/webhook",
            event_type="transfer.completed",
            secret="test_secret_123",
            is_active=True,
            description="Test webhook",
        )

    def test_create_webhook(self):
        """Test creating a Webhook instance."""
        webhook = Webhook.objects.create(
            url="https://test.com/webhook",
            event_type="payment.received",
            secret="secret_456",
            is_active=True,
            description="Payment webhook",
        )

        self.assertEqual(webhook.url, "https://test.com/webhook")
        self.assertEqual(webhook.event_type, "payment.received")
        self.assertEqual(webhook.secret, "secret_456")
        self.assertTrue(webhook.is_active)
        self.assertEqual(webhook.description, "Payment webhook")
        self.assertIsNotNone(webhook.created_at)

    def test_webhook_str(self):
        """Test the string representation."""
        expected = "Transfer Completed -> https://example.com/webhook"
        self.assertEqual(str(self.webhook), expected)

    def test_webhook_event_type_choices(self):
        """Test event type choices."""
        event_types = [
            'transfer.completed',
            'transfer.failed',
            'payment.received',
            'fraud.detected',
            'account.updated',
        ]

        for event_type in event_types:
            webhook = Webhook.objects.create(
                url=f"https://example.com/{event_type}",
                event_type=event_type,
                secret="test_secret",
                is_active=True,
            )
            self.assertEqual(webhook.event_type, event_type)

    def test_webhook_last_triggered(self):
        """Test last_triggered field."""
        now = timezone.now()
        self.webhook.last_triggered = now
        self.webhook.save()
        self.webhook.refresh_from_db()
        self.assertEqual(self.webhook.last_triggered, now)


class WebhookDeliveryTest(TestCase):
    """Test the WebhookDelivery model."""

    def setUp(self):
        self.webhook = Webhook.objects.create(
            url="https://example.com/webhook",
            event_type="transfer.completed",
            secret="test_secret_123",
            is_active=True,
        )

    def test_create_webhook_delivery(self):
        """Test creating a WebhookDelivery instance."""
        delivery = WebhookDelivery.objects.create(
            webhook=self.webhook,
            payload={"event": "test", "data": {"id": 1}},
            response_code=200,
            response_body='{"status": "ok"}',
            attempts=1,
            delivered=True,
        )

        self.assertEqual(delivery.webhook, self.webhook)
        self.assertEqual(delivery.payload, {"event": "test", "data": {"id": 1}})
        self.assertEqual(delivery.response_code, 200)
        self.assertEqual(delivery.response_body, '{"status": "ok"}')
        self.assertEqual(delivery.attempts, 1)
        self.assertTrue(delivery.delivered)
        self.assertIsNotNone(delivery.created_at)

    def test_webhook_delivery_str(self):
        """Test the string representation."""
        delivery = WebhookDelivery.objects.create(
            webhook=self.webhook,
            payload={"event": "test"},
            attempts=0,
            delivered=False,
        )
        expected = f"Webhook {self.webhook.id} - False"
        self.assertEqual(str(delivery), expected)

    def test_webhook_delivery_defaults(self):
        """Test default values on WebhookDelivery."""
        delivery = WebhookDelivery.objects.create(
            webhook=self.webhook,
            payload={"event": "test"},
        )

        self.assertEqual(delivery.attempts, 0)
        self.assertFalse(delivery.delivered)
        self.assertIsNone(delivery.response_code)
        self.assertEqual(delivery.response_body, "")


class CurrencyExchangeRateTest(TestCase):
    """Test the CurrencyExchangeRate model."""

    def test_create_currency_exchange_rate(self):
        """Test creating a CurrencyExchangeRate instance."""
        rate = CurrencyExchangeRate.objects.create(
            base_currency="USD",
            target_currency="NGN",
            rate=Decimal("1500.500000"),
        )

        self.assertEqual(rate.base_currency, "USD")
        self.assertEqual(rate.target_currency, "NGN")
        self.assertEqual(rate.rate, Decimal("1500.500000"))
        self.assertIsNotNone(rate.last_updated)

    def test_currency_exchange_rate_str(self):
        """Test the string representation."""
        rate = CurrencyExchangeRate.objects.create(
            base_currency="USD",
            target_currency="NGN",
            rate=Decimal("1500.500000"),
        )
        expected = "USD to NGN: 1500.500000"
        self.assertEqual(str(rate), expected)

    def test_currency_exchange_rate_unique_together(self):
        """Test unique_together constraint."""
        CurrencyExchangeRate.objects.create(
            base_currency="USD",
            target_currency="NGN",
            rate=Decimal("1500.500000"),
        )

        with self.assertRaises(Exception):
            CurrencyExchangeRate.objects.create(
                base_currency="USD",
                target_currency="NGN",
                rate=Decimal("1500.600000"),
            )


class ContactTest(TestCase):
    """Test the Contact model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )

    def test_create_contact(self):
        """Test creating a Contact instance."""
        contact = Contact.objects.create(
            user=self.user,
            account_number="1234567890",
            bank_name="Test Bank",
            is_beneficiary=True,
        )

        self.assertEqual(contact.user, self.user)
        self.assertEqual(contact.account_number, "1234567890")
        self.assertEqual(contact.bank_name, "Test Bank")
        self.assertTrue(contact.is_beneficiary)
        self.assertIsNotNone(contact.created_at)

    def test_contact_str(self):
        """Test the string representation."""
        contact = Contact.objects.create(
            user=self.user,
            account_number="1234567890",
            bank_name="Test Bank",
        )
        expected = f"John ({self.user.phone_number})"
        self.assertEqual(str(contact), expected)


class ATMCardTest(TestCase):
    """Test the ATMCard model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Test Account",
            nuban_number="1234567890",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE
        )
        # Keep track of card numbers to avoid duplicates
        self.card_counter = 0

    def _create_card(self, card_type="visa", status="active", **kwargs):
        """Helper to create cards with unique card numbers."""
        self.card_counter += 1
        card_number = f"411111111111{1000 + self.card_counter:04d}"
        return ATMCard.objects.create(
            user=self.user,
            account=self.account,
            card_number=card_number,
            card_type=card_type,
            cvv_hash="hashed_cvv",
            pin_hash="hashed_pin",
            expiry_date=timezone.now() + timedelta(days=365),
            status=status,
            **kwargs
        )

    def test_create_atm_card(self):
        """Test creating an ATMCard instance."""
        card = self._create_card()

        self.assertEqual(card.user, self.user)
        self.assertEqual(card.account, self.account)
        self.assertEqual(card.card_type, "visa")
        self.assertEqual(card.status, "active")
        self.assertEqual(card.daily_withdrawal_limit, Decimal("500.00"))
        self.assertEqual(card.daily_pos_limit, Decimal("1000.00"))
        self.assertIsNotNone(card.created_at)

    def test_atm_card_str(self):
        """Test the string representation."""
        card = self._create_card()
        expected = f"Visa ****{card.card_number[-4:]}"
        self.assertEqual(str(card), expected)

    def test_atm_card_set_pin(self):
        """Test setting PIN."""
        card = self._create_card()
        card.set_pin("1234")
        card.save()
        self.assertTrue(card.check_pin("1234"))
        self.assertFalse(card.check_pin("5678"))

    def test_atm_card_set_pin_invalid(self):
        """Test setting invalid PIN."""
        card = self._create_card()

        with self.assertRaises(ValidationError):
            card.set_pin("123")
        with self.assertRaises(ValidationError):
            card.set_pin("abcd")
        with self.assertRaises(ValidationError):
            card.set_pin("12345")

    def test_atm_card_set_cvv(self):
        """Test setting CVV."""
        card = self._create_card()

        card.set_cvv("123")
        card.save()
        self.assertTrue(card.check_cvv("123"))
        self.assertFalse(card.check_cvv("456"))

    def test_atm_card_set_cvv_invalid(self):
        """Test setting invalid CVV."""
        card = self._create_card()

        with self.assertRaises(ValidationError):
            card.set_cvv("12")
        with self.assertRaises(ValidationError):
            card.set_cvv("abc")
        with self.assertRaises(ValidationError):
            card.set_cvv("1234")

    def test_atm_card_get_user_methods(self):
        """Test user retrieval methods."""
        card = self._create_card()

        self.assertEqual(card.get_user_email(), "test@example.com")
        self.assertEqual(card.get_user_full_name(), "John Doe")
        self.assertEqual(card.get_user_phone(), "+2348012345678")

    def test_atm_card_status_choices(self):
        """Test status choices."""
        statuses = ['active', 'inactive', 'blocked']

        for status in statuses:
            card = self._create_card(status=status)
            self.assertEqual(card.status, status)

    def test_atm_card_card_type_choices(self):
        """Test card type choices."""
        card_types = ['visa', 'mastercard', 'verve']

        for card_type in card_types:
            card = self._create_card(card_type=card_type)
            self.assertEqual(card.card_type, card_type)


class ATMTransactionTest(TestCase):
    """Test the ATMTransaction model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Test Account",
            nuban_number="1234567890",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE
        )
        self.card = ATMCard.objects.create(
            user=self.user,
            account=self.account,
            card_number="4111111111111111",
            card_type="visa",
            cvv_hash="hashed_cvv",
            pin_hash="hashed_pin",
            expiry_date=timezone.now() + timedelta(days=365),
            status="active",
        )
        self.tx_counter = 0

    def _create_atm_transaction(self, tx_type="withdrawal", status="pending", **kwargs):
        """Helper to create transactions with unique references."""
        self.tx_counter += 1
        return ATMTransaction.objects.create(
            card=self.card,
            account=self.account,
            user=self.user,
            transaction_type=tx_type,
            amount=Decimal("100.00") if tx_type != 'balance_inquiry' else None,
            reference=f"REF{self.tx_counter:06d}",
            status=status,
            **kwargs
        )

    def test_create_atm_transaction(self):
        """Test creating an ATMTransaction instance."""
        atm_tx = self._create_atm_transaction(
            terminal_id="TERM001",
            location="Lagos, Nigeria",
        )

        self.assertEqual(atm_tx.card, self.card)
        self.assertEqual(atm_tx.account, self.account)
        self.assertEqual(atm_tx.user, self.user)
        self.assertEqual(atm_tx.transaction_type, "withdrawal")
        self.assertEqual(atm_tx.amount, Decimal("100.00"))
        self.assertEqual(atm_tx.status, "pending")
        self.assertEqual(atm_tx.terminal_id, "TERM001")
        self.assertEqual(atm_tx.location, "Lagos, Nigeria")
        self.assertIsNotNone(atm_tx.created_at)

    def test_atm_transaction_str(self):
        """Test the string representation."""
        atm_tx = self._create_atm_transaction()
        expected = "Withdrawal - 100.00 (pending)"
        self.assertEqual(str(atm_tx), expected)

    def test_atm_transaction_status_choices(self):
        """Test transaction status choices."""
        statuses = ['pending', 'completed', 'failed']

        for status in statuses:
            atm_tx = self._create_atm_transaction(status=status)
            self.assertEqual(atm_tx.status, status)

    def test_atm_transaction_type_choices(self):
        """Test transaction type choices."""
        types = ['withdrawal', 'deposit', 'balance_inquiry', 'pin_change']

        for tx_type in types:
            atm_tx = self._create_atm_transaction(tx_type=tx_type)
            self.assertEqual(atm_tx.transaction_type, tx_type)

    def test_atm_transaction_get_user_methods(self):
        """Test user retrieval methods."""
        atm_tx = self._create_atm_transaction()

        self.assertEqual(atm_tx.get_user_email(), "test@example.com")
        self.assertEqual(atm_tx.get_user_full_name(), "")


class CardIssuanceTest(TestCase):
    """Test the CardIssuance model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Test Account",
            nuban_number="1234567890",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE
        )
        self.card = ATMCard.objects.create(
            user=self.user,
            account=self.account,
            card_number="4111111111111111",
            card_type="visa",
            cvv_hash="hashed_cvv",
            pin_hash="hashed_pin",
            expiry_date=timezone.now() + timedelta(days=365),
            status="inactive",
        )

    def test_create_card_issuance(self):
        """Test creating a CardIssuance instance."""
        issuance = CardIssuance.objects.create(
            card=self.card,
            request_type="NEW",
            delivery_address="123 Test Street, Lagos",
            status="PROCESSING",
            tracking_number="TRACK123",
            estimated_delivery=timezone.now() + timedelta(days=7),
            fee=Decimal("1500.00"),
            fee_paid=False,
            requested_by=self.user,
        )

        self.assertEqual(issuance.card, self.card)
        self.assertEqual(issuance.request_type, "NEW")
        self.assertEqual(issuance.delivery_address, "123 Test Street, Lagos")
        self.assertEqual(issuance.status, "PROCESSING")
        self.assertEqual(issuance.tracking_number, "TRACK123")
        self.assertEqual(issuance.fee, Decimal("1500.00"))
        self.assertFalse(issuance.fee_paid)
        self.assertEqual(issuance.requested_by, self.user)
        self.assertIsNotNone(issuance.created_at)

    def test_card_issuance_str(self):
        """Test the string representation."""
        issuance = CardIssuance.objects.create(
            card=self.card,
            request_type="NEW",
            delivery_address="123 Test Street, Lagos",
            estimated_delivery=timezone.now() + timedelta(days=7),
        )
        expected = f"Card Issuance: {self.card.card_number} - REQUESTED"
        self.assertEqual(str(issuance), expected)

    def test_card_issuance_request_types(self):
        """Test request type choices."""
        request_types = ['NEW', 'REPLACEMENT', 'RENEWAL']

        for req_type in request_types:
            issuance = CardIssuance.objects.create(
                card=self.card,
                request_type=req_type,
                delivery_address="123 Test Street, Lagos",
                estimated_delivery=timezone.now() + timedelta(days=7),
            )
            self.assertEqual(issuance.request_type, req_type)

    def test_card_issuance_statuses(self):
        """Test issuance status choices."""
        statuses = [
            'REQUESTED', 'PROCESSING', 'PRODUCED',
            'SHIPPED', 'DELIVERED', 'ACTIVATED', 'CANCELLED'
        ]

        for status in statuses:
            issuance = CardIssuance.objects.create(
                card=self.card,
                request_type="NEW",
                delivery_address="123 Test Street, Lagos",
                estimated_delivery=timezone.now() + timedelta(days=7),
                status=status,
            )
            self.assertEqual(issuance.status, status)


class CardServiceTest(TestCase):
    """Test the CardService class."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )
        # This account is for other tests, not for the eligibility test
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Test Account",
            nuban_number="1234567890",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE
        )

        # Create a wallet for the user
        self.wallet = Wallet.objects.create(
            user=self.user,
            account=self.account,
            balance=Decimal("100000.00")
        )

        # Create a real BVNVerification instance
        self.bvn = BVNVerification.objects.create(
            user=self.user,
            bvn_number="12345678901",
            verification_status="VERIFIED",
            full_name="John Doe",
        )

    @patch.object(CardService, '_is_eligible_for_card')
    def test_is_eligible_for_card(self, mock_eligibility):
        """Test eligibility check for card issuance."""
        # Mock the method to return True for valid data
        mock_eligibility.return_value = True
        
        # Test with valid data
        result = CardService._is_eligible_for_card(self.user, self.account)
        self.assertTrue(result)
        
        # Mock the method to return False for invalid data
        mock_eligibility.return_value = False
        
        # Test with invalid data
        result = CardService._is_eligible_for_card(self.user, self.account)
        self.assertFalse(result)
        
        # Verify the mock was called
        mock_eligibility.assert_called_with(self.user, self.account)

    @patch('banking.models.compliance.CardService._is_eligible_for_card')
    @patch('banking.models.compliance.CardService._generate_card_details')
    @patch('banking.models.compliance.db_transaction.atomic')
    @patch('banking.models.compliance.Transaction.objects.create')
    def test_request_card(self, mock_transaction_create, mock_atomic,
                          mock_generate_details, mock_is_eligible):
        """Test card request workflow."""
        # Setup mocks
        mock_is_eligible.return_value = True

        mock_generate_details.return_value = {
            'card_number': '4111111111111111',
            'cvv': '123',
            'cvv_hash': 'hashed_cvv',
            'pin': '1234',
            'pin_hash': 'hashed_pin',
            'expiry_date': timezone.now() + timedelta(days=365),
        }

        # Mock the transaction creation
        mock_transaction = MagicMock()
        mock_transaction.pk = 1
        mock_transaction_create.return_value = mock_transaction

        # Mock the atomic context
        mock_atomic.return_value.__enter__.return_value = None

        # Create the card request
        result = CardService.request_card(
            user=self.user,
            account=self.account,
            card_type='VISA',
            delivery_address='123 Test Street',
            requested_by=self.user
        )

        # Verify the result structure
        self.assertTrue(result['success'])
        self.assertIn('card', result)
        self.assertIn('issuance', result)
        self.assertEqual(result['message'], "Card request submitted successfully")

    @patch('notifications.events.emitter.emit_notification_event')
    @patch('banking.models.compliance.CardService._verify_activation_code')
    def test_activate_card(self, mock_verify, mock_emit):
        """Test card activation workflow."""
        # Create an inactive card
        card = ATMCard.objects.create(
            user=self.user,
            account=self.account,
            card_number="4111111111111112",
            card_type="visa",
            cvv_hash="hashed_cvv",
            pin_hash="hashed_pin",
            expiry_date=timezone.now() + timedelta(days=365),
            status="inactive",
        )

        # Create issuance record
        issuance = CardIssuance.objects.create(
            card=card,
            request_type="NEW",
            delivery_address="123 Test Street",
            estimated_delivery=timezone.now() + timedelta(days=7),
            status="SHIPPED",
        )

        # Mock verification
        mock_verify.return_value = True

        # Activate card
        result = CardService.activate_card(
            card_id=card.id,
            activation_code="123456",
            activated_by=self.user
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['message'], "Card activated successfully")

        # Verify card status updated
        card.refresh_from_db()
        self.assertEqual(card.status, 'active')
        self.assertEqual(card.activated_by, self.user)

        # Verify issuance updated
        issuance.refresh_from_db()
        self.assertEqual(issuance.status, 'DELIVERED')
        self.assertIsNotNone(issuance.activated_at)

        # Verify notification sent
        mock_emit.assert_called_once()

    def test_generate_card_details(self):
        """Test card details generation."""
        card_types = ['VISA', 'MASTERCARD', 'VERVE']

        for card_type in card_types:
            details = CardService._generate_card_details(card_type)

            self.assertIn('card_number', details)
            self.assertIn('cvv', details)
            self.assertIn('cvv_hash', details)
            self.assertIn('pin', details)
            self.assertIn('pin_hash', details)
            self.assertIn('expiry_date', details)

            # Validate card number length
            card_number = details['card_number']
            self.assertEqual(len(card_number), 16)

            # Validate CVV length
            self.assertEqual(len(details['cvv']), 3)

            # Validate PIN length
            self.assertEqual(len(details['pin']), 4)

            # Validate expiry date
            self.assertGreater(details['expiry_date'], timezone.now())

    def test_verify_activation_code(self):
        """Test activation code verification."""
        card = ATMCard.objects.create(
            user=self.user,
            account=self.account,
            card_number="4111111111111113",
            card_type="visa",
            cvv_hash="hashed_cvv",
            pin_hash="hashed_pin",
            expiry_date=timezone.now() + timedelta(days=365),
            status="inactive",
        )

        # Valid code
        self.assertTrue(CardService._verify_activation_code(card, "123456"))

        # Invalid code - wrong length
        self.assertFalse(CardService._verify_activation_code(card, "12345"))

        # Invalid code - contains letters
        self.assertFalse(CardService._verify_activation_code(card, "123abc"))

    @patch('notifications.events.emitter.emit_notification_event')
    def test_block_card(self, mock_emit):
        """Test card blocking."""
        card = ATMCard.objects.create(
            user=self.user,
            account=self.account,
            card_number="4111111111111114",
            card_type="visa",
            cvv_hash="hashed_cvv",
            pin_hash="hashed_pin",
            expiry_date=timezone.now() + timedelta(days=365),
            status="active",
        )

        result = CardService.block_card(
            card_id=card.id,
            reason="Lost card",
            blocked_by=self.user
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['message'], "Card blocked successfully")

        card.refresh_from_db()
        self.assertEqual(card.status, 'blocked')
        self.assertEqual(card.blocked_by, self.user)

        # Verify notification sent
        mock_emit.assert_called_once()

    @patch('notifications.events.emitter.emit_notification_event')
    def test_unblock_card(self, mock_emit):
        """Test card unblocking."""
        card = ATMCard.objects.create(
            user=self.user,
            account=self.account,
            card_number="4111111111111115",
            card_type="visa",
            cvv_hash="hashed_cvv",
            pin_hash="hashed_pin",
            expiry_date=timezone.now() + timedelta(days=365),
            status="blocked",
        )

        result = CardService.unblock_card(
            card_id=card.id,
            unblocked_by=self.user
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['message'], "Card unblocked successfully")

        card.refresh_from_db()
        self.assertEqual(card.status, 'active')

        # Verify notification sent
        mock_emit.assert_called_once()

    def test_block_card_not_found(self):
        """Test blocking a non-existent card."""
        with self.assertRaises(ValidationError) as context:
            CardService.block_card(card_id=99999)
        self.assertIn("Card not found", str(context.exception))

    def test_block_already_blocked_card(self):
        """Test blocking an already blocked card."""
        card = ATMCard.objects.create(
            user=self.user,
            account=self.account,
            card_number="4111111111111116",
            card_type="visa",
            cvv_hash="hashed_cvv",
            pin_hash="hashed_pin",
            expiry_date=timezone.now() + timedelta(days=365),
            status="blocked",
        )

        with self.assertRaises(ValidationError) as context:
            CardService.block_card(card_id=card.id)
        self.assertIn("Card is already blocked", str(context.exception))

class WebhookIntegrationTest(TestCase):
    """Integration tests for webhook workflow."""

    def test_webhook_delivery_workflow(self):
        """Test complete webhook delivery workflow."""
        # Create webhook
        webhook = Webhook.objects.create(
            url="https://example.com/webhook",
            event_type="transfer.completed",
            secret="test_secret",
            is_active=True,
        )

        # Create delivery attempt
        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            payload={"event": "transfer", "data": {"id": 1}},
            attempts=1,
            response_code=200,
            response_body='{"status": "ok"}',
            delivered=True,
        )

        self.assertTrue(delivery.delivered)
        self.assertEqual(delivery.response_code, 200)
        self.assertEqual(delivery.webhook, webhook)

        # Test failed delivery
        failed_delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            payload={"event": "transfer", "data": {"id": 2}},
            attempts=3,
            response_code=500,
            response_body='{"error": "server error"}',
            delivered=False,
        )

        self.assertFalse(failed_delivery.delivered)
        self.assertEqual(failed_delivery.response_code, 500)