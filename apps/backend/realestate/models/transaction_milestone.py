# apps/backend/realestate/models/transaction_milestone.py

"""
Transaction Milestone model for real estate.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction as db_transaction
from django.utils import timezone


class TransactionMilestone(models.Model):
    transaction = models.ForeignKey(
        "Transaction",
        on_delete=models.CASCADE,
        related_name="milestones",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    required = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    documents = models.ManyToManyField(
        "Document",
        related_name="transaction_milestones",
        blank=True,
    )

    class Meta:
        ordering = ["order", "id"]
        indexes = [
            models.Index(
                fields=["transaction", "order"],
                name="milestone_transac_order_idx",
            ),
            models.Index(
                fields=["transaction", "required", "completed_date"],
                name="milestone_completion_idx",
            ),
            models.Index(
                fields=["due_date", "completed_date"],
                name="milestone_due_complet_idx",
            ),
        ]

    def __str__(self):
        status = "Completed" if self.is_completed else "Pending"
        return f"{self.name} - Due: {self.due_date} - {status}"

    def clean(self):
        """
        Validate that every attached document belongs to the same
        property as the transaction.

        Uses select_related to avoid the N+1 the previous
        implementation had (documents → package → property).
        """
        # Guard against unsaved instances (no transaction FK yet).
        if self.transaction_id is None:
            return

        transaction_property_id = self.transaction.property_id

        for doc in self.documents.select_related("package__property"):
            if doc.package is None:
                continue
            if doc.package.property_id != transaction_property_id:
                raise ValidationError(
                    {
                        "documents": (
                            f"Document '{doc.title}' belongs to a "
                            f"different property."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        """
        Save the milestone.

        Derives `is_completed` from `completed_date`, then runs
        `self.clean()` for the cross-row document/property
        validation. `full_clean()` is not called — that's the
        caller's responsibility for constraint-level checks.
        """
        self.is_completed = bool(self.completed_date)
        self.clean()
        super().save(*args, **kwargs)

    @db_transaction.atomic
    def complete(self, completion_date=None):
        """
        Mark the milestone complete.

        Locks the row so concurrent completions of the same milestone
        cannot both succeed.
        """
        locked = (
            type(self)
            .objects
            .select_for_update()
            .get(pk=self.pk)
        )

        if locked.is_completed:
            raise ValidationError("Milestone is already completed.")

        locked.completed_date = (
            completion_date or timezone.now().date()
        )
        locked.is_completed = True
        locked.save()

        # Sync the caller's instance.
        self.completed_date = locked.completed_date
        self.is_completed = locked.is_completed

        return self