from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.core import Account
from banking.models.accounting import AccountingManager
#from payment.models import Transaction
from banking.services.bank_manager import BankAPIManager


class BankingOrchestrator:
    """
    Orchestrates end-to-end Nigerian transfers:
    User → Internal Float → External Bank
    """

    @staticmethod
    @db_transaction.atomic
    def process_nigerian_transfer(sender_profile, recipient_data, amount, narration):
        sender_account = sender_profile.account

        if sender_account.status != "ACTIVE":
            raise ValidationError("Sender account is not active")

        if Decimal(amount) <= 0:
            raise ValidationError("Invalid transfer amount")

        # 1️⃣ Create transaction
        '''txn = Transaction.objects.create(
            user=sender_profile,
            transaction_type="TRANSFER",
            amount=amount,
            status="PENDING",
            description=narration,
        )'''

        # 2️⃣ Lock and fetch FLOAT account
        float_account = (
            Account.objects
            .select_for_update()
            .filter(is_system_account=True, linked_float_account__isnull=False)
            .first()
        )

        if not float_account:
            raise RuntimeError("System float account not configured")

        # 3️⃣ Internal ledger movement
        AccountingManager.create_double_entry(
            transaction=txn,
            debit_account=sender_account,
            credit_account=float_account,
            amount=amount,
            description=narration,
        )

        # 4️⃣ External transfer
        try:
            bank_result = BankAPIManager.transfer_funds(
                from_account=float_account.linked_float_account.account_number,
                to_account=recipient_data["account_number"],
                to_bank_code=recipient_data["bank_code"],
                amount=amount,
                narration=narration,
            )
        except Exception as exc:
            txn.status = "FAILED"
            txn.failure_reason = str(exc)
            txn.save()
            raise

        if not bank_result["success"]:
            txn.status = "FAILED"
            txn.save()
            raise RuntimeError("External bank transfer failed")

        # 5️⃣ Finalize
        txn.status = "COMPLETED"
        txn.bank_reference = bank_result["reference"]
        txn.completed_at = timezone.now()
        txn.save()

        return txn
