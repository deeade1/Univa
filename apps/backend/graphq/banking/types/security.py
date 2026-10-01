# apps/backend/graphq/banking/types/security.py

"""
GraphQL types for Banking security models.

This module contains node types for:
    - BankingSecurity: PIN management for banking users
    - PhoneChangeRequest: Phone number change with OTP
    - FraudDetectionRule: Fraud detection rules
    - FraudAlert: Fraud alerts
    - AuditLog: Banking audit trail
"""

import graphene
from django.utils import timezone
from graphene_django import DjangoObjectType
from graphene import relay

from banking.models.security import (
    BankingSecurity,
    PhoneChangeRequest,
    FraudDetectionRule,
    FraudAlert,
    AuditLog,
)


# ============================================================================
# BANKING SECURITY NODE
# ============================================================================

class BankingSecurityNode(DjangoObjectType):
    """Banking security node type."""
    
    has_pin = graphene.Boolean()
    is_pin_locked = graphene.Boolean()
    remaining_lockout_minutes = graphene.Int()
    formatted_pin_set_at = graphene.String()
    
    class Meta:
        model = BankingSecurity
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'pin_attempts': ['exact', 'gt', 'gte', 'lt', 'lte'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }
        fields = '__all__'

    def resolve_has_pin(self, info):
        return self.has_pin

    def resolve_is_pin_locked(self, info):
        return self.is_pin_locked

    def resolve_remaining_lockout_minutes(self, info):
        return self.remaining_lockout_minutes

    def resolve_formatted_pin_set_at(self, info):
        if self.pin_set_at:
            return self.pin_set_at.strftime("%Y-%m-%d %H:%M:%S")
        return None


# ============================================================================
# PHONE CHANGE REQUEST NODE
# ============================================================================

class PhoneChangeRequestNode(DjangoObjectType):
    """Phone change request node type."""
    
    attempts_left = graphene.Int()
    cooldown_remaining = graphene.Int()
    is_locked = graphene.Boolean()
    formatted_otp_sent_at = graphene.String()
    formatted_created_at = graphene.String()
    can_resend_otp = graphene.Boolean()
    
    class Meta:
        model = PhoneChangeRequest
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'verified': ['exact'],
            'new_phone': ['exact', 'icontains'],
            'old_phone': ['exact', 'icontains'],
            'otp_attempts': ['exact', 'gt', 'gte', 'lt', 'lte'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }
        fields = '__all__'

    def resolve_attempts_left(self, info):
        return max(PhoneChangeRequest.MAX_ATTEMPTS - self.otp_attempts, 0)

    def resolve_cooldown_remaining(self, info):
        if not self.otp_sent_at:
            return 0
        delta = (timezone.now() - self.otp_sent_at).total_seconds()
        remaining = PhoneChangeRequest.OTP_RESEND_INTERVAL - delta
        return max(int(remaining), 0)

    def resolve_is_locked(self, info):
        return bool(self.locked_until and timezone.now() < self.locked_until)

    def resolve_formatted_otp_sent_at(self, info):
        if self.otp_sent_at:
            return self.otp_sent_at.strftime("%Y-%m-%d %H:%M:%S")
        return None

    def resolve_formatted_created_at(self, info):
        return self.created_at.strftime("%Y-%m-%d %H:%M:%S")

    def resolve_can_resend_otp(self, info):
        if not self.otp_sent_at:
            return True
        if self.is_locked:
            return False
        delta = (timezone.now() - self.otp_sent_at).total_seconds()
        return delta >= PhoneChangeRequest.OTP_RESEND_INTERVAL


# ============================================================================
# FRAUD DETECTION RULE NODE
# ============================================================================

class FraudDetectionRuleNode(DjangoObjectType):
    """Fraud detection rule node type."""
    
    formatted_threshold = graphene.String()
    action_display = graphene.String()
    rule_type_display = graphene.String()
    is_active_display = graphene.String()
    formatted_created_at = graphene.String()
    formatted_updated_at = graphene.String()
    
    class Meta:
        model = FraudDetectionRule
        interfaces = (relay.Node,)
        filter_fields = {
            'rule_type': ['exact'],
            'is_active': ['exact'],
            'action': ['exact'],
            'name': ['exact', 'icontains'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
        }
        fields = '__all__'

    def resolve_formatted_threshold(self, info):
        return f"{self.threshold:,.2f}"

    def resolve_action_display(self, info):
        return self.get_action_display()

    def resolve_rule_type_display(self, info):
        return self.get_rule_type_display()

    def resolve_is_active_display(self, info):
        return "Active" if self.is_active else "Inactive"

    def resolve_formatted_created_at(self, info):
        return self.created_at.strftime("%Y-%m-%d %H:%M:%S")

    def resolve_formatted_updated_at(self, info):
        return self.updated_at.strftime("%Y-%m-%d %H:%M:%S")


# ============================================================================
# FRAUD ALERT NODE
# ============================================================================

class FraudAlertNode(DjangoObjectType):
    """Fraud alert node type."""
    
    formatted_detected_value = graphene.String()
    time_since_created = graphene.String()
    is_resolved = graphene.Boolean()
    status_display = graphene.String()
    formatted_created_at = graphene.String()
    formatted_updated_at = graphene.String()
    can_investigate = graphene.Boolean()
    
    class Meta:
        model = FraudAlert
        interfaces = (relay.Node,)
        filter_fields = {
            'status': ['exact'],
            'rule': ['exact'],
            'user': ['exact'],
            'created_at': ['exact', 'gt', 'gte', 'lt', 'lte'],
            'transaction_reference': ['exact', 'icontains'],
        }
        fields = '__all__'

    def resolve_formatted_detected_value(self, info):
        return f"{self.detected_value:,.2f}"

    def resolve_time_since_created(self, info):
        from django.utils.timesince import timesince
        return timesince(self.created_at)

    def resolve_is_resolved(self, info):
        return self.status in ['RESOLVED', 'FALSE_POSITIVE']

    def resolve_status_display(self, info):
        return self.get_status_display()

    def resolve_formatted_created_at(self, info):
        return self.created_at.strftime("%Y-%m-%d %H:%M:%S")

    def resolve_formatted_updated_at(self, info):
        return self.updated_at.strftime("%Y-%m-%d %H:%M:%S")

    def resolve_can_investigate(self, info):
        return self.status in ['OPEN', 'INVESTIGATING']


# ============================================================================
# AUDIT LOG NODE
# ============================================================================

class AuditLogNode(DjangoObjectType):
    """Audit log node type."""
    
    action_display = graphene.String()
    formatted_timestamp = graphene.String()
    time_since = graphene.String()
    resource_type_display = graphene.String()
    
    class Meta:
        model = AuditLog
        interfaces = (relay.Node,)
        filter_fields = {
            'user': ['exact'],
            'action': ['exact'],
            'resource_type': ['exact', 'icontains'],
            'timestamp': ['exact', 'gt', 'gte', 'lt', 'lte'],
            'ip_address': ['exact', 'icontains'],
        }
        fields = '__all__'

    def resolve_action_display(self, info):
        return dict(self.ACTION_CHOICES).get(self.action, self.action)

    def resolve_formatted_timestamp(self, info):
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def resolve_time_since(self, info):
        from django.utils.timesince import timesince
        return timesince(self.timestamp)

    def resolve_resource_type_display(self, info):
        return self.resource_type


# ============================================================================
# QUERY TYPE
# ============================================================================

class SecurityQuery(graphene.ObjectType):
    """Security query type."""
    
    banking_security = relay.Node.Field(BankingSecurityNode)
    banking_securities = relay.ConnectionField(BankingSecurityNode)
    
    phone_change_request = relay.Node.Field(PhoneChangeRequestNode)
    phone_change_requests = relay.ConnectionField(PhoneChangeRequestNode)
    
    fraud_rule = relay.Node.Field(FraudDetectionRuleNode)
    fraud_rules = relay.ConnectionField(FraudDetectionRuleNode)
    
    fraud_alert = relay.Node.Field(FraudAlertNode)
    fraud_alerts = relay.ConnectionField(FraudAlertNode)
    
    audit_log = relay.Node.Field(AuditLogNode)
    audit_logs = relay.ConnectionField(AuditLogNode)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "BankingSecurityNode",
    "PhoneChangeRequestNode",
    "FraudDetectionRuleNode",
    "FraudAlertNode",
    "AuditLogNode",
    "SecurityQuery",
]