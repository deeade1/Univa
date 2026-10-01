import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone
from banking.services import notification_service as notify
from banking.models.accounting import AccountingJournal, AccountingManager
from banking.models.core import Account
from banking.models.payments import Transaction
from banking.models.qr_payments import QRCode, QRTransaction
from banking.models.merchant import Merchant

logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")

class QRService:
    """Handle QR code payments like OPay"""
    
    @staticmethod
    def create_qr_code(user, qr_type='STATIC', amount=None, merchant_id=None, description=""):
        """Create a QR code for payments"""
        
        merchant = None
        if merchant_id:
            try:
                merchant = Merchant.objects.get(merchant_id=merchant_id, user=user)
            except Merchant.DoesNotExist:
                raise ValidationError("Merchant not found or unauthorized")
        
        with db_transaction.atomic():
            # Generate QR code
            qr_code = QRCode.objects.create(
                creator=user,
                merchant=merchant,
                qr_type=qr_type,
                fixed_amount=amount,
                description=description,
                is_active=True,
                expires_at=timezone.now() + timezone.timedelta(days=90)  # 90 days validity
            )
            
            # Generate QR data and image
            qr_code.generate_qr_data()
            qr_code.save()
            
            return qr_code
    
    @staticmethod
    @db_transaction.atomic
    def pay_via_qr(
        *,
        scanner_user,
        qr_code: QRCode,
        payer_account: Account,
        amount=None,
        scanned_location: str = "",
        device_id: str = "",
    ) -> QRTransaction:
        """
        Pay a QR code.

        Posts one principal journal:

            payer_account -> payee_account

        No fee journal. Merchant fees (if any) are computed and posted
        by the merchant module at settlement time, not here.

        Owner scoping, QR validity, expiry, use limits, and balance
        checks all run inside this method so the GraphQL layer stays
        a thin wrapper.
        """
        # ------------------------------------------------------------------
        # 1. Validate inputs
        # ------------------------------------------------------------------
        if scanner_user is None or scanner_user.pk is None:
            raise ValidationError("Scanner user is required.")

        if qr_code is None or qr_code.pk is None:
            raise ValidationError("QR code is required.")

        if payer_account is None or payer_account.pk is None:
            raise ValidationError("Payer account is required.")

        if payer_account.user_id != scanner_user.pk:
            raise ValidationError("Payer account does not belong to this user.")

        if payer_account.is_system_account:
            raise ValidationError("Payer account cannot be a system account.")

        if payer_account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Payer account is not active.")

        # ------------------------------------------------------------------
        # 2. Validate QR state
        # ------------------------------------------------------------------
        if not qr_code.is_valid():
            raise ValidationError("QR code is expired, inactive, or fully used.")

        # ------------------------------------------------------------------
        # 3. Resolve payee and payee_account
        # ------------------------------------------------------------------
        if qr_code.merchant_id:
            payee = qr_code.merchant.user
            payee_account = qr_code.merchant.settlement_account
        else:
            payee = qr_code.creator
            payee_account = Account.objects.filter(user=payee).first()

        if payee is None:
            raise ValidationError("QR code has no payee.")

        if payee_account is None:
            raise ValidationError("Payee has no settlement account.")

        if payee_account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Payee account is not active.")

        # ------------------------------------------------------------------
        # 4. Prevent self-payment
        # ------------------------------------------------------------------
        if scanner_user.pk == payee.pk:
            raise ValidationError("Cannot pay yourself.")

        if payer_account.pk == payee_account.pk:
            raise ValidationError("Payer and payee accounts must be different.")

        # ------------------------------------------------------------------
        # 5. Resolve amount
        # ------------------------------------------------------------------
        if qr_code.qr_type == "STATIC":
            if qr_code.fixed_amount is None:
                raise ValidationError(
                    "Static QR code has no fixed amount."
                )
            payment_amount = qr_code.fixed_amount.quantize(MONEY_QUANTUM)
        else:
            # DYNAMIC / MERCHANT / PERSONAL: caller supplies the amount.
            if amount is None:
                raise ValidationError(
                    "Amount is required for this QR code type."
                )
            payment_amount = QRService._validate_amount(amount)

        if (
            qr_code.max_amount_per_use
            and payment_amount > qr_code.max_amount_per_use
        ):
            raise ValidationError(
                f"Amount exceeds the maximum per-use limit of "
                f"₦{qr_code.max_amount_per_use:,.2f}."
            )

        # ------------------------------------------------------------------
        # 6. Balance check (authoritative check happens again inside
        #    create_double_entry once the accounts are row-locked)
        # ------------------------------------------------------------------
        if payer_account.get_balance() < payment_amount:
            raise ValidationError("Insufficient funds in payer account.")

        # ------------------------------------------------------------------
        # 7. Create the Transaction row
        # ------------------------------------------------------------------
        reference = (
            f"QR-{timezone.now().strftime('%Y%m%d')}-"
            f"{timezone.now().strftime('%H%M%S')}"
        )

        txn = Transaction.objects.create(
            account=payer_account,
            amount=payment_amount,
            type=Transaction.TRANSFER,
            narration=(
                f"QR payment: {qr_code.description}"
                if qr_code.description
                else f"QR payment {qr_code.qr_id}"
            ),
            recipient_name=payee.get_full_name() or payee.email,
            recipient_account_number=payee_account.nuban_number,
            status=Transaction.PENDING,
        )

        # ------------------------------------------------------------------
        # 8. Post the ledger journal
        # ------------------------------------------------------------------
        journal = AccountingManager.create_double_entry(
            transaction=txn,
            debit_account=payer_account,
            credit_account=payee_account,
            amount=payment_amount,
            description=(
                f"QR payment {qr_code.qr_id}: {qr_code.description}"
                if qr_code.description
                else f"QR payment {qr_code.qr_id}"
            ),
            journal_type=AccountingJournal.TRANSFER,
            created_by=scanner_user,
        )

        # ------------------------------------------------------------------
        # 9. Write journal back to the Transaction row
        # ------------------------------------------------------------------
        txn.journal = journal
        txn.status = Transaction.SUCCESS
        txn.balance_after = payer_account.get_balance()
        txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # ------------------------------------------------------------------
        # 10. Create the QRTransaction business record
        # ------------------------------------------------------------------
        qr_transaction = QRTransaction.objects.create(
            qr_code=qr_code,
            payer=scanner_user,
            payer_account=payer_account,
            payee=payee,
            payee_account=payee_account,
            amount=payment_amount,
            reference=reference,
            status="COMPLETED",
            scanned_at=timezone.now(),
            scanned_location=scanned_location,
            device_id=device_id,
            completed_at=timezone.now(),
            journal=journal,
        )

        # ------------------------------------------------------------------
        # 11. Increment QR usage (last, so a failed posting never burns a use)
        # ------------------------------------------------------------------
        qr_code.increment_usage()

        logger.info(
            "QR payment %s: %s -> %s amount=%s journal=%s",
            qr_transaction.reference,
            payer_account.pk,
            payee_account.pk,
            payment_amount,
            journal.pk,
        )
        notify.emit_qr_payment_successful(
            user=scanner_user,
            qr_transaction=qr_transaction,
        )
        return qr_transaction
    
    @staticmethod
    def _validate_amount(amount) -> Decimal:
        if amount is None:
            raise ValidationError("Amount is required.")
        try:
            value = Decimal(str(amount))
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise ValidationError("Invalid amount.") from exc
        if not value.is_finite():
            raise ValidationError("Amount must be finite.")
        if value <= Decimal("0.00"):
            raise ValidationError("Amount must be greater than zero.")
        return value.quantize(MONEY_QUANTUM)