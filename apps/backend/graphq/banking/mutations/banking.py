import graphene
from graphene import relay, ObjectType

# ============================================================================
# MUTATION IMPORTS
# ============================================================================

from graphq.banking.mutations.core import CoreMutations
from graphq.banking.mutations.security import SecurityMutations
from graphq.banking.mutations.payments import PaymentsMutations
from graphq.banking.mutations.bill_payments import BillPaymentMutations
from graphq.banking.mutations.card import CardMutations
from graphq.banking.mutations.compliance import ComplianceMutations
from graphq.banking.mutations.accounting import AccountingMutations
from graphq.banking.mutations.integrations import IntegrationsMutations
from graphq.banking.mutations.investments import InvestmentsMutations
from graphq.banking.mutations.merchant import MerchantMutations
from graphq.banking.mutations.payment_gateways import PaymentGatewayMutations
from graphq.banking.mutations.qr_payments import QRMutations
from graphq.banking.mutations.reconciliation import ReconciliationMutations
from graphq.banking.mutations.regulatory import RegulatoryMutations
from graphq.banking.mutations.savings import SavingsMutations
from graphq.banking.mutations.scheduled import ScheduledMutations
from graphq.banking.mutations.insurance import InsuranceMutations




# ============================================================================
# MUTATION CLASS
# ============================================================================

class BankingMutations(
    CoreMutations,
    SecurityMutations,
    PaymentsMutations,
    BillPaymentMutations,
    CardMutations,
    ComplianceMutations,
    AccountingMutations,
    IntegrationsMutations,
    InvestmentsMutations,
    MerchantMutations,
    PaymentGatewayMutations,
    QRMutations,
    ReconciliationMutations,
    RegulatoryMutations,
    SavingsMutations,
    ScheduledMutations,
    InsuranceMutations,
    graphene.ObjectType,
):
    """Banking mutations type combining all mutation classes."""
    pass

