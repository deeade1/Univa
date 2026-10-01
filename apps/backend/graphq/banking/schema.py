# apps/backend/graphq/banking/schema.py

"""
Banking GraphQL schema.

This module combines all banking queries and mutations into a unified schema.
"""

import graphene
from graphene import Node, ObjectType
from graphene_django.filter import DjangoFilterConnectionField
# ============================================================================
# QUERY IMPORTS - Core
# ============================================================================

from graphq.banking.types.core import (
    BankNode,
    AccountNode,
)

# ============================================================================
# QUERY IMPORTS - Security
# ============================================================================

from graphq.banking.types.security import (
    BankingSecurityNode,
    PhoneChangeRequestNode,
    FraudDetectionRuleNode,
    FraudAlertNode,
    AuditLogNode,
)

# ============================================================================
# QUERY IMPORTS - Payments
# ============================================================================

from graphq.banking.types.payments import (
    TransactionNode,
    PaymentStatNode,
    MoneyTransferNode,
    WalletNode,
)

# ============================================================================
# QUERY IMPORTS - Bill Payments
# ============================================================================

from graphq.banking.types.bill_payments import (
    BillCategoryNode,
    BillerNode,
    BillProviderNode,
    BillAccountNode,
    BillNode,
    BillPaymentNode,
    AirtimePurchaseNode,
    DataBundlePurchaseNode,
)

# ============================================================================
# QUERY IMPORTS - Cards
# ============================================================================

from graphq.banking.types.card import (
    CardBrandNode,
    VirtualCardNode,
    CardTransactionNode,
    PhysicalCardNode,
)

# ============================================================================
# QUERY IMPORTS - Compliance
# ============================================================================

from graphq.banking.types.compliance import (
    WebhookNode,
    WebhookDeliveryNode,
    CurrencyExchangeRateNode,
    ContactNode,
    ATMCardNode,
    ATMTransactionNode,
    CardIssuanceNode,
)

# ============================================================================
# QUERY IMPORTS - Accounting
# ============================================================================

from graphq.banking.types.accounting import (
    AccountingJournalNode,
    FloatAccountNode,
    KYCDocumentNode,
    KYCDocumentVerificationNode,
    ForexLimitNode,
    CurrencyWalletNode,
    ForexTransactionNode,
    TransactionDisputeNode,
    DisputeEvidenceNode,
    SystemAccountNode,
)

# ============================================================================
# QUERY IMPORTS - Integrations
# ============================================================================

from graphq.banking.types.integrations import (
    BankAPIIntegrationNode,
    APITransactionLogNode,
)

# ============================================================================
# QUERY IMPORTS - Investments
# ============================================================================

from graphq.banking.types.investments import (
    InvestmentProductNode,
    InvestmentNode,
    InvestmentEarningsNode,
)

# ============================================================================
# QUERY IMPORTS - Merchant
# ============================================================================

from graphq.banking.types.merchant import (
    MerchantNode,
    MerchantTransactionNode,
)

# ============================================================================
# QUERY IMPORTS - Payment Gateways
# ============================================================================

from graphq.banking.types.payment_gateways import (
    PaymentGatewayNode,
    USSDSessionNode,
    USSDOperationNode,
)

# ============================================================================
# QUERY IMPORTS - QR Payments
# ============================================================================

from graphq.banking.types.qr_payments import (
    QRCodeNode,
    QRTransactionNode,
)

# ============================================================================
# QUERY IMPORTS - Reconciliation
# ============================================================================

from graphq.banking.types.reconciliation import (
    ReconciliationRunNode,
    ReconciliationMatchNode,
    UnreconciledTransactionNode,
)

# ============================================================================
# QUERY IMPORTS - Regulatory
# ============================================================================

from graphq.banking.types.regulatory import (
    BVNVerificationNode,
    CBNReportNode,
)

# ============================================================================
# QUERY IMPORTS - Savings
# ============================================================================

from graphq.banking.types.savings import (
    SavingsGoalNode,
    SavingsTransactionNode,
    AutoSaveRuleNode,
)

# ============================================================================
# QUERY IMPORTS - Scheduled
# ============================================================================

from graphq.banking.types.scheduled import (
    ScheduledPaymentNode,
    CreditProductNode,
    SupportTicketNode,
    APIKeyNode,
    RemittanceProviderNode,
    InternationalTransferNode,
    ExchangeRateNode,
)

# ============================================================================
# QUERY IMPORTS - Insurance
# ============================================================================

from graphq.banking.types.insurance import (
    InsuranceProviderNode,
    InsuranceProductNode,
    InsurancePolicyNode,
    InsuranceClaimNode,
)




# ============================================================================
# QUERY CLASS
# ============================================================================

class BankingQueries(graphene.ObjectType):
    """Banking query type."""
    
    # Core
    bank = Node.Field(BankNode)
    banks = DjangoFilterConnectionField(BankNode)
    account = Node.Field(AccountNode)
    accounts = DjangoFilterConnectionField(AccountNode)
    
    # Security
    banking_security = Node.Field(BankingSecurityNode)
    banking_securities = DjangoFilterConnectionField(BankingSecurityNode)
    phone_change_request = Node.Field(PhoneChangeRequestNode)
    phone_change_requests = DjangoFilterConnectionField(PhoneChangeRequestNode)
    fraud_rule = Node.Field(FraudDetectionRuleNode)
    fraud_rules = DjangoFilterConnectionField(FraudDetectionRuleNode)
    fraud_alert = Node.Field(FraudAlertNode)
    fraud_alerts = DjangoFilterConnectionField(FraudAlertNode)
    audit_log = Node.Field(AuditLogNode)
    audit_logs = DjangoFilterConnectionField(AuditLogNode)
    
    # Payments
    transaction = Node.Field(TransactionNode)
    transactions = DjangoFilterConnectionField(TransactionNode)
    payment_stat = Node.Field(PaymentStatNode)
    payment_stats = DjangoFilterConnectionField(PaymentStatNode)
    money_transfer = Node.Field(MoneyTransferNode)
    money_transfers = DjangoFilterConnectionField(MoneyTransferNode)
    wallet = Node.Field(WalletNode)
    wallets = DjangoFilterConnectionField(WalletNode)
    
    # Bill Payments
    bill_category = Node.Field(BillCategoryNode)
    bill_categories = DjangoFilterConnectionField(BillCategoryNode)
    biller = Node.Field(BillerNode)
    billers = DjangoFilterConnectionField(BillerNode)
    bill_provider = Node.Field(BillProviderNode)
    bill_providers = DjangoFilterConnectionField(BillProviderNode)
    bill_account = Node.Field(BillAccountNode)
    bill_accounts = DjangoFilterConnectionField(BillAccountNode)
    bill = Node.Field(BillNode)
    bills = DjangoFilterConnectionField(BillNode)
    bill_payment = Node.Field(BillPaymentNode)
    bill_payments = DjangoFilterConnectionField(BillPaymentNode)
    airtime_purchase = Node.Field(AirtimePurchaseNode)
    airtime_purchases = DjangoFilterConnectionField(AirtimePurchaseNode)
    data_bundle_purchase = Node.Field(DataBundlePurchaseNode)
    data_bundle_purchases = DjangoFilterConnectionField(DataBundlePurchaseNode)
    
    # Cards
    card_brand = Node.Field(CardBrandNode)
    card_brands = DjangoFilterConnectionField(CardBrandNode)
    virtual_card = Node.Field(VirtualCardNode)
    virtual_cards = DjangoFilterConnectionField(VirtualCardNode)
    card_transaction = Node.Field(CardTransactionNode)
    card_transactions = DjangoFilterConnectionField(CardTransactionNode)
    physical_card = Node.Field(PhysicalCardNode)
    physical_cards = DjangoFilterConnectionField(PhysicalCardNode)
    
    # Compliance
    webhook = Node.Field(WebhookNode)
    webhooks = DjangoFilterConnectionField(WebhookNode)
    webhook_delivery = Node.Field(WebhookDeliveryNode)
    webhook_deliveries = DjangoFilterConnectionField(WebhookDeliveryNode)
    currency_exchange_rate = Node.Field(CurrencyExchangeRateNode)
    currency_exchange_rates = DjangoFilterConnectionField(CurrencyExchangeRateNode)
    contact = Node.Field(ContactNode)
    contacts = DjangoFilterConnectionField(ContactNode)
    atm_card = Node.Field(ATMCardNode)
    atm_cards = DjangoFilterConnectionField(ATMCardNode)
    atm_transaction = Node.Field(ATMTransactionNode)
    atm_transactions = DjangoFilterConnectionField(ATMTransactionNode)
    card_issuance = Node.Field(CardIssuanceNode)
    card_issuances = DjangoFilterConnectionField(CardIssuanceNode)
    
    # Accounting
    
    accounting_journal = Node.Field(AccountingJournalNode)
    accounting_journals = DjangoFilterConnectionField(AccountingJournalNode)
    float_account = Node.Field(FloatAccountNode)
    float_accounts = DjangoFilterConnectionField(FloatAccountNode)
    kyc_document = Node.Field(KYCDocumentNode)
    kyc_documents = DjangoFilterConnectionField(KYCDocumentNode)
    kyc_document_verification = Node.Field(KYCDocumentVerificationNode)
    kyc_document_verifications = DjangoFilterConnectionField(KYCDocumentVerificationNode)
    forex_limit = Node.Field(ForexLimitNode)
    forex_limits = DjangoFilterConnectionField(ForexLimitNode)
    currency_wallet = Node.Field(CurrencyWalletNode)
    currency_wallets = DjangoFilterConnectionField(CurrencyWalletNode)
    forex_transaction = Node.Field(ForexTransactionNode)
    forex_transactions = DjangoFilterConnectionField(ForexTransactionNode)
    transaction_dispute = Node.Field(TransactionDisputeNode)
    transaction_disputes = DjangoFilterConnectionField(TransactionDisputeNode)
    dispute_evidence = Node.Field(DisputeEvidenceNode)
    dispute_evidences = DjangoFilterConnectionField(DisputeEvidenceNode)
    system_account = Node.Field(SystemAccountNode)
    system_accounts = DjangoFilterConnectionField(SystemAccountNode)
    
    # Integrations
    bank_api_integration = Node.Field(BankAPIIntegrationNode)
    bank_api_integrations = DjangoFilterConnectionField(BankAPIIntegrationNode)
    api_transaction_log = Node.Field(APITransactionLogNode)
    api_transaction_logs = DjangoFilterConnectionField(APITransactionLogNode)
    
    # Investments
    investment_product = Node.Field(InvestmentProductNode)
    investment_products = DjangoFilterConnectionField(InvestmentProductNode)
    investment = Node.Field(InvestmentNode)
    investments = DjangoFilterConnectionField(InvestmentNode)
    investment_earnings = Node.Field(InvestmentEarningsNode)
    investment_earnings_list = DjangoFilterConnectionField(InvestmentEarningsNode)
    
    # Merchant
    merchant = Node.Field(MerchantNode)
    merchants = DjangoFilterConnectionField(MerchantNode)
    merchant_transaction = Node.Field(MerchantTransactionNode)
    merchant_transactions = DjangoFilterConnectionField(MerchantTransactionNode)
    
    # Payment Gateways
    payment_gateway = Node.Field(PaymentGatewayNode)
    payment_gateways = DjangoFilterConnectionField(PaymentGatewayNode)
    ussd_session = Node.Field(USSDSessionNode)
    ussd_sessions = DjangoFilterConnectionField(USSDSessionNode)
    ussd_operation = Node.Field(USSDOperationNode)
    ussd_operations = DjangoFilterConnectionField(USSDOperationNode)
    
    # QR Payments
    qr_code = Node.Field(QRCodeNode)
    qr_codes = DjangoFilterConnectionField(QRCodeNode)
    qr_transaction = Node.Field(QRTransactionNode)
    qr_transactions = DjangoFilterConnectionField(QRTransactionNode)
    
    # Reconciliation
    reconciliation_run = Node.Field(ReconciliationRunNode)
    reconciliation_runs = DjangoFilterConnectionField(ReconciliationRunNode)
    reconciliation_match = Node.Field(ReconciliationMatchNode)
    reconciliation_matches = DjangoFilterConnectionField(ReconciliationMatchNode)
    unreconciled_transaction = Node.Field(UnreconciledTransactionNode)
    unreconciled_transactions = DjangoFilterConnectionField(UnreconciledTransactionNode)
    
    # Regulatory
    bvn_verification = Node.Field(BVNVerificationNode)
    bvn_verifications = DjangoFilterConnectionField(BVNVerificationNode)
    cbn_report = Node.Field(CBNReportNode)
    cbn_reports = DjangoFilterConnectionField(CBNReportNode)
    
    # Savings
    savings_goal = Node.Field(SavingsGoalNode)
    savings_goals = DjangoFilterConnectionField(SavingsGoalNode)
    savings_transaction = Node.Field(SavingsTransactionNode)
    savings_transactions = DjangoFilterConnectionField(SavingsTransactionNode)
    auto_save_rule = Node.Field(AutoSaveRuleNode)
    auto_save_rules = DjangoFilterConnectionField(AutoSaveRuleNode)
    
    # Scheduled
    scheduled_payment = Node.Field(ScheduledPaymentNode)
    scheduled_payments = DjangoFilterConnectionField(ScheduledPaymentNode)
    credit_product = Node.Field(CreditProductNode)
    credit_products = DjangoFilterConnectionField(CreditProductNode)
    support_ticket = Node.Field(SupportTicketNode)
    support_tickets = DjangoFilterConnectionField(SupportTicketNode)
    api_key = Node.Field(APIKeyNode)
    api_keys = DjangoFilterConnectionField(APIKeyNode)
    remittance_provider = Node.Field(RemittanceProviderNode)
    remittance_providers = DjangoFilterConnectionField(RemittanceProviderNode)
    international_transfer = Node.Field(InternationalTransferNode)
    international_transfers = DjangoFilterConnectionField(InternationalTransferNode)
    exchange_rate = Node.Field(ExchangeRateNode)
    exchange_rates = DjangoFilterConnectionField(ExchangeRateNode)
    
    # Insurance
    insurance_provider = Node.Field(InsuranceProviderNode)
    insurance_providers = DjangoFilterConnectionField(InsuranceProviderNode)
    insurance_product = Node.Field(InsuranceProductNode)
    insurance_products = DjangoFilterConnectionField(InsuranceProductNode)
    insurance_policy = Node.Field(InsurancePolicyNode)
    insurance_policies = DjangoFilterConnectionField(InsurancePolicyNode)
    insurance_claim = Node.Field(InsuranceClaimNode)
    insurance_claims = DjangoFilterConnectionField(InsuranceClaimNode)


class SecurityQueries(graphene.ObjectType):
    """Security query type."""
    
    banking_security = Node.Field(BankingSecurityNode)
    banking_securities = DjangoFilterConnectionField(BankingSecurityNode)
    
    phone_change_request = Node.Field(PhoneChangeRequestNode)
    phone_change_requests = DjangoFilterConnectionField(PhoneChangeRequestNode)
    
    fraud_rule = Node.Field(FraudDetectionRuleNode)
    fraud_rules = DjangoFilterConnectionField(FraudDetectionRuleNode)
    
    fraud_alert = Node.Field(FraudAlertNode)
    fraud_alerts = DjangoFilterConnectionField(FraudAlertNode)
    
    audit_log = Node.Field(AuditLogNode)
    audit_logs = DjangoFilterConnectionField(AuditLogNode)



# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "BankingQuery",
    "SecurityQueries",
]