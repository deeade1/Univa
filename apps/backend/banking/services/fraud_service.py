# apps/backend/banking/services/fraud_service.py
import logging
from datetime import timedelta

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from ..models.payments import Transaction
from ..models.security import FraudAlert, FraudDetectionRule

logger = logging.getLogger(__name__)

class FraudDetectionService:
    def analyze_transaction(self, transaction_data):
        """Analyze transaction for fraud risks"""
        risks = []
        
        # Check all active fraud rules
        active_rules = FraudDetectionRule.objects.filter(is_active=True)
        
        for rule in active_rules:
            if self._evaluate_rule(rule, transaction_data):
                risk = {
                    'rule': rule.name,
                    'type': rule.rule_type,
                    'action': rule.action,
                    'threshold': rule.threshold,
                    'detected_value': self._get_detected_value(rule, transaction_data)
                }
                risks.append(risk)
                
                # Create fraud alert
                self._create_fraud_alert(rule, transaction_data, risk['detected_value'])
        
        return risks

    def _evaluate_rule(self, rule, transaction_data):
        """Evaluate if a transaction triggers a fraud rule"""
        if rule.rule_type == FraudDetectionRule.RuleType.TRANSACTION_AMOUNT:
            return self._check_amount_rule(rule, transaction_data)
        elif rule.rule_type == FraudDetectionRule.RuleType.FREQUENCY:
            return self._check_frequency_rule(rule, transaction_data)
        elif rule.rule_type == FraudDetectionRule.RuleType.BEHAVIORAL:
            return self._check_behavioral_rule(rule, transaction_data)
        
        return False

    def _check_amount_rule(self, rule, transaction_data):
        """Check for unusual transaction amounts"""
        user = transaction_data.get('sender')
        amount = transaction_data.get('amount')
        
        # Get user's typical transaction pattern
        recent_transactions = Transaction.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=30),
            status=Transaction.COMPLETED
        )
        
        avg_amount = recent_transactions.aggregate(avg=Avg('amount'))['avg'] or 0
        max_amount = recent_transactions.aggregate(max=Max('amount'))['max'] or 0
        
        # Check if amount is significantly higher than average
        if avg_amount > 0 and amount > avg_amount * rule.threshold:
            return True
        
        return amount > rule.threshold

    def _check_frequency_rule(self, rule, transaction_data):
        """Check for high-frequency transactions"""
        user = transaction_data.get('sender')
        
        # Count transactions in last hour
        hour_ago = timezone.now() - timedelta(hours=1)
        recent_count = Transaction.objects.filter(
            user=user,
            created_at__gte=hour_ago,
            status=Transaction.COMPLETED
        ).count()
        
        return recent_count >= rule.threshold

    def _check_behavioral_rule(self, rule, transaction_data):
        """Check for behavioral anomalies"""
        # Implement machine learning based behavioral analysis
        # This is a simplified version
        user = transaction_data.get('sender')
        amount = transaction_data.get('amount')
        
        # Get user's transaction time pattern
        current_hour = timezone.now().hour
        typical_hours = self._get_typical_transaction_hours(user)
        
        # Check if transaction is outside typical hours
        if typical_hours and current_hour not in typical_hours:
            return amount > rule.threshold * 0.5  # Lower threshold for unusual times
        
        return False

    def _get_typical_transaction_hours(self, user):
        """Get user's typical transaction hours"""
        transactions = Transaction.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        if transactions.count() < 10:
            return None
            
        # Return hours where 80% of transactions occur
        hour_counts = transactions.annotate(hour=ExtractHour('created_at')).values('hour').annotate(count=Count('id'))
        total = sum(item['count'] for item in hour_counts)
        typical_hours = [item['hour'] for item in hour_counts if item['count'] / total > 0.1]
        
        return typical_hours

    def _get_detected_value(self, rule, transaction_data):
        """Get the value that triggered the rule"""
        if rule.rule_type == FraudDetectionRule.RuleType.TRANSACTION_AMOUNT:
            return transaction_data.get('amount', 0)
        elif rule.rule_type == FraudDetectionRule.RuleType.FREQUENCY:
            user = transaction_data.get('sender')
            hour_ago = timezone.now() - timedelta(hours=1)
            return Transaction.objects.filter(
                user=user,
                created_at__gte=hour_ago
            ).count()
        
        return 0

    def _create_fraud_alert(self, rule, transaction_data, detected_value):
        """Create a fraud alert record"""
        FraudAlert.objects.create(
            rule=rule,
            user=transaction_data.get('sender'),
            transaction_reference=transaction_data.get('reference'),
            detected_value=detected_value,
            evidence_data=transaction_data,
            status=FraudAlert.AlertStatus.OPEN
        )