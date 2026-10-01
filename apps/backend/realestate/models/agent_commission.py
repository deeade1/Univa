from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from .commission import CommissionPlan

class AgentCommission(models.Model):
    agent = models.ForeignKey("Agent", on_delete=models.CASCADE, related_name="commissions")
    transaction = models.ForeignKey("Transaction", on_delete=models.CASCADE, related_name="commissions_transaction")
    commission_plan = models.ForeignKey(
        CommissionPlan,
        on_delete=models.PROTECT,
        related_name="agent_commissions"
    )
    calculated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['agent', 'paid_date'], name='commission_agent_paid_idx'),
            models.Index(fields=['transaction'], name='commission_transaction_idx'),
        ]

    def __str__(self):
        return f"Commission: {self.agent} - ${self.calculated_amount}"