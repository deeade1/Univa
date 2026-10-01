# apps/backend/graphq/banking/mutations/accounting.py

"""
This module contains mutations for:
    - AccountingJournal: posted only via
      AccountingManager.create_double_entry (staff-only mutation)
    - FloatAccount: External bank accounts
    - KYCDocument: KYC documents
    - KYCDocumentVerification: KYC verification results
    - ForexLimit: Foreign exchange limits
    - CurrencyWallet: Currency wallet metadata
    - ForexTransaction: Foreign exchange transactions
    - TransactionDispute: Transaction disputes
    - DisputeEvidence: Dispute evidence
    - SystemAccount: System account metadata

LedgerEntry and raw journal-header creation are intentionally NOT
exposed as mutations. All ledger posting flows through
AccountingManager.create_double_entry.
"""

import base64
import logging
import uuid
from datetime import date
from decimal import Decimal
import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction as db_transaction
from django.utils import timezone
from graphene import ID, Boolean, Decimal as GrapheneDecimal, Field, Int, String, relay
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from graphql_relay import from_global_id


from banking.models.accounting import (
    AccountingJournal,
    AccountingManager,
    CurrencyWallet,
    DisputeEvidence,
    FloatAccount,
    ForexLimit,
    ForexTransaction,
    KYCDocument,
    KYCDocumentVerification,
    SystemAccount,
    TransactionDispute,
)
from banking.models.core import Account
from banking.models.payments import Transaction
from graphq.accounts.types.user import UserNode
from graphq.banking.types.accounting import (
    AccountingJournalNode,
    CurrencyWalletNode,
    DisputeEvidenceNode,
    FloatAccountNode,
    ForexLimitNode,
    ForexTransactionNode,
    KYCDocumentNode,
    KYCDocumentVerificationNode,
    SystemAccountNode,
    TransactionDisputeNode,
)
from univa_jwt.decorators import login_required

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def _get_authenticated_user(info):
    """Return the authenticated Django user."""
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user

def _require_staff(user):
    """Raise if the authenticated user is not staff."""
    if not user.is_staff:
        raise GraphQLError("Staff privileges required.")

def _validate_amount(amount):
    """Validate and normalize a monetary amount."""
    try:
        amount = Decimal(str(amount))
    except (TypeError, ValueError):
        raise GraphQLError("Invalid amount value.")
    
    if amount <= Decimal("0.00"):
        raise GraphQLError("Amount must be greater than zero.")
    
    return amount.quantize(Decimal("0.01"))


def _validate_date(date_value):
    """Validate a date input."""
    if not date_value:
        return None
    if isinstance(date_value, date):
        return date_value
    if isinstance(date_value, str):
        try:
            return date.fromisoformat(date_value)
        except ValueError:
            raise GraphQLError("Invalid date format. Use YYYY-MM-DD.")
    raise GraphQLError("Invalid date value.")


def _get_model_by_global_id(global_id, model, model_name):
    """Get a model instance by Relay global ID."""
    if not global_id:
        raise GraphQLError(f"{model_name} ID is required.")
    
    try:
        _, pk = from_global_id(global_id)
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise GraphQLError(f"{model_name} not found.")
    except Exception as exc:
        raise GraphQLError(f"Invalid {model_name} ID.") from exc



# ============================================================================
# ACCOUNTING JOURNAL MUTATIONS
# ============================================================================


class CreateDoubleEntryMutation(relay.ClientIDMutation):
    """
    Create a balanced double-entry journal. STAFF ONLY.

    This is the administrative entry point for posting arbitrary
    journals. Customer-facing money movement must go through the
    per-module services (bill payments, savings, investments,
    qr payments, etc.), which call
    AccountingManager.create_double_entry internally.

    Creates both debit and credit entries in one atomic operation
    and verifies the resulting journal balances before marking it
    posted.
    """
    class Input:
        debit_account_id = ID(required=True)
        credit_account_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        description = String()
        journal_type = String()
        transaction_id = ID()

    journal = Field(AccountingJournalNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)  
        
        # Get accounts
        debit_account = _get_model_by_global_id(
            input["debit_account_id"], Account, "Debit account"
        )
        credit_account = _get_model_by_global_id(
            input["credit_account_id"], Account, "Credit account"
        )
        
        # Get optional transaction
        transaction = None
        if input.get("transaction_id"):
            transaction = _get_model_by_global_id(
                input["transaction_id"], Transaction, "Transaction"
            )
        
        # Validate amount
        amount = _validate_amount(input["amount"])
        
        # Validate journal type
        journal_type = input.get("journal_type", AccountingJournal.TRANSFER)
        valid_types = [choice[0] for choice in AccountingJournal.JOURNAL_TYPES]
        if journal_type not in valid_types:
            raise GraphQLError(f"Invalid journal type. Must be one of: {', '.join(valid_types)}")
        
        # Create double entry
        try:
            journal = AccountingManager.create_double_entry(
                transaction=transaction,
                debit_account=debit_account,
                credit_account=credit_account,
                amount=amount,
                description=input.get("description", ""),
                journal_type=journal_type,
                created_by=user,
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            journal=journal,
            success=True,
            message="Double-entry journal created successfully.",
        )


# ============================================================================
# FLOAT ACCOUNT MUTATIONS
# ============================================================================

class CreateFloatAccountMutation(relay.ClientIDMutation):
    """Create a float account for external bank operations."""

    class Input:
        bank_name = String(required=True)
        account_number = String(required=True)
        account_name = String(required=True)
        statement_balance = GrapheneDecimal()
        max_daily_deposit = GrapheneDecimal()
        max_daily_withdrawal = GrapheneDecimal()

    float_account = Field(FloatAccountNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Validate bank name
        valid_banks = [choice[0] for choice in FloatAccount.BANK_CHOICES]
        if input["bank_name"] not in valid_banks:
            raise GraphQLError(f"Invalid bank name. Must be one of: {', '.join(valid_banks)}")
        
        # Check if account number already exists
        if FloatAccount.objects.filter(account_number=input["account_number"]).exists():
            raise GraphQLError("Account number already exists.")
        
        # Create float account
        try:
            float_account = FloatAccount.objects.create(
                bank_name=input["bank_name"],
                account_number=input["account_number"],
                account_name=input["account_name"],
                statement_balance=Decimal(input["statement_balance"]) if input.get("statement_balance") else None,
                max_daily_deposit=Decimal(input.get("max_daily_deposit", "10000000.00")),
                max_daily_withdrawal=Decimal(input.get("max_daily_withdrawal", "10000000.00")),
                is_active=True,
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            float_account=float_account,
            success=True,
            message="Float account created successfully.",
        )


class UpdateFloatAccountMutation(relay.ClientIDMutation):
    """Update a float account."""

    class Input:
        float_account_id = ID(required=True)
        bank_name = String()
        account_name = String()
        statement_balance = GrapheneDecimal()
        max_daily_deposit = GrapheneDecimal()
        max_daily_withdrawal = GrapheneDecimal()
        is_active = Boolean()

    float_account = Field(FloatAccountNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        float_account = _get_model_by_global_id(
            input["float_account_id"], FloatAccount, "Float account"
        )
        
        # Update fields
        if input.get("bank_name"):
            valid_banks = [choice[0] for choice in FloatAccount.BANK_CHOICES]
            if input["bank_name"] not in valid_banks:
                raise GraphQLError(f"Invalid bank name. Must be one of: {', '.join(valid_banks)}")
            float_account.bank_name = input["bank_name"]
        
        if input.get("account_name"):
            float_account.account_name = input["account_name"]
        
        if input.get("statement_balance"):
            float_account.statement_balance = Decimal(input["statement_balance"])
        
        if input.get("max_daily_deposit"):
            float_account.max_daily_deposit = Decimal(input["max_daily_deposit"])
        
        if input.get("max_daily_withdrawal"):
            float_account.max_daily_withdrawal = Decimal(input["max_daily_withdrawal"])
        
        if input.get("is_active") is not None:
            float_account.is_active = input["is_active"]
        
        try:
            float_account.save()
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            float_account=float_account,
            success=True,
            message="Float account updated successfully.",
        )


class DeleteFloatAccountMutation(relay.ClientIDMutation):
    """Delete a float account (soft delete by setting is_active=False)."""

    class Input:
        float_account_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        float_account = _get_model_by_global_id(
            input["float_account_id"], FloatAccount, "Float account"
        )
        
        # Soft delete by deactivating
        float_account.is_active = False
        float_account.save(update_fields=["is_active"])
        
        return cls(
            success=True,
            message="Float account deactivated successfully.",
        )


# ============================================================================
# KYC DOCUMENT MUTATIONS
# ============================================================================

class CreateKYCDocumentMutation(relay.ClientIDMutation):
    """Create a KYC document."""

    class Input:
        document_type = String(required=True)
        document_number = String()
        document_file = String(required=True)  # Base64 encoded
        country = String()
        issued_date = String()
        expiry_date = String()

    kyc_document = Field(KYCDocumentNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Validate document type
        if not input["document_type"]:
            raise GraphQLError("Document type is required.")
        
        # Decode base64 file
        try:
            file_data = base64.b64decode(input["document_file"])
            file_content = ContentFile(file_data)
            file_name = f"{input['document_type']}_{user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
        except Exception as exc:
            raise GraphQLError("Invalid file data. Must be base64 encoded.") from exc
        
        # Parse dates
        issued_date = _validate_date(input.get("issued_date"))
        expiry_date = _validate_date(input.get("expiry_date"))
        
        # Check if document already exists
        if KYCDocument.objects.filter(user=user, document_type=input["document_type"]).exists():
            raise GraphQLError(f"Document type '{input['document_type']}' already exists for this user.")
        
        # Create KYC document
        try:
            kyc_document = KYCDocument.objects.create(
                user=user,
                document_type=input["document_type"],
                document_number=input.get("document_number", ""),
                document_file=file_content,
                country=input.get("country", "NG"),
                issued_date=issued_date,
                expiry_date=expiry_date,
                status="PENDING",
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            kyc_document=kyc_document,
            success=True,
            message="KYC document created successfully.",
        )


class UpdateKYCDocumentMutation(relay.ClientIDMutation):
    """Update a KYC document."""

    class Input:
        kyc_document_id = ID(required=True)
        document_number = String()
        document_file = String()
        country = String()
        issued_date = String()
        expiry_date = String()
        status = String()
        rejection_reason = String()

    kyc_document = Field(KYCDocumentNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        kyc_document = _get_model_by_global_id(
            input["kyc_document_id"], KYCDocument, "KYC document"
        )
        
        # Check ownership
        if kyc_document.user != user:
            raise GraphQLError("You do not own this KYC document.")
        
        # Update fields
        if input.get("document_number"):
            kyc_document.document_number = input["document_number"]
        
        if input.get("document_file"):
            try:
                file_data = base64.b64decode(input["document_file"])
                file_content = ContentFile(file_data)
                file_name = f"{kyc_document.document_type}_{user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
                kyc_document.document_file.save(file_name, file_content, save=False)
            except Exception as exc:
                raise GraphQLError("Invalid file data. Must be base64 encoded.") from exc
        
        if input.get("country"):
            kyc_document.country = input["country"]
        
        if input.get("issued_date"):
            kyc_document.issued_date = _validate_date(input["issued_date"])
        
        if input.get("expiry_date"):
            kyc_document.expiry_date = _validate_date(input["expiry_date"])
        
        if input.get("status"):
            valid_statuses = ["PENDING", "VERIFIED", "REJECTED", "MANUAL_REVIEW"]
            if input["status"] not in valid_statuses:
                raise GraphQLError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            kyc_document.status = input["status"]
            if input["status"] == "VERIFIED":
                kyc_document.verified_at = timezone.now()
                kyc_document.verified_by = user
        
        if input.get("rejection_reason"):
            kyc_document.rejection_reason = input["rejection_reason"]
        
        try:
            kyc_document.save()
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            kyc_document=kyc_document,
            success=True,
            message="KYC document updated successfully.",
        )


class DeleteKYCDocumentMutation(relay.ClientIDMutation):
    """Delete a KYC document."""

    class Input:
        kyc_document_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        kyc_document = _get_model_by_global_id(
            input["kyc_document_id"], KYCDocument, "KYC document"
        )
        
        # Check ownership
        if kyc_document.user != user:
            raise GraphQLError("You do not own this KYC document.")
        
        # Delete the document
        kyc_document.delete()
        
        return cls(
            success=True,
            message="KYC document deleted successfully.",
        )


# ============================================================================
# KYC DOCUMENT VERIFICATION MUTATIONS
# ============================================================================

class CreateKYCDocumentVerificationMutation(relay.ClientIDMutation):
    """Create a KYC document verification record."""

    class Input:
        document_id = ID(required=True)
        status = String(required=True)
        verification_type = String(required=True)
        verification_result = GenericScalar()

    verification = Field(KYCDocumentVerificationNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        document = _get_model_by_global_id(
            input["document_id"], KYCDocument, "KYC document"
        )
        
        # Validate status and type
        if not input["status"] or not input["verification_type"]:
            raise GraphQLError("Status and verification type are required.")
        
        # Create verification
        try:
            verification = KYCDocumentVerification.objects.create(
                document=document,
                status=input["status"],
                verification_type=input["verification_type"],
                verification_result=input.get("verification_result", {}),
                verified_at=timezone.now() if input["status"] == "VERIFIED" else None,
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            verification=verification,
            success=True,
            message="KYC document verification created successfully.",
        )


# ============================================================================
# FOREX LIMIT MUTATIONS
# ============================================================================

class CreateForexLimitMutation(relay.ClientIDMutation):
    """Create a foreign exchange limit for a user."""

    class Input:
        user_id = ID()
        currency_pair = String(required=True)
        daily_limit = GrapheneDecimal(required=True)
        monthly_limit = GrapheneDecimal(required=True)

    forex_limit = Field(ForexLimitNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        requesting_user = _get_authenticated_user(info)
        
        # Determine target user
        if input.get("user_id"):
            target_user = _get_model_by_global_id(input["user_id"], User, "User")
            # Check if requesting user is admin (you can add admin check here)
        else:
            target_user = requesting_user
        
        # Validate currency pair
        if not input["currency_pair"] or len(input["currency_pair"]) != 6:
            raise GraphQLError("Currency pair must be 6 characters (e.g., USDNGN).")
        
        # Validate limits
        daily_limit = _validate_amount(input["daily_limit"])
        monthly_limit = _validate_amount(input["monthly_limit"])
        
        # Check if limit already exists
        if ForexLimit.objects.filter(user=target_user, currency_pair=input["currency_pair"]).exists():
            raise GraphQLError("Forex limit already exists for this currency pair.")
        
        # Create forex limit
        try:
            forex_limit = ForexLimit.objects.create(
                user=target_user,
                currency_pair=input["currency_pair"],
                daily_limit=daily_limit,
                monthly_limit=monthly_limit,
                is_active=True,
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            forex_limit=forex_limit,
            success=True,
            message="Forex limit created successfully.",
        )


class UpdateForexLimitMutation(relay.ClientIDMutation):
    """Update a foreign exchange limit."""

    class Input:
        forex_limit_id = ID(required=True)
        daily_limit = GrapheneDecimal()
        monthly_limit = GrapheneDecimal()
        is_active = Boolean()

    forex_limit = Field(ForexLimitNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        forex_limit = _get_model_by_global_id(
            input["forex_limit_id"], ForexLimit, "Forex limit"
        )
        
        # Check ownership or admin
        if forex_limit.user != user:
            # Add admin check here if needed
            raise GraphQLError("You do not own this forex limit.")
        
        # Update fields
        if input.get("daily_limit"):
            forex_limit.daily_limit = _validate_amount(input["daily_limit"])
        
        if input.get("monthly_limit"):
            forex_limit.monthly_limit = _validate_amount(input["monthly_limit"])
        
        if input.get("is_active") is not None:
            forex_limit.is_active = input["is_active"]
        
        try:
            forex_limit.save()
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            forex_limit=forex_limit,
            success=True,
            message="Forex limit updated successfully.",
        )


class DeleteForexLimitMutation(relay.ClientIDMutation):
    """Delete a foreign exchange limit."""

    class Input:
        forex_limit_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        forex_limit = _get_model_by_global_id(
            input["forex_limit_id"], ForexLimit, "Forex limit"
        )
        
        # Check ownership
        if forex_limit.user != user:
            raise GraphQLError("You do not own this forex limit.")
        
        forex_limit.delete()
        
        return cls(
            success=True,
            message="Forex limit deleted successfully.",
        )


# ============================================================================
# CURRENCY WALLET MUTATIONS
# ============================================================================

class CreateCurrencyWalletMutation(relay.ClientIDMutation):
    """Create a currency wallet for a user."""

    class Input:
        currency = String(required=True)
        account_number = String(required=True)
        account_id = ID()

    currency_wallet = Field(CurrencyWalletNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Validate currency
        if not input["currency"] or len(input["currency"]) != 3:
            raise GraphQLError("Currency must be 3 characters (e.g., NGN, USD).")
        
        # Get optional account
        account = None
        if input.get("account_id"):
            account = _get_model_by_global_id(input["account_id"], Account, "Account")
            if account.user != user:
                raise GraphQLError("Account does not belong to this user.")
        
        # Check if wallet already exists
        if CurrencyWallet.objects.filter(user=user, currency=input["currency"]).exists():
            raise GraphQLError("Currency wallet already exists for this currency.")
        
        # Check if account number is unique
        if CurrencyWallet.objects.filter(account_number=input["account_number"]).exists():
            raise GraphQLError("Account number already in use.")
        
        # Create currency wallet
        try:
            currency_wallet = CurrencyWallet.objects.create(
                user=user,
                currency=input["currency"],
                account_number=input["account_number"],
                account=account,
                is_active=True,
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            currency_wallet=currency_wallet,
            success=True,
            message="Currency wallet created successfully.",
        )


class UpdateCurrencyWalletMutation(relay.ClientIDMutation):
    """Update a currency wallet."""

    class Input:
        currency_wallet_id = ID(required=True)
        account_id = ID()
        is_active = Boolean()

    currency_wallet = Field(CurrencyWalletNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        currency_wallet = _get_model_by_global_id(
            input["currency_wallet_id"], CurrencyWallet, "Currency wallet"
        )
        
        # Check ownership
        if currency_wallet.user != user:
            raise GraphQLError("You do not own this currency wallet.")
        
        # Update fields
        if input.get("account_id"):
            account = _get_model_by_global_id(input["account_id"], Account, "Account")
            if account.user != user:
                raise GraphQLError("Account does not belong to this user.")
            currency_wallet.account = account
        
        if input.get("is_active") is not None:
            currency_wallet.is_active = input["is_active"]
        
        try:
            currency_wallet.save()
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            currency_wallet=currency_wallet,
            success=True,
            message="Currency wallet updated successfully.",
        )


class DeleteCurrencyWalletMutation(relay.ClientIDMutation):
    """Delete a currency wallet."""

    class Input:
        currency_wallet_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        currency_wallet = _get_model_by_global_id(
            input["currency_wallet_id"], CurrencyWallet, "Currency wallet"
        )
        
        # Check ownership
        if currency_wallet.user != user:
            raise GraphQLError("You do not own this currency wallet.")
        
        currency_wallet.delete()
        
        return cls(
            success=True,
            message="Currency wallet deleted successfully.",
        )


# ============================================================================
# FOREX TRANSACTION MUTATIONS
# ============================================================================

class CreateForexTransactionMutation(relay.ClientIDMutation):
    """Create a foreign exchange transaction."""

    class Input:
        transaction_type = String(required=True)
        source_currency = String(required=True)
        target_currency = String(required=True)
        source_amount = GrapheneDecimal(required=True)
        target_amount = GrapheneDecimal(required=True)
        exchange_rate = GrapheneDecimal(required=True)
        fee = GrapheneDecimal()
        status = String()

    forex_transaction = Field(ForexTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Validate transaction type
        valid_types = [choice[0] for choice in ForexTransaction.TRANSACTION_TYPES]
        if input["transaction_type"] not in valid_types:
            raise GraphQLError(f"Invalid transaction type. Must be one of: {', '.join(valid_types)}")
        
        # Validate currencies
        if not input["source_currency"] or len(input["source_currency"]) != 3:
            raise GraphQLError("Source currency must be 3 characters.")
        if not input["target_currency"] or len(input["target_currency"]) != 3:
            raise GraphQLError("Target currency must be 3 characters.")
        if input["source_currency"] == input["target_currency"]:
            raise GraphQLError("Source and target currencies must be different.")
        
        # Validate amounts
        source_amount = _validate_amount(input["source_amount"])
        target_amount = _validate_amount(input["target_amount"])
        exchange_rate = Decimal(str(input["exchange_rate"]))
        fee = Decimal(str(input.get("fee", "0.00")))
        
        # Validate exchange rate
        if exchange_rate <= Decimal("0"):
            raise GraphQLError("Exchange rate must be greater than zero.")
        
        # Create forex transaction
        try:
            forex_transaction = ForexTransaction.objects.create(
                user=user,
                transaction_type=input["transaction_type"],
                source_currency=input["source_currency"],
                target_currency=input["target_currency"],
                source_amount=source_amount,
                target_amount=target_amount,
                exchange_rate=exchange_rate,
                fee=fee,
                status=input.get("status", "PENDING"),
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            forex_transaction=forex_transaction,
            success=True,
            message="Forex transaction created successfully.",
        )


class UpdateForexTransactionMutation(relay.ClientIDMutation):
    """Update a foreign exchange transaction."""

    class Input:
        forex_transaction_id = ID(required=True)
        status = String()
        fee = GrapheneDecimal()

    forex_transaction = Field(ForexTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        forex_transaction = _get_model_by_global_id(
            input["forex_transaction_id"], ForexTransaction, "Forex transaction"
        )
        
        # Check ownership
        if forex_transaction.user != user:
            raise GraphQLError("You do not own this forex transaction.")
        
        # Update fields
        if input.get("status"):
            forex_transaction.status = input["status"]
        
        if input.get("fee"):
            forex_transaction.fee = Decimal(input["fee"])
        
        try:
            forex_transaction.save()
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            forex_transaction=forex_transaction,
            success=True,
            message="Forex transaction updated successfully.",
        )


# ============================================================================
# TRANSACTION DISPUTE MUTATIONS
# ============================================================================

class CreateTransactionDisputeMutation(relay.ClientIDMutation):
    """Create a transaction dispute."""

    class Input:
        transaction_id = ID(required=True)
        dispute_type = String(required=True)
        reason = String(required=True)
        description = String(required=True)
        requested_amount = GrapheneDecimal(required=True)
        priority = String()
        contact_preference = String()
        estimated_resolution_date = String(required=True)

    dispute = Field(TransactionDisputeNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Get transaction
        transaction = _get_model_by_global_id(
            input["transaction_id"], Transaction, "Transaction"
        )
        
        # Validate amount
        requested_amount = _validate_amount(input["requested_amount"])
        
        # Validate resolution date
        resolution_date = _validate_date(input["estimated_resolution_date"])
        if not resolution_date:
            raise GraphQLError("Estimated resolution date is required.")
        
        # Create dispute
        try:
            dispute = TransactionDispute.objects.create(
                user=user,
                transaction=transaction,
                case_number=f"DSP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                dispute_type=input["dispute_type"],
                reason=input["reason"],
                description=input["description"],
                requested_amount=requested_amount,
                priority=input.get("priority", "NORMAL"),
                contact_preference=input.get("contact_preference", "EMAIL"),
                estimated_resolution_date=resolution_date,
                status="OPEN",
                created_by_user=True,
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            dispute=dispute,
            success=True,
            message="Transaction dispute created successfully.",
        )


class UpdateTransactionDisputeMutation(relay.ClientIDMutation):
    """Update a transaction dispute."""

    class Input:
        dispute_id = ID(required=True)
        status = String()
        priority = String()
        resolution = String()
        refund_amount = GrapheneDecimal()
        resolution_date = String()

    dispute = Field(TransactionDisputeNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        dispute = _get_model_by_global_id(
            input["dispute_id"], TransactionDispute, "Dispute"
        )
        
        # Update fields
        if input.get("status"):
            valid_statuses = ["OPEN", "IN_PROGRESS", "RESOLVED", "REJECTED", "ESCALATED"]
            if input["status"] not in valid_statuses:
                raise GraphQLError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            dispute.status = input["status"]
        
        if input.get("priority"):
            dispute.priority = input["priority"]
        
        if input.get("resolution"):
            dispute.resolution = input["resolution"]
        
        if input.get("refund_amount"):
            dispute.refund_amount = Decimal(input["refund_amount"])
        
        if input.get("resolution_date"):
            dispute.resolution_date = _validate_date(input["resolution_date"])
        
        try:
            dispute.save()
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            dispute=dispute,
            success=True,
            message="Dispute updated successfully.",
        )


# ============================================================================
# DISPUTE EVIDENCE MUTATIONS
# ============================================================================

class CreateDisputeEvidenceMutation(relay.ClientIDMutation):
    """Add evidence to a transaction dispute."""

    class Input:
        dispute_id = ID(required=True)
        evidence_type = String(required=True)
        file = String(required=True)  # Base64 encoded
        description = String()

    evidence = Field(DisputeEvidenceNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        dispute = _get_model_by_global_id(
            input["dispute_id"], TransactionDispute, "Dispute"
        )
        
        # Check ownership
        if dispute.user != user:
            raise GraphQLError("You do not own this dispute.")
        
        # Decode base64 file
        try:
            file_data = base64.b64decode(input["file"])
            file_content = ContentFile(file_data)
            file_name = f"evidence_{dispute.case_number}_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
        except Exception as exc:
            raise GraphQLError("Invalid file data. Must be base64 encoded.") from exc
        
        # Create evidence
        try:
            evidence = DisputeEvidence.objects.create(
                dispute=dispute,
                evidence_type=input["evidence_type"],
                file=file_content,
                description=input.get("description", ""),
                uploaded_by_user=True,
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            evidence=evidence,
            success=True,
            message="Evidence added successfully.",
        )


# ============================================================================
# SYSTEM ACCOUNT MUTATIONS
# ============================================================================

class CreateSystemAccountMutation(relay.ClientIDMutation):
    """Create a system account configuration."""

    class Input:
        account_id = ID(required=True)
        purpose = String(required=True)
        description = String()

    system_account = Field(SystemAccountNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Get account
        account = _get_model_by_global_id(
            input["account_id"], Account, "Account"
        )
        
        # Validate purpose
        valid_purposes = [choice[0] for choice in SystemAccount.PURPOSE_CHOICES]
        if input["purpose"] not in valid_purposes:
            raise GraphQLError(f"Invalid purpose. Must be one of: {', '.join(valid_purposes)}")
        
        # Check if purpose already exists
        if SystemAccount.objects.filter(purpose=input["purpose"]).exists():
            raise GraphQLError(f"System account for purpose '{input['purpose']}' already exists.")
        
        # Create system account
        try:
            system_account = SystemAccount.objects.create(
                account=account,
                purpose=input["purpose"],
                description=input.get("description", ""),
                is_active=True,
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            system_account=system_account,
            success=True,
            message="System account created successfully.",
        )


class UpdateSystemAccountMutation(relay.ClientIDMutation):
    """Update a system account configuration."""

    class Input:
        system_account_id = ID(required=True)
        description = String()
        is_active = Boolean()

    system_account = Field(SystemAccountNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        system_account = _get_model_by_global_id(
            input["system_account_id"], SystemAccount, "System account"
        )
        
        # Update fields
        if input.get("description") is not None:
            system_account.description = input["description"]
        
        if input.get("is_active") is not None:
            system_account.is_active = input["is_active"]
        
        try:
            system_account.save()
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            system_account=system_account,
            success=True,
            message="System account updated successfully.",
        )


class DeleteSystemAccountMutation(relay.ClientIDMutation):
    """Delete a system account configuration (soft delete by deactivating)."""

    class Input:
        system_account_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        system_account = _get_model_by_global_id(
            input["system_account_id"], SystemAccount, "System account"
        )
        
        # Soft delete by deactivating
        system_account.is_active = False
        system_account.save(update_fields=["is_active"])
        
        return cls(
            success=True,
            message="System account deactivated successfully.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class AccountingMutations(graphene.ObjectType):
    
    # Accounting Journal
    create_double_entry = CreateDoubleEntryMutation.Field()
    
    # Float Account
    create_float_account = CreateFloatAccountMutation.Field()
    update_float_account = UpdateFloatAccountMutation.Field()
    delete_float_account = DeleteFloatAccountMutation.Field()
    
    # KYC Document
    create_kyc_document = CreateKYCDocumentMutation.Field()
    update_kyc_document = UpdateKYCDocumentMutation.Field()
    delete_kyc_document = DeleteKYCDocumentMutation.Field()
    
    # KYC Document Verification
    create_kyc_document_verification = CreateKYCDocumentVerificationMutation.Field()
    
    # Forex Limit
    create_forex_limit = CreateForexLimitMutation.Field()
    update_forex_limit = UpdateForexLimitMutation.Field()
    delete_forex_limit = DeleteForexLimitMutation.Field()
    
    # Currency Wallet
    create_currency_wallet = CreateCurrencyWalletMutation.Field()
    update_currency_wallet = UpdateCurrencyWalletMutation.Field()
    delete_currency_wallet = DeleteCurrencyWalletMutation.Field()
    
    # Forex Transaction
    create_forex_transaction = CreateForexTransactionMutation.Field()
    update_forex_transaction = UpdateForexTransactionMutation.Field()
    
    # Transaction Dispute
    create_transaction_dispute = CreateTransactionDisputeMutation.Field()
    update_transaction_dispute = UpdateTransactionDisputeMutation.Field()
    
    # Dispute Evidence
    create_dispute_evidence = CreateDisputeEvidenceMutation.Field()
    
    # System Account
    create_system_account = CreateSystemAccountMutation.Field()
    update_system_account = UpdateSystemAccountMutation.Field()
    delete_system_account = DeleteSystemAccountMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Accounting Journal
    "CreateDoubleEntryMutation",
    
    # Float Account
    "CreateFloatAccountMutation",
    "UpdateFloatAccountMutation",
    "DeleteFloatAccountMutation",
    
    # KYC Document
    "CreateKYCDocumentMutation",
    "UpdateKYCDocumentMutation",
    "DeleteKYCDocumentMutation",
    
    # KYC Document Verification
    "CreateKYCDocumentVerificationMutation",
    
    # Forex Limit
    "CreateForexLimitMutation",
    "UpdateForexLimitMutation",
    "DeleteForexLimitMutation",
    
    # Currency Wallet
    "CreateCurrencyWalletMutation",
    "UpdateCurrencyWalletMutation",
    "DeleteCurrencyWalletMutation",
    
    # Forex Transaction
    "CreateForexTransactionMutation",
    "UpdateForexTransactionMutation",
    
    # Transaction Dispute
    "CreateTransactionDisputeMutation",
    "UpdateTransactionDisputeMutation",
    
    # Dispute Evidence
    "CreateDisputeEvidenceMutation",
    
    # System Account
    "CreateSystemAccountMutation",
    "UpdateSystemAccountMutation",
    "DeleteSystemAccountMutation",
    
    # Registry
    "AccountingMutations",
]