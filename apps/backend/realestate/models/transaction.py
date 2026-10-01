# apps/backend/realestate/models/transaction.py

"""
Transaction model for real estate.

Relationship architecture:

    accounts.User
        ├── realestate.Client
        │       └── Transaction.buyer
        │
        └── Transaction.seller

The central account identity belongs to AUTH_USER_MODEL.
Real-estate-specific buyer information belongs to Client.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from realestate.constants import TransactionStatus


class Transaction(models.Model):
    """
    Represents a real-estate transaction.

    buyer:
        Real-estate Client who is purchasing the property.

    seller:
        Central account User who is selling the property.
    """

    property = models.ForeignKey(
        "Listing",
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    buyer = models.ForeignKey(
        "Client",
        on_delete=models.PROTECT,
        related_name="buyer_transactions",
    )

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="seller_transactions",
    )

    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.CHOICES,
        default=TransactionStatus.PRE_OFFER,
    )

    offer_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    agreed_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    target_close_date = models.DateField()

    actual_close_date = models.DateField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    escrow_number = models.CharField(
        max_length=50,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["buyer", "status"],
                name="transac_buyer_status_idx",
            ),
            models.Index(
                fields=["seller", "status"],
                name="transac_seller_status_idx",
            ),
            models.Index(
                fields=["property", "status"],
                name="transac_proper_status_idx",
            ),
            models.Index(
                fields=["target_close_date", "status"],
                name="transac_close_date__idx",
            ),
            models.Index(
                fields=["-created_at"],
                name="transac_created_desc_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=[
                            TransactionStatus.CLOSED,
                            TransactionStatus.CANCELLED,
                        ]
                    )
                    | models.Q(agreed_price__isnull=True)
                ),
                name="transaction_agreed_price_required_for_closed",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=[
                            TransactionStatus.CLOSED,
                            TransactionStatus.CANCELLED,
                        ]
                    )
                    | models.Q(actual_close_date__isnull=True)
                ),
                name="transaction_close_date_required_for_closed",
            ),
        ]

    
    def __str__(self):
        property_title = self.property.title or "No Title"

        return (
            f"Transaction #{self.id}: "
            f"{property_title[:30]} - "
            f"{self.get_status_display()}"
        )

    def clean(self):
        """
        Validate transaction business rules.
        """
        super().clean()

        if self.offer_price < 0:
            raise ValidationError(
                {
                    "offer_price": (
                        "Offer price cannot be negative."
                    )
                }
            )

        if self.status == TransactionStatus.CLOSED:
            if self.agreed_price is None:
                raise ValidationError(
                    {
                        "agreed_price": (
                            "Agreed price is required for "
                            "closed transactions."
                        )
                    }
                )

            if self.actual_close_date is None:
                raise ValidationError(
                    {
                        "actual_close_date": (
                            "Actual close date is required for "
                            "closed transactions."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        """
        Save the transaction and synchronize the property's status.
        """

        if (
            self.status == TransactionStatus.CLOSED
            and self.agreed_price is None
        ):
            self.agreed_price = self.offer_price

        if (
            self.status == TransactionStatus.CLOSED
            and self.actual_close_date is None
        ):
            self.actual_close_date = timezone.now().date()

        self.full_clean()

        super().save(*args, **kwargs)

        self._update_property_status()

    def _update_property_status(self):
        """
        Synchronize the associated property's status with
        the transaction state.
        """

        if self.status in [
            TransactionStatus.UNDER_CONTRACT,
            TransactionStatus.DUE_DILIGENCE,
            TransactionStatus.CLOSING,
        ]:
            self.property.property_status = "under_contract"

            self.property.save(
                update_fields=["property_status"]
            )

        elif self.status == TransactionStatus.CLOSED:
            self.property.property_status = "sold"

            self.property.save(
                update_fields=["property_status"]
            )

        elif self.status == TransactionStatus.CANCELLED:
            active_statuses = [
                TransactionStatus.UNDER_CONTRACT,
                TransactionStatus.DUE_DILIGENCE,
                TransactionStatus.CLOSING,
                TransactionStatus.CLOSED,
            ]

            has_other_active_transaction = (
                Transaction.objects
                .filter(
                    property=self.property,
                    status__in=active_statuses,
                )
                .exclude(id=self.id)
                .exists()
            )

            if not has_other_active_transaction:
                self.property.property_status = "published"

                self.property.save(
                    update_fields=["property_status"]
                )

    @classmethod
    def can_create_transaction(
        cls,
        property,
        buyer,
        seller,
    ):
        """
        Determine whether a property can have a new transaction.
        """

        active_statuses = [
            TransactionStatus.PRE_OFFER,
            TransactionStatus.OFFER_PENDING,
            TransactionStatus.UNDER_CONTRACT,
            TransactionStatus.DUE_DILIGENCE,
            TransactionStatus.CLOSING,
        ]

        active = cls.objects.filter(
            property=property,
            status__in=active_statuses,
        )

        if active.exists():
            return (
                False,
                "Property already has an active transaction.",
            )

        return (
            True,
            "Transaction can be created.",
        )

    def update_status(self, new_status, **kwargs):
        """
        Validate and apply a transaction status transition.
        """

        if not TransactionStatus.is_valid_transition(
            self.status,
            new_status,
        ):
            raise ValidationError(
                {
                    "status": (
                        f"Invalid transition from "
                        f"{self.status} to {new_status}."
                    )
                }
            )

        if new_status == TransactionStatus.CLOSED:
            self.agreed_price = kwargs.get(
                "agreed_price",
                self.agreed_price,
            )

            self.actual_close_date = kwargs.get(
                "actual_close_date",
                timezone.now().date(),
            )

        self.status = new_status
        self.save()

        return self
