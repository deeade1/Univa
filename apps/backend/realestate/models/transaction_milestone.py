# apps/backend/realestate/models/transaction_milestone.py

"""
Transaction Milestone model for real estate.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TransactionMilestone(models.Model):
    transaction = models.ForeignKey("Transaction", on_delete=models.CASCADE, related_name="milestones")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    required = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    documents = models.ManyToManyField('Document', related_name="transaction_milestones", blank=True)

    class Meta:
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["transaction", "order"], name="milestone_transac_order_idx"),
            models.Index(fields=["transaction", "required", "completed_date"], name="milestone_completion_idx"),
            models.Index(fields=["due_date", "completed_date"], name="milestone_due_complet_idx"),
        ]

    def __str__(self):
        return f"{self.name} - Due: {self.due_date} - {'Completed' if self.is_completed else 'Pending'}"

    def clean(self):
        for doc in self.documents.all():
            if not doc.package:
                continue
            if doc.package.property != self.transaction.property:
                raise ValidationError({
                    "documents": f"Document '{doc.title}' belongs to a different property."
                })

    def save(self, *args, **kwargs):
        self.is_completed = bool(self.completed_date)
        self.full_clean()
        super().save(*args, **kwargs)

    def complete(self, completion_date=None):
        if self.is_completed:
            raise ValidationError("Milestone is already completed.")
        self.completed_date = completion_date or timezone.now().date()
        self.is_completed = True
        self.save()
        return self