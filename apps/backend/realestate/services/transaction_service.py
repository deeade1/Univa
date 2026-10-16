# apps/backend/realestate/services/transaction_service.py

"""
Transaction service layer.

Encapsulates business logic for transaction lifecycle operations.
All public methods are atomic and use row-level locking to
serialize concurrent calls.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.constants import TransactionStatus
from realestate.models import (
    Document,
    Listing,
    Transaction,
    TransactionMilestone,
)


class TransactionService:
    """
    Service layer for transaction operations.

    Should be called from GraphQL mutations and other entry
    points; not from model methods.
    """

    @staticmethod
    @transaction.atomic
    def create_transaction(property, buyer, seller, offer_price, **kwargs):
        """
        Create a new transaction with validation.

        Locks the property row to serialize against concurrent
        create attempts. The unique_active_transaction_per_property
        DB constraint is the real guard.

        Returns the persisted Transaction.
        """
        property = (
            Listing.objects
            .select_for_update()
            .get(pk=property.pk)
        )

        can_create, message = Transaction.can_create_transaction(
            property, buyer, seller,
        )
        if not can_create:
            raise ValidationError({"property": message})

        txn = Transaction(
            property=property,
            buyer=buyer,
            seller=seller,
            offer_price=offer_price,
            target_close_date=kwargs.get(
                "target_close_date",
                timezone.now().date() + timezone.timedelta(days=30),
            ),
            notes=kwargs.get("notes", ""),
            escrow_number=kwargs.get("escrow_number", ""),
        )

        # Validate cross-field rules explicitly; the DB will catch
        # constraint violations with IntegrityError.
        txn.clean()

        txn.save()

        # Create default milestones unless the caller supplied
        # their own. This runs in the same transaction as the
        # create; if it fails, the transaction is rolled back too.
        if not kwargs.get("milestones"):
            TransactionService.create_default_milestones(txn)

        return txn

    @staticmethod
    @transaction.atomic
    def create_default_milestones(txn):
        """
        Create the default milestone workflow for a transaction.
        """
        default_milestones = [
            {"name": "Offer Accepted", "order": 1, "due_days": 3},
            {"name": "Contract Signed", "order": 2, "due_days": 7},
            {"name": "Inspection Period", "order": 3, "due_days": 14},
            {"name": "Title Search", "order": 4, "due_days": 21},
            {"name": "Financing Approval", "order": 5, "due_days": 25},
            {"name": "Final Documentation", "order": 6, "due_days": 28},
            {"name": "Closing", "order": 7, "due_days": 30},
        ]

        start_date = timezone.now().date()
        for data in default_milestones:
            due_date = start_date + timezone.timedelta(
                days=data["due_days"]
            )
            TransactionMilestone.objects.create(
                transaction=txn,
                name=data["name"],
                order=data["order"],
                due_date=due_date,
                required=True,
            )

    @staticmethod
    @transaction.atomic
    def complete_milestone(milestone_id, completion_data=None):
        """
        Complete a milestone with validation.

        Returns the completed TransactionMilestone.
        """
        milestone = (
            TransactionMilestone.objects
            .select_for_update()
            .get(id=milestone_id)
        )

        if milestone.transaction.status in [
            TransactionStatus.CLOSED,
            TransactionStatus.CANCELLED,
        ]:
            raise ValidationError(
                "Cannot complete milestones on closed/cancelled "
                "transactions."
            )

        completion_date = (
            completion_data.get("completed_date")
            if completion_data
            else None
        )
        milestone.complete(completion_date)

        if completion_data and "document_ids" in completion_data:
            documents = Document.objects.filter(
                id__in=completion_data["document_ids"],
            )
            milestone.documents.add(*documents)

        return milestone

    @staticmethod
    @transaction.atomic
    def close_transaction(transaction_id, agreed_price, close_date=None):
        """
        Close a transaction with validation.

        Idempotent: if the transaction is already closed, returns
        it unchanged.

        Returns the closed Transaction.
        """
        txn = (
            Transaction.objects
            .select_for_update()
            .get(id=transaction_id)
        )

        if txn.status == TransactionStatus.CLOSED:
            return txn

        if txn.status == TransactionStatus.CANCELLED:
            raise ValidationError(
                {"status": "Cannot close a cancelled transaction."}
            )

        incomplete_required = txn.milestones.filter(
            required=True,
            is_completed=False,
        )
        if incomplete_required.exists():
            missing = ", ".join(
                m.name for m in incomplete_required
            )
            raise ValidationError(
                {"milestones": f"Missing required milestones: {missing}"}
            )

        txn.update_status(
            TransactionStatus.CLOSED,
            agreed_price=agreed_price,
            actual_close_date=close_date or timezone.now().date(),
        )

        return txn