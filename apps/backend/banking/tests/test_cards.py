"""
Tests for banking.models.cards

This test suite covers:
- CardBrand model
- VirtualCard model
- CardTransaction model
- PhysicalCard model
"""

from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings

from banking.models.core import Account, Bank
from banking.models.payments import Wallet, Transaction
from banking.models.cards import (
    CardBrand,
    VirtualCard,
    CardTransaction,
    PhysicalCard,
)

User = get_user_model()


class CardBrandTest(TestCase):
    """Test the CardBrand model."""

    def setUp(self):
        self.card_brand = CardBrand.objects.create(
            name="Visa",
            code="VI",
            is_active=True
        )

    def test_create_card_brand(self):
        """Test creating a CardBrand instance."""
        brand = CardBrand.objects.create(
            name="Mastercard",
            code="MC",
            is_active=True
        )

        self.assertEqual(brand.name, "Mastercard")
        self.assertEqual(brand.code, "MC")
        self.assertTrue(brand.is_active)

    def test_card_brand_str(self):
        """Test the string representation."""
        self.assertEqual(str(self.card_brand), "Visa")

    def test_card_brand_unique_name(self):
        """Test that name must be unique."""
        with self.assertRaises(Exception):
            CardBrand.objects.create(
                name="Visa",
                code="VS",
                is_active=True
            )

    def test_card_brand_unique_code(self):
        """Test that code must be unique."""
        with self.assertRaises(Exception):
            CardBrand.objects.create(
                name="Verve",
                code="VI",
                is_active=True
            )


class VirtualCardTest(TestCase):
    """Test the VirtualCard model."""

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
        self.wallet = Wallet.objects.create(
            user=self.user,
            account=self.account,
            balance=Decimal("100000.00")
        )
        self.card_brand = CardBrand.objects.create(
            name="Visa",
            code="VI",
            is_active=True
        )

        # Mock settings.CARD_ENCRYPTION_KEY
        self.settings_patch = patch('django.conf.settings.CARD_ENCRYPTION_KEY', 'test_key')
        self.settings_patch.start()

        # Mock encryption for testing
        self.encryption_patch = patch('banking.models.cards.Fernet')
        self.mock_fernet = self.encryption_patch.start()
        self.mock_cipher = MagicMock()
        self.mock_fernet.return_value = self.mock_cipher
        self.mock_cipher.encrypt.return_value = b'encrypted_value'
        self.mock_cipher.decrypt.return_value = b'decrypted_value'

    def tearDown(self):
        self.settings_patch.stop()
        self.encryption_patch.stop()

    def test_create_virtual_card(self):
        """Test creating a VirtualCard instance."""
        expires_at = timezone.now() + timedelta(days=365)
        card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=expires_at,
        )

        self.assertEqual(card.user, self.user)
        self.assertEqual(card.wallet, self.wallet)
        self.assertEqual(card.card_brand, self.card_brand)
        self.assertEqual(card.card_holder_name, "Test User")
        self.assertEqual(card.expiry_month, 12)
        self.assertEqual(card.expiry_year, 2026)
        self.assertEqual(card.card_type, "VISA")
        self.assertEqual(card.last_four, "1111")
        self.assertEqual(card.bin, "411111")
        self.assertEqual(card.status, "ACTIVE")
        self.assertTrue(card.is_active)
        self.assertFalse(card.is_frozen)
        self.assertFalse(card.is_lost)
        self.assertFalse(card.is_stolen)

    def test_virtual_card_str(self):
        """Test the string representation."""
        expires_at = timezone.now() + timedelta(days=365)
        card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=expires_at,
        )
        expected = f"VISA ****1111 ({self.user.email})"
        self.assertEqual(str(card), expected)

    def test_virtual_card_is_expired(self):
        """Test the is_expired method."""
        # Card not expired
        expires_at = timezone.now() + timedelta(days=365)
        card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=expires_at,
        )
        self.assertFalse(card.is_expired())

        # Card expired
        expires_at = timezone.now() - timedelta(days=1)
        card.expires_at = expires_at
        card.save()
        self.assertTrue(card.is_expired())

    def test_virtual_card_get_card_number(self):
        """Test get_card_number method."""
        expires_at = timezone.now() + timedelta(days=365)
        card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=expires_at,
        )
        self.mock_cipher.decrypt.return_value = b'4111111111111111'
        self.assertEqual(card.get_card_number(), '4111111111111111')

    def test_virtual_card_get_cvv(self):
        """Test get_cvv method."""
        expires_at = timezone.now() + timedelta(days=365)
        card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=expires_at,
        )
        self.mock_cipher.decrypt.return_value = b'123'
        self.assertEqual(card.get_cvv(), '123')

    def test_virtual_card_encrypt_field(self):
        """Test the _encrypt_field method."""
        expires_at = timezone.now() + timedelta(days=365)
        card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=expires_at,
        )
        self.mock_cipher.encrypt.return_value = b'encrypted_value'
        result = card._encrypt_field("test_value")
        self.assertEqual(result, 'encrypted_value')

    def test_virtual_card_decrypt_field(self):
        """Test the _decrypt_field method."""
        expires_at = timezone.now() + timedelta(days=365)
        card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=expires_at,
        )
        self.mock_cipher.decrypt.return_value = b'decrypted_value'
        result = card._decrypt_field("encrypted_value")
        self.assertEqual(result, 'decrypted_value')

    def test_virtual_card_default_limits(self):
        """Test default limits on VirtualCard."""
        expires_at = timezone.now() + timedelta(days=365)
        card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=expires_at,
        )

        self.assertEqual(card.daily_limit, Decimal("100000.00"))
        self.assertEqual(card.monthly_limit, Decimal("1000000.00"))
        self.assertEqual(card.per_transaction_limit, Decimal("50000.00"))
        self.assertEqual(card.daily_usage, Decimal("0.00"))
        self.assertEqual(card.monthly_usage, Decimal("0.00"))
        self.assertEqual(card.total_usage, Decimal("0.00"))

    def test_virtual_card_status_choices(self):
        """Test card status choices."""
        expires_at = timezone.now() + timedelta(days=365)
        statuses = ['PENDING', 'ACTIVE', 'BLOCKED', 'FROZEN', 'EXPIRED', 'CLOSED']

        for status in statuses:
            card = VirtualCard.objects.create(
                user=self.user,
                wallet=self.wallet,
                card_brand=self.card_brand,
                card_number="encrypted",
                card_holder_name="Test User",
                expiry_month=12,
                expiry_year=2026,
                cvv="encrypted",
                card_type="VISA",
                last_four="1111",
                bin="411111",
                status=status,
                expires_at=expires_at,
            )
            self.assertEqual(card.status, status)

    def test_virtual_card_card_types(self):
        """Test card type choices."""
        expires_at = timezone.now() + timedelta(days=365)
        card_types = ['VISA', 'MASTERCARD', 'VERVE']

        for card_type in card_types:
            card = VirtualCard.objects.create(
                user=self.user,
                wallet=self.wallet,
                card_brand=self.card_brand,
                card_number="encrypted",
                card_holder_name="Test User",
                expiry_month=12,
                expiry_year=2026,
                cvv="encrypted",
                card_type=card_type,
                last_four="1111",
                bin="411111",
                status="ACTIVE",
                expires_at=expires_at,
            )
            self.assertEqual(card.card_type, card_type)


class CardTransactionTest(TestCase):
    """Test the CardTransaction model."""

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
        self.wallet = Wallet.objects.create(
            user=self.user,
            account=self.account,
            balance=Decimal("100000.00")
        )
        self.card_brand = CardBrand.objects.create(
            name="Visa",
            code="VI",
            is_active=True
        )
        self.expires_at = timezone.now() + timedelta(days=365)
        self.virtual_card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=self.expires_at,
        )
        self.transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            status="PENDING"
        )

    def test_create_card_transaction(self):
        """Test creating a CardTransaction instance."""
        card_tx = CardTransaction.objects.create(
            card=self.virtual_card,
            transaction=self.transaction,
            user=self.user,
            transaction_type="PURCHASE",
            amount=Decimal("50.00"),
            currency="NGN",
            merchant_name="Test Merchant",
            merchant_category_code="1234",
            merchant_country="NG",
            auth_code="AUTH123",
            auth_amount=Decimal("50.00"),
            status="AUTHORIZED",
            acquirer_id="ACQ001",
            acquirer_reference="REF123",
        )

        self.assertEqual(card_tx.card, self.virtual_card)
        self.assertEqual(card_tx.transaction, self.transaction)
        self.assertEqual(card_tx.user, self.user)
        self.assertEqual(card_tx.transaction_type, "PURCHASE")
        self.assertEqual(card_tx.amount, Decimal("50.00"))
        self.assertEqual(card_tx.currency, "NGN")
        self.assertEqual(card_tx.merchant_name, "Test Merchant")
        self.assertEqual(card_tx.merchant_category_code, "1234")
        self.assertEqual(card_tx.merchant_country, "NG")
        self.assertEqual(card_tx.auth_code, "AUTH123")
        self.assertEqual(card_tx.auth_amount, Decimal("50.00"))
        self.assertEqual(card_tx.status, "AUTHORIZED")
        self.assertEqual(card_tx.acquirer_id, "ACQ001")
        self.assertEqual(card_tx.acquirer_reference, "REF123")

    def test_card_transaction_str(self):
        """Test the string representation."""
        card_tx = CardTransaction.objects.create(
            card=self.virtual_card,
            transaction=self.transaction,
            user=self.user,
            transaction_type="PURCHASE",
            amount=Decimal("50.00"),
            currency="NGN",
            merchant_name="Test Merchant",
            merchant_category_code="1234",
            merchant_country="NG",
            status="PENDING",
            acquirer_id="ACQ001",
        )
        expected = f"PURCHASE - 50.00 NGN - Test Merchant"
        self.assertEqual(str(card_tx), expected)

    def test_card_transaction_status_choices(self):
        """Test transaction status choices."""
        statuses = ['PENDING', 'AUTHORIZED', 'SETTLED', 'DECLINED', 'REVERSED', 'CHARGEBACK']

        for status in statuses:
            card_tx = CardTransaction.objects.create(
                card=self.virtual_card,
                transaction=self.transaction,
                user=self.user,
                transaction_type="PURCHASE",
                amount=Decimal("50.00"),
                currency="NGN",
                merchant_name="Test Merchant",
                merchant_category_code="1234",
                merchant_country="NG",
                status=status,
                acquirer_id="ACQ001",
            )
            self.assertEqual(card_tx.status, status)

    def test_card_transaction_types(self):
        """Test transaction type choices."""
        types = ['PURCHASE', 'REFUND', 'AUTHORIZATION', 'REVERSAL']

        for tx_type in types:
            card_tx = CardTransaction.objects.create(
                card=self.virtual_card,
                transaction=self.transaction,
                user=self.user,
                transaction_type=tx_type,
                amount=Decimal("50.00"),
                currency="NGN",
                merchant_name="Test Merchant",
                merchant_category_code="1234",
                merchant_country="NG",
                status="PENDING",
                acquirer_id="ACQ001",
            )
            self.assertEqual(card_tx.transaction_type, tx_type)


class PhysicalCardTest(TestCase):
    """Test the PhysicalCard model."""

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
        self.wallet = Wallet.objects.create(
            user=self.user,
            account=self.account,
            balance=Decimal("100000.00")
        )
        self.card_brand = CardBrand.objects.create(
            name="Visa",
            code="VI",
            is_active=True
        )
        self.expires_at = timezone.now() + timedelta(days=365)
        self.virtual_card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=self.expires_at,
        )

    def test_create_physical_card(self):
        """Test creating a PhysicalCard instance."""
        physical_card = PhysicalCard.objects.create(
            user=self.user,
            virtual_card=self.virtual_card,
            delivery_address="123 Test Street, Lagos",
            delivery_city="Lagos",
            delivery_state="Lagos",
            delivery_country="NG",
            delivery_phone="+2348012345678",
            shipping_method="Express",
            tracking_number="TRACK123",
            delivery_status="PENDING",
            card_fee=Decimal("1000.00"),
            shipping_fee=Decimal("500.00"),
            total_fee=Decimal("1500.00"),
        )

        self.assertEqual(physical_card.user, self.user)
        self.assertEqual(physical_card.virtual_card, self.virtual_card)
        self.assertEqual(physical_card.delivery_address, "123 Test Street, Lagos")
        self.assertEqual(physical_card.delivery_city, "Lagos")
        self.assertEqual(physical_card.delivery_state, "Lagos")
        self.assertEqual(physical_card.delivery_country, "NG")
        self.assertEqual(physical_card.delivery_phone, "+2348012345678")
        self.assertEqual(physical_card.shipping_method, "Express")
        self.assertEqual(physical_card.tracking_number, "TRACK123")
        self.assertEqual(physical_card.delivery_status, "PENDING")
        self.assertEqual(physical_card.card_fee, Decimal("1000.00"))
        self.assertEqual(physical_card.shipping_fee, Decimal("500.00"))
        self.assertEqual(physical_card.total_fee, Decimal("1500.00"))

    def test_physical_card_str(self):
        """Test the string representation."""
        physical_card = PhysicalCard.objects.create(
            user=self.user,
            virtual_card=self.virtual_card,
            delivery_address="123 Test Street, Lagos",
            delivery_city="Lagos",
            delivery_state="Lagos",
            delivery_country="NG",
            delivery_phone="+2348012345678",
            shipping_method="Express",
            delivery_status="PENDING",
            card_fee=Decimal("1000.00"),
            shipping_fee=Decimal("500.00"),
            total_fee=Decimal("1500.00"),
        )
        expected = f"Physical Card for {self.user.email} - PENDING"
        self.assertEqual(str(physical_card), expected)

    def test_physical_card_delivery_status_choices(self):
        """Test delivery status choices."""
        statuses = ['PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED']

        for status in statuses:
            physical_card = PhysicalCard.objects.create(
                user=self.user,
                virtual_card=self.virtual_card,
                delivery_address="123 Test Street, Lagos",
                delivery_city="Lagos",
                delivery_state="Lagos",
                delivery_country="NG",
                delivery_phone="+2348012345678",
                shipping_method="Express",
                delivery_status=status,
                card_fee=Decimal("1000.00"),
                shipping_fee=Decimal("500.00"),
                total_fee=Decimal("1500.00"),
            )
            self.assertEqual(physical_card.delivery_status, status)

    def test_physical_card_default_country(self):
        """Test default country is NG."""
        physical_card = PhysicalCard.objects.create(
            user=self.user,
            virtual_card=self.virtual_card,
            delivery_address="123 Test Street, Lagos",
            delivery_city="Lagos",
            delivery_state="Lagos",
            delivery_phone="+2348012345678",
            shipping_method="Express",
            delivery_status="PENDING",
            card_fee=Decimal("1000.00"),
            shipping_fee=Decimal("500.00"),
            total_fee=Decimal("1500.00"),
        )
        self.assertEqual(physical_card.delivery_country, "NG")


class IntegrationCardTest(TestCase):
    """Integration tests for card-related workflows."""

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
        self.wallet = Wallet.objects.create(
            user=self.user,
            account=self.account,
            balance=Decimal("100000.00")
        )
        self.card_brand = CardBrand.objects.create(
            name="Visa",
            code="VI",
            is_active=True
        )

        # Mock settings first, then encryption
        self.settings_patch = patch('django.conf.settings.CARD_ENCRYPTION_KEY', 'test_key')
        self.settings_patch.start()

        # Mock encryption for testing
        self.encryption_patch = patch('banking.models.cards.Fernet')
        self.mock_fernet = self.encryption_patch.start()
        self.mock_cipher = MagicMock()
        self.mock_fernet.return_value = self.mock_cipher
        self.mock_cipher.encrypt.return_value = b'encrypted_value'
        self.mock_cipher.decrypt.return_value = b'decrypted_value'

        self.expires_at = timezone.now() + timedelta(days=365)
        self.virtual_card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=self.card_brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="VISA",
            last_four="1111",
            bin="411111",
            status="ACTIVE",
            expires_at=self.expires_at,
        )

    def tearDown(self):
        self.settings_patch.stop()
        self.encryption_patch.stop()

    def test_card_issuance_workflow(self):
        """Test complete card issuance workflow."""
        # 1. Create card brand
        brand = CardBrand.objects.create(
            name="Mastercard",
            code="MC",
            is_active=True
        )

        # 2. Issue virtual card
        card = VirtualCard.objects.create(
            user=self.user,
            wallet=self.wallet,
            card_brand=brand,
            card_number="encrypted",
            card_holder_name="Test User",
            expiry_month=12,
            expiry_year=2026,
            cvv="encrypted",
            card_type="MASTERCARD",
            last_four="2222",
            bin="511111",
            status="ACTIVE",
            expires_at=timezone.now() + timedelta(days=365),
        )

        self.assertEqual(card.status, "ACTIVE")
        self.assertTrue(card.is_active)

        # 3. Create transaction
        transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("50.00"),
            status="COMPLETED"
        )

        # 4. Make card transaction
        card_tx = CardTransaction.objects.create(
            card=card,
            transaction=transaction,
            user=self.user,
            transaction_type="PURCHASE",
            amount=Decimal("50.00"),
            currency="NGN",
            merchant_name="Online Store",
            merchant_category_code="1234",
            merchant_country="NG",
            status="AUTHORIZED",
            acquirer_id="ACQ001",
        )

        self.assertEqual(card_tx.card, card)
        self.assertEqual(card_tx.transaction_type, "PURCHASE")
        self.assertEqual(card_tx.status, "AUTHORIZED")

        # 5. Request physical card
        physical_card = PhysicalCard.objects.create(
            user=self.user,
            virtual_card=card,
            delivery_address="123 Test Street, Lagos",
            delivery_city="Lagos",
            delivery_state="Lagos",
            delivery_country="NG",
            delivery_phone="+2348012345678",
            shipping_method="Standard",
            delivery_status="PENDING",
            card_fee=Decimal("1000.00"),
            shipping_fee=Decimal("0.00"),
            total_fee=Decimal("1000.00"),
        )

        self.assertEqual(physical_card.virtual_card, card)
        self.assertEqual(physical_card.delivery_status, "PENDING")