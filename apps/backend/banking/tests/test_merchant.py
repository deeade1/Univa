from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from banking.models.core import Account, Bank
from banking.models.merchant import Merchant, MerchantTransaction
from banking.models.payments import Transaction


User = get_user_model()


class MerchantModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant@example.com",
            password="TestPassword123!",
            phone_number="08030000001",
        )

        self.verified_by = User.objects.create_user(
            email="admin@example.com",
            password="TestPassword123!",
            phone_number="08030000002",
        )

        self.bank = Bank.objects.create(
            name="Test Bank",
            code="999",
        )

        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            phone_number=self.user.phone_number,
            account_name="Test Merchant",
            status="ACTIVE",
        )
    
    def create_merchant(self, **overrides):
        defaults = {
            "user": self.user,
            "business_name": "Test Merchant Ltd",
            "business_type": "SMALL_BUSINESS",
            "business_registration_number": "RC123456",
            "tax_id": "TIN123456",
            "business_email": "business@example.com",
            "business_phone": "08012345678",
            "business_address": "123 Test Street",
            "business_state": "Lagos",
            "business_city": "Lagos",
            "settlement_account": self.account,
            "settlement_bank": self.bank,
        }
        defaults.update(overrides)

        return Merchant.objects.create(**defaults)

    def test_create_merchant(self):
        merchant = self.create_merchant()

        self.assertIsNotNone(merchant.pk)
        self.assertEqual(merchant.user, self.user)
        self.assertEqual(merchant.business_name, "Test Merchant Ltd")
        self.assertEqual(merchant.business_type, "SMALL_BUSINESS")
        self.assertEqual(merchant.verification_status, "UNVERIFIED")
        self.assertTrue(merchant.is_active)
        self.assertFalse(merchant.is_flagged)

    def test_merchant_id_is_generated_when_missing(self):
        merchant = self.create_merchant()

        self.assertTrue(merchant.merchant_id)
        self.assertTrue(merchant.merchant_id.startswith("MER"))
        self.assertEqual(len(merchant.merchant_id), 11)

    def test_explicit_merchant_id_is_preserved(self):
        merchant = self.create_merchant(
            merchant_id="MERCHANT-001",
        )

        self.assertEqual(merchant.merchant_id, "MERCHANT-001")

    def test_merchant_id_is_unique(self):
        self.create_merchant(
            merchant_id="MERCHANT-001",
        )

        with self.assertRaises(IntegrityError):
            self.create_merchant(
                user=User.objects.create_user(
                    email="second@example.com",
                    password="TestPassword123!",
                ),
                merchant_id="MERCHANT-001",
            )

    def test_user_has_one_to_one_merchant_relationship(self):
        merchant = self.create_merchant()

        self.assertEqual(
            self.user.merchant_profile,
            merchant,
        )

    def test_default_financial_limits(self):
        merchant = self.create_merchant()

        self.assertEqual(
            merchant.transaction_fee_percentage,
            Decimal("1.50"),
        )
        self.assertEqual(
            merchant.daily_transaction_limit,
            Decimal("1000000.00"),
        )
        self.assertEqual(
            merchant.monthly_transaction_limit,
            Decimal("5000000.00"),
        )

    def test_default_settlement_schedule(self):
        merchant = self.create_merchant()

        self.assertEqual(
            merchant.settlement_schedule,
            "DAILY",
        )
        self.assertIsNone(merchant.last_settlement_at)
        self.assertIsNone(merchant.next_settlement_at)

    def test_default_statistics(self):
        merchant = self.create_merchant()

        self.assertEqual(merchant.total_transactions, 0)
        self.assertEqual(
            merchant.total_volume,
            Decimal("0.00"),
        )
        self.assertEqual(
            merchant.successful_transactions,
            0,
        )

    def test_default_document_fields_are_empty(self):
        merchant = self.create_merchant()

        self.assertFalse(merchant.id_document_front)
        self.assertFalse(merchant.id_document_back)
        self.assertFalse(merchant.business_registration_cert)
        self.assertFalse(merchant.utility_bill)

    def test_str(self):
        merchant = self.create_merchant(
            merchant_id="MER12345678",
        )

        self.assertEqual(
            str(merchant),
            "Test Merchant Ltd (MER12345678)",
        )

    def test_business_type_choices(self):
        expected = {
            "INDIVIDUAL",
            "SMALL_BUSINESS",
            "MEDIUM_BUSINESS",
            "ENTERPRISE",
            "ONLINE_STORE",
        }

        actual = {
            value
            for value, _label in Merchant.MERCHANT_TYPES
        }

        self.assertEqual(actual, expected)

    def test_verification_status_choices(self):
        expected = {
            "UNVERIFIED",
            "PENDING",
            "VERIFIED",
            "REJECTED",
            "SUSPENDED",
        }

        actual = {
            value
            for value, _label in Merchant.VERIFICATION_STATUS
        }

        self.assertEqual(actual, expected)

    def test_settlement_schedule_choices(self):
        expected = {
            "DAILY",
            "WEEKLY",
            "MONTHLY",
            "INSTANT",
        }

        actual = {
            value
            for value, _label in Merchant._meta.get_field(
                "settlement_schedule"
            ).choices
        }

        self.assertEqual(actual, expected)

    def test_verification_fields_can_be_set(self):
        verified_at = timezone.now()

        merchant = self.create_merchant(
            verification_status="VERIFIED",
            verified_at=verified_at,
            verified_by=self.verified_by,
        )

        self.assertEqual(
            merchant.verification_status,
            "VERIFIED",
        )
        self.assertEqual(
            merchant.verified_at,
            verified_at,
        )
        self.assertEqual(
            merchant.verified_by,
            self.verified_by,
        )

    def test_settlement_relationships(self):
        merchant = self.create_merchant()

        self.assertEqual(
            merchant.settlement_account,
            self.account,
        )
        self.assertEqual(
            merchant.settlement_bank,
            self.bank,
        )

        self.assertIn(
            merchant,
            self.account.merchant_settlements.all(),
        )
        self.assertIn(
            merchant,
            self.bank.merchant_banks.all(),
        )

    def test_settlement_account_is_protected(self):
        merchant = self.create_merchant()

        with self.assertRaises(ProtectedError):
            self.account.delete()

        self.assertTrue(
            Merchant.objects.filter(pk=merchant.pk).exists()
        )

    def test_settlement_bank_is_protected(self):
        merchant = self.create_merchant()

        with self.assertRaises(ProtectedError):
            self.bank.delete()

        self.assertTrue(
            Merchant.objects.filter(pk=merchant.pk).exists()
        )

    def test_user_deletion_is_protected_by_banking_account(self):
        merchant = self.create_merchant()

        with self.assertRaises(ProtectedError):
            self.user.delete()

        merchant.refresh_from_db()

        self.assertTrue(
            Merchant.objects.filter(pk=merchant.pk).exists()
        )

    def test_verified_by_deletion_sets_verified_by_null(self):
        merchant = self.create_merchant(
            verification_status="VERIFIED",
            verified_by=self.verified_by,
            verified_at=timezone.now(),
        )

        self.verified_by.delete()

        merchant.refresh_from_db()

        self.assertIsNone(merchant.verified_by)

    def test_calculate_fee_percentage(self):
        merchant = self.create_merchant(
            transaction_fee_percentage=Decimal("1.50"),
        )

        fee = merchant.calculate_fee(
            Decimal("1000.00")
        )

        self.assertEqual(
            fee,
            Decimal("15.00"),
        )

    def test_calculate_fee_enforces_minimum_fee(self):
        merchant = self.create_merchant(
            transaction_fee_percentage=Decimal("1.50"),
        )

        fee = merchant.calculate_fee(
            Decimal("100.00")
        )

        self.assertEqual(
            fee,
            Decimal("10.00"),
        )

    def test_calculate_fee_with_zero_percentage_still_returns_minimum(self):
        merchant = self.create_merchant(
            transaction_fee_percentage=Decimal("0.00"),
        )

        fee = merchant.calculate_fee(
            Decimal("1000.00")
        )

        self.assertEqual(
            fee,
            Decimal("10.00"),
        )

    def test_can_accept_payment_when_daily_total_is_below_limit(self):
        merchant = self.create_merchant(
            daily_transaction_limit=Decimal("1000000.00"),
        )

        result = merchant.can_accept_payment(
            Decimal("100000.00")
        )

        self.assertTrue(result)


    def test_can_accept_payment_rejects_when_daily_limit_would_be_exceeded(
        self,
    ):
        merchant = self.create_merchant(
            daily_transaction_limit=Decimal("100000.00"),
        )

        Transaction.objects.create(
            reference="TX-MERCHANT-001",
            account=self.account,
            amount=Decimal("90000.00"),
            type=Transaction.TRANSFER,
            recipient_account_number=self.account.nuban_number,
            status=Transaction.SUCCESS,
        )

        result = merchant.can_accept_payment(
            Decimal("20000.00")
        )

        self.assertFalse(result)


    def test_can_accept_payment_allows_amount_equal_to_remaining_limit(
        self,
    ):
        merchant = self.create_merchant(
            daily_transaction_limit=Decimal("100000.00"),
        )

        Transaction.objects.create(
            reference="TX-MERCHANT-002",
            account=self.account,
            amount=Decimal("60000.00"),
            type=Transaction.TRANSFER,
            recipient_account_number=self.account.nuban_number,
            status=Transaction.SUCCESS,
        )

        result = merchant.can_accept_payment(
            Decimal("40000.00")
        )

        self.assertTrue(result)


    def test_can_accept_payment_ignores_non_completed_transactions(self):
        merchant = self.create_merchant(
            daily_transaction_limit=Decimal("100000.00"),
        )

        Transaction.objects.create(
            reference="TX-MERCHANT-003",
            account=self.account,
            amount=Decimal("90000.00"),
            type=Transaction.TRANSFER,
            recipient_account_number=self.account.nuban_number,
            status=Transaction.PENDING,
        )

        result = merchant.can_accept_payment(
            Decimal("90000.00")
        )

        self.assertTrue(result)


    def test_can_accept_payment_ignores_completed_transactions_from_previous_days(
        self,
    ):
        merchant = self.create_merchant(
            daily_transaction_limit=Decimal("100000.00"),
        )

        transaction = Transaction.objects.create(
            reference="TX-MERCHANT-004",
            account=self.account,
            amount=Decimal("90000.00"),
            type=Transaction.TRANSFER,
            recipient_account_number=self.account.nuban_number,
            status=Transaction.SUCCESS,
        )

        Transaction.objects.filter(
            pk=transaction.pk
        ).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        result = merchant.can_accept_payment(
            Decimal("90000.00")
        )

        self.assertTrue(result)

    def test_merchant_transaction_creation(self):
        merchant = self.create_merchant()

        customer = User.objects.create_user(
            email="customer@example.com",
            password="TestPassword123!",
        )

        transaction = MerchantTransaction.objects.create(
            merchant=merchant,
            customer=customer,
            transaction_type="SALE",
            reference="MTX-001",
            amount=Decimal("50000.00"),
            fee=Decimal("750.00"),
            net_amount=Decimal("49250.00"),
            items=[
                {
                    "name": "Test Product",
                    "quantity": 1,
                    "price": "50000.00",
                }
            ],
        )

        self.assertIsNotNone(transaction.pk)
        self.assertEqual(transaction.merchant, merchant)
        self.assertEqual(transaction.customer, customer)
        self.assertEqual(transaction.status, "PENDING")
        self.assertFalse(transaction.is_settled)
        self.assertEqual(transaction.items[0]["name"], "Test Product")

    def test_merchant_transaction_defaults(self):
        merchant = self.create_merchant()

        customer = User.objects.create_user(
            email="customer@example.com",
            password="TestPassword123!",
        )

        transaction = MerchantTransaction.objects.create(
            merchant=merchant,
            customer=customer,
            transaction_type="SALE",
            reference="MTX-002",
            amount=Decimal("10000.00"),
            net_amount=Decimal("9850.00"),
        )

        self.assertEqual(
            transaction.fee,
            Decimal("0.00"),
        )
        self.assertEqual(
            transaction.items,
            [],
        )
        self.assertEqual(
            transaction.status,
            "PENDING",
        )
        self.assertFalse(transaction.is_settled)
        self.assertIsNone(transaction.settled_at)
        self.assertEqual(
            transaction.settlement_reference,
            "",
        )

    def test_merchant_transaction_str(self):
        merchant = self.create_merchant()

        customer = User.objects.create_user(
            email="customer@example.com",
            password="TestPassword123!",
        )

        transaction = MerchantTransaction.objects.create(
            merchant=merchant,
            customer=customer,
            transaction_type="SALE",
            reference="MTX-003",
            amount=Decimal("25000.00"),
            net_amount=Decimal("24625.00"),
        )

        self.assertEqual(
            str(transaction),
            "SALE - ₦25000.00 - Test Merchant Ltd",
        )

    def test_merchant_transaction_reference_is_unique(self):
        merchant = self.create_merchant()

        customer = User.objects.create_user(
            email="customer@example.com",
            password="TestPassword123!",
        )

        MerchantTransaction.objects.create(
            merchant=merchant,
            customer=customer,
            transaction_type="SALE",
            reference="MTX-UNIQUE",
            amount=Decimal("1000.00"),
            net_amount=Decimal("1000.00"),
        )

        with self.assertRaises(IntegrityError):
            MerchantTransaction.objects.create(
                merchant=merchant,
                customer=customer,
                transaction_type="SALE",
                reference="MTX-UNIQUE",
                amount=Decimal("2000.00"),
                net_amount=Decimal("2000.00"),
            )

    def test_merchant_transaction_relationships(self):
        merchant = self.create_merchant()

        customer = User.objects.create_user(
            email="customer@example.com",
            password="TestPassword123!",
        )

        transaction = MerchantTransaction.objects.create(
            merchant=merchant,
            customer=customer,
            transaction_type="SALE",
            reference="MTX-REL-001",
            amount=Decimal("10000.00"),
            net_amount=Decimal("10000.00"),
        )

        self.assertIn(
            transaction,
            merchant.transactions.all(),
        )
        self.assertIn(
            transaction,
            customer.merchant_purchases.all(),
        )

    def test_merchant_transaction_ordering(self):
        merchant = self.create_merchant()

        customer = User.objects.create_user(
            email="customer@example.com",
            password="TestPassword123!",
        )

        first = MerchantTransaction.objects.create(
            merchant=merchant,
            customer=customer,
            transaction_type="SALE",
            reference="MTX-ORDER-001",
            amount=Decimal("1000.00"),
            net_amount=Decimal("1000.00"),
        )

        second = MerchantTransaction.objects.create(
            merchant=merchant,
            customer=customer,
            transaction_type="REFUND",
            reference="MTX-ORDER-002",
            amount=Decimal("500.00"),
            net_amount=Decimal("500.00"),
        )

        transactions = list(
            MerchantTransaction.objects.all()
        )

        self.assertEqual(transactions[0].pk, second.pk)
        self.assertEqual(transactions[1].pk, first.pk)

    def test_merchant_transaction_settlement_fields(self):
        merchant = self.create_merchant()

        customer = User.objects.create_user(
            email="customer@example.com",
            password="TestPassword123!",
        )

        settled_at = timezone.now()

        transaction = MerchantTransaction.objects.create(
            merchant=merchant,
            customer=customer,
            transaction_type="SETTLEMENT",
            reference="MTX-SETTLE-001",
            amount=Decimal("50000.00"),
            fee=Decimal("750.00"),
            net_amount=Decimal("49250.00"),
            is_settled=True,
            settled_at=settled_at,
            settlement_reference="SET-001",
        )

        self.assertTrue(transaction.is_settled)
        self.assertEqual(
            transaction.settled_at,
            settled_at,
        )
        self.assertEqual(
            transaction.settlement_reference,
            "SET-001",
        )

    def test_merchant_deletion_cascades_to_merchant_transactions(self):
        merchant = self.create_merchant()

        customer = User.objects.create_user(
            email="customer@example.com",
            password="TestPassword123!",
        )

        transaction = MerchantTransaction.objects.create(
            merchant=merchant,
            customer=customer,
            transaction_type="SALE",
            reference="MTX-CASCADE-001",
            amount=Decimal("1000.00"),
            net_amount=Decimal("1000.00"),
        )

        transaction_id = transaction.pk

        merchant.delete()

        self.assertFalse(
            MerchantTransaction.objects.filter(
                pk=transaction_id
            ).exists()
        )