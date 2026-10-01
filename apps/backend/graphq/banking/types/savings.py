# ============================================================================
# SAVINGS TYPES
# ============================================================================

import graphene
from graphene import  Decimal,  Int, String, relay
from graphene_django import DjangoObjectType



from banking.models.savings import AutoSaveRule, SavingsGoal, SavingsTransaction


class SavingsGoalNode(DjangoObjectType):
    """Savings goal node type."""
    goal_type_display = graphene.String()
    savings_method_display = graphene.String()
    current_amount = graphene.Decimal()
    interest_earned = graphene.Decimal()
    formatted_target_amount = graphene.String()
    formatted_current_amount = graphene.String()
    progress_percentage = graphene.Float()
    days_remaining = graphene.Int()
    daily_savings_needed = graphene.Decimal()
    is_completed_display = graphene.String()
    is_active_display = graphene.String()
    is_locked_display = graphene.String()

    class Meta:
        model = SavingsGoal
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'goal_type': ['exact'],
            'savings_method': ['exact'],
            'is_active': ['exact'],
            'is_completed': ['exact'],
            'is_locked': ['exact'],
        }

    def resolve_goal_type_display(self, info):
        return dict(self.GOAL_TYPES).get(self.goal_type, self.goal_type)

    def resolve_savings_method_display(self, info):
        return dict(self.SAVINGS_METHODS).get(self.savings_method, self.savings_method)

    def resolve_formatted_target_amount(self, info):
        return f"₦{self.target_amount:,.2f}"

    def resolve_formatted_current_amount(self, info):
        return f"₦{self.current_amount:,.2f}"

    def resolve_progress_percentage(self, info):
        return self.progress_percentage

    def resolve_days_remaining(self, info):
        return self.days_remaining

    def resolve_daily_savings_needed(self, info):
        return self.daily_savings_needed

    def resolve_is_completed_display(self, info):
        return "Completed" if self.is_completed else "In Progress"

    def resolve_is_active_display(self, info):
        return "Active" if self.is_active else "Inactive"

    def resolve_is_locked_display(self, info):
        return "Locked" if self.is_locked else "Unlocked"
    
    def resolve_current_amount(self, info):
        return self.current_amount

    def resolve_interest_earned(self, info):
        return self.interest_earned


class SavingsTransactionNode(DjangoObjectType):
    """Savings transaction node type."""
    formatted_amount = graphene.String()
    formatted_balance_before = graphene.String()
    formatted_balance_after = graphene.String()
    transaction_type_display = graphene.String()
    status_display = graphene.String()

    class Meta:
        model = SavingsTransaction
        interfaces = (relay.Node,)
        filter_fields = {
            'goal': ['exact'],
            'transaction_type': ['exact'],
            'status': ['exact'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_formatted_balance_before(self, info):
        return f"₦{self.balance_before:,.2f}"

    def resolve_formatted_balance_after(self, info):
        return f"₦{self.balance_after:,.2f}"

    def resolve_transaction_type_display(self, info):
        return dict(self.TRANSACTION_TYPES).get(self.transaction_type, self.transaction_type)

    def resolve_status_display(self, info):
        return self.status


class AutoSaveRuleNode(DjangoObjectType):
    """Auto-save rule node type."""
    rule_type_display = graphene.String()
    formatted_total_amount_saved = graphene.String()
    is_active_display = graphene.String()
    total_amount_saved = graphene.Decimal()

    class Meta:
        model = AutoSaveRule
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'goal': ['exact'],
            'rule_type': ['exact'],
            'is_active': ['exact'],
        }

    def resolve_rule_type_display(self, info):
        return dict(self.RULE_TYPES).get(self.rule_type, self.rule_type)

    def resolve_formatted_total_amount_saved(self, info):
        return f"₦{self.total_amount_saved:,.2f}"

    def resolve_is_active_display(self, info):
        return "Active" if self.is_active else "Inactive"
    
    def resolve_total_amount_saved(self, info):
        return self.total_amount_saved
    

