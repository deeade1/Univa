# ============================================================================
# BILL PAYMENTS TYPES
# ============================================================================
import graphene
from graphene import String, relay
from graphene_django import DjangoObjectType


from banking.models.bill_payments import (
    Bill,
    BillAccount,
    BillCategory,
    Biller,
    BillProvider,
    DataBundlePurchase,
    BillPayment,
    AirtimePurchase
)

class BillCategoryNode(DjangoObjectType):
    """Bill category node type."""

    class Meta:
        model = BillCategory
        interfaces = (relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains'],
            'slug': ['exact'],
            'is_active': ['exact'],
        }


class BillerNode(DjangoObjectType):
    """Biller node type."""
    formatted_fee_percentage = graphene.String()
    formatted_fee_fixed = graphene.String()
    formatted_min_amount = graphene.String()
    formatted_max_amount = graphene.String()

    class Meta:
        model = Biller
        interfaces = (relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains'],
            'slug': ['exact'],
            'code': ['exact'],
            'category': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_formatted_fee_percentage(self, info):
        return f"{self.fee_percentage}%"

    def resolve_formatted_fee_fixed(self, info):
        return f"₦{self.fee_fixed:,.2f}"

    def resolve_formatted_min_amount(self, info):
        return f"₦{self.min_amount:,.2f}"

    def resolve_formatted_max_amount(self, info):
        if self.max_amount:
            return f"₦{self.max_amount:,.2f}"
        return "Unlimited"


class BillProviderNode(DjangoObjectType):
    """Bill provider node type."""
    provider_type_display = graphene.String()

    class Meta:
        model = BillProvider
        interfaces = (relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains'],
            'provider_type': ['exact'],
            'provider_code': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_provider_type_display(self, info):
        return self.get_provider_type_display()


class BillAccountNode(DjangoObjectType):
    """Bill account node type."""
    is_validated_display = graphene.String()

    class Meta:
        model = BillAccount
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'provider': ['exact'],
            'account_number': ['exact'],
            'is_validated': ['exact'],
        }

    def resolve_is_validated_display(self, info):
        return "Validated" if self.is_validated else "Pending Validation"


class BillNode(DjangoObjectType):
    """Bill node type."""
    formatted_total_amount = graphene.String()
    formatted_outstanding_amount = graphene.String()
    status_display = graphene.String()
    is_overdue = graphene.Boolean()
    is_paid = graphene.Boolean()

    class Meta:
        model = Bill
        interfaces = (relay.Node,)
        filter_fields = {
            'bill_account': ['exact'],
            'status': ['exact'],
            'due_date': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_formatted_total_amount(self, info):
        return f"₦{self.total_amount:,.2f}"

    def resolve_formatted_outstanding_amount(self, info):
        return f"₦{self.outstanding_amount:,.2f}"

    def resolve_status_display(self, info):
        return dict(self.BILL_STATUS).get(self.status, self.status)

    def resolve_is_overdue(self, info):
        return self.status == "OVERDUE"

    def resolve_is_paid(self, info):
        return self.status == "PAID"


class BillPaymentNode(DjangoObjectType):
    """Bill payment node type."""
    formatted_amount = graphene.String()
    formatted_fee = graphene.String()
    formatted_total_amount = graphene.String()
    status_display = graphene.String()
    bill_type_display = graphene.String()

    class Meta:
        model = BillPayment
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'bill_type': ['exact'],
            'status': ['exact'],
            'provider': ['exact', 'icontains'],
            'biller': ['exact'],
            'reference': ['exact'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_formatted_fee(self, info):
        return f"₦{self.fee:,.2f}"

    def resolve_formatted_total_amount(self, info):
        return f"₦{self.total_amount:,.2f}"

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def resolve_bill_type_display(self, info):
        return dict(self.BILL_TYPES).get(self.bill_type, self.bill_type)


class AirtimePurchaseNode(DjangoObjectType):
    """Airtime purchase node type."""
    formatted_amount = graphene.String()
    formatted_fee = graphene.String()
    formatted_total_amount = graphene.String()
    operator_display = graphene.String()
    status_display = graphene.String()

    class Meta:
        model = AirtimePurchase
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'operator': ['exact'],
            'status': ['exact'],
            'phone_number': ['exact'],
            'reference': ['exact'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_formatted_fee(self, info):
        return f"₦{self.fee:,.2f}"

    def resolve_formatted_total_amount(self, info):
        return f"₦{self.total_amount:,.2f}"

    def resolve_operator_display(self, info):
        return dict(self.OPERATORS).get(self.operator, self.operator)

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


class DataBundlePurchaseNode(DjangoObjectType):
    """Data bundle purchase node type."""
    formatted_price = graphene.String()
    data_type_display = graphene.String()
    status_display = graphene.String()

    class Meta:
        model = DataBundlePurchase
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'operator': ['exact'],
            'status': ['exact'],
            'phone_number': ['exact'],
        }

    def resolve_formatted_price(self, info):
        return f"₦{self.price:,.2f}"

    def resolve_data_type_display(self, info):
        return dict(self.DATA_TYPES).get(self.data_type, self.data_type)

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

