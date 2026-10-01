# ============================================================================
# ACCOUNTING TYPES
# ============================================================================
import graphene
from graphene import Decimal, String, relay
from graphene_django import DjangoObjectType
from django.utils import timezone



from banking.models.accounting import (
    AccountingManager,  
    TransactionDispute,
    AccountingJournal,
    FloatAccount,
    KYCDocument,
    KYCDocumentVerification,
    ForexLimit,
    CurrencyWallet,
    ForexTransaction,
    DisputeEvidence,
    SystemAccount
)


class AccountingJournalNode(DjangoObjectType):
    """Accounting journal node type."""
    formatted_total_amount = graphene.String()
    journal_type_display = graphene.String()
    balanced_status = graphene.String()
    total_debit = graphene.Decimal()
    total_credit = graphene.Decimal()
    is_balanced_computed = graphene.Boolean()

    class Meta:
        model = AccountingJournal
        interfaces = (relay.Node,)
        filter_fields = {
            'journal_type': ['exact'],
            'is_balanced': ['exact'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_formatted_total_amount(self, info):
        return f"₦{self.total_amount:,.2f}"

    def resolve_journal_type_display(self, info):
        return dict(self.JOURNAL_TYPES).get(self.journal_type, self.journal_type)

    def resolve_balanced_status(self, info):
        return "Balanced" if self.is_balanced else "Pending"

    def resolve_total_debit(self, info):
        debit, _ = self.calculate_totals()
        return debit

    def resolve_total_credit(self, info):
        _, credit = self.calculate_totals()
        return credit

    def resolve_is_balanced_computed(self, info):
        return self.verify_balance()


class FloatAccountNode(DjangoObjectType):
    """Float account node type."""
    formatted_statement_balance = graphene.String()
    formatted_last_reconciled_balance = graphene.String()
    discrepancy = graphene.Decimal()
    bank_name_display = graphene.String()

    class Meta:
        model = FloatAccount
        interfaces = (relay.Node,)
        filter_fields = {
            'bank_name': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_formatted_statement_balance(self, info):
        if self.statement_balance:
            return f"₦{self.statement_balance:,.2f}"
        return "N/A"

    def resolve_formatted_last_reconciled_balance(self, info):
        if self.last_reconciled_balance:
            return f"₦{self.last_reconciled_balance:,.2f}"
        return "N/A"

    def resolve_discrepancy(self, info):
        return self.discrepancy()

    def resolve_bank_name_display(self, info):
        return dict(self.BANK_CHOICES).get(self.bank_name, self.bank_name)


class KYCDocumentNode(DjangoObjectType):
    """KYC document node type."""
    status_display = graphene.String()
    document_url = graphene.String()
    is_expired = graphene.Boolean()

    class Meta:
        model = KYCDocument
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'document_type': ['exact'],
            'status': ['exact'],
            'country': ['exact'],
        }

    def resolve_status_display(self, info):
        return self.status

    def resolve_document_url(self, info):
        if self.document_file and hasattr(self.document_file, 'url'):
            return self.document_file.url
        return None

    def resolve_is_expired(self, info):
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False


class KYCDocumentVerificationNode(DjangoObjectType):
    """KYC document verification node type."""
    status_display = graphene.String()
    verification_type_display = graphene.String()

    class Meta:
        model = KYCDocumentVerification
        interfaces = (relay.Node,)
        filter_fields = {
            'document': ['exact'],
            'status': ['exact'],
            'verification_type': ['exact'],
        }

    def resolve_status_display(self, info):
        return self.status

    def resolve_verification_type_display(self, info):
        return self.verification_type


class ForexLimitNode(DjangoObjectType):
    """Forex limit node type."""
    formatted_daily_limit = graphene.String()
    formatted_monthly_limit = graphene.String()

    class Meta:
        model = ForexLimit
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'currency_pair': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_formatted_daily_limit(self, info):
        return f"₦{self.daily_limit:,.2f}"

    def resolve_formatted_monthly_limit(self, info):
        return f"₦{self.monthly_limit:,.2f}"


class CurrencyWalletNode(DjangoObjectType):
    """Currency wallet node type."""
    formatted_balance = graphene.String()
    is_active_display = graphene.String()

    class Meta:
        model = CurrencyWallet
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'currency': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_formatted_balance(self, info):
        balance = self.balance
        return f"₦{balance:,.2f}"

    def resolve_is_active_display(self, info):
        return "Active" if self.is_active else "Inactive"


class ForexTransactionNode(DjangoObjectType):
    """Forex transaction node type."""
    formatted_source_amount = graphene.String()
    formatted_target_amount = graphene.String()
    formatted_fee = graphene.String()
    transaction_type_display = graphene.String()

    class Meta:
        model = ForexTransaction
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'transaction_type': ['exact'],
            'status': ['exact'],
            'source_currency': ['exact'],
            'target_currency': ['exact'],
        }

    def resolve_formatted_source_amount(self, info):
        return f"{self.source_amount:,.2f} {self.source_currency}"

    def resolve_formatted_target_amount(self, info):
        return f"{self.target_amount:,.2f} {self.target_currency}"

    def resolve_formatted_fee(self, info):
        return f"₦{self.fee:,.2f}"

    def resolve_transaction_type_display(self, info):
        return dict(self.TRANSACTION_TYPES).get(self.transaction_type, self.transaction_type)


class TransactionDisputeNode(DjangoObjectType):
    """Transaction dispute node type."""
    formatted_requested_amount = graphene.String()
    formatted_refund_amount = graphene.String()
    status_display = graphene.String()
    priority_display = graphene.String()

    class Meta:
        model = TransactionDispute
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'transaction': ['exact'],
            'case_number': ['exact', 'icontains'],
            'dispute_type': ['exact'],
            'status': ['exact'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_formatted_requested_amount(self, info):
        return f"₦{self.requested_amount:,.2f}"

    def resolve_formatted_refund_amount(self, info):
        if self.refund_amount:
            return f"₦{self.refund_amount:,.2f}"
        return "N/A"

    def resolve_status_display(self, info):
        return self.status

    def resolve_priority_display(self, info):
        return self.priority


class DisputeEvidenceNode(DjangoObjectType):
    """Dispute evidence node type."""
    evidence_type_display = graphene.String()
    file_url = graphene.String()

    class Meta:
        model = DisputeEvidence
        interfaces = (relay.Node,)
        filter_fields = {
            'dispute': ['exact'],
            'evidence_type': ['exact'],
        }

    def resolve_evidence_type_display(self, info):
        return self.evidence_type

    def resolve_file_url(self, info):
        if self.file and hasattr(self.file, 'url'):
            return self.file.url
        return None


class SystemAccountNode(DjangoObjectType):
    """System account node type."""
    purpose_display = graphene.String()

    class Meta:
        model = SystemAccount
        interfaces = (relay.Node,)
        filter_fields = {
            'purpose': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_purpose_display(self, info):
        return dict(self.PURPOSE_CHOICES).get(self.purpose, self.purpose)

