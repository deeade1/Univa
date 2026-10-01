"""
Commission application service for Univa.

This module orchestrates commission creation and lifecycle operations.

The service sits between domain-specific callers and the canonical
commission models/calculation service.

Responsibilities:

    - validate application-level inputs
    - calculate commissions
    - create Commission records
    - create and finalize allocations
    - manage controlled commission lifecycle transitions

Not responsible for:

    - payment execution
    - settlement execution
    - banking ledger operations
    - domain-specific transaction rules
    - notification delivery

Those concerns belong to their respective domains/services.
"""

from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ..models import (
    Commission,
    CommissionAllocation,
    CommissionPlan,
)
from .calculator import CommissionCalculationResult
from .calculator import CommissionCalculator


class CommissionService:
    """
    Application service for canonical commissions.
    """

    @classmethod
    @transaction.atomic
    def create_commission(
        cls,
        *,
        plan: CommissionPlan,
        beneficiary,
        source_type: str,
        source_id: str,
        calculation_basis: Decimal,
        currency: str = "NGN",
        source_reference: str = "",
        notes: str = "",
        metadata: dict | None = None,
    ) -> Commission:
        """
        Calculate and create a Commission.

        A newly created commission is placed in the CALCULATED state
        because calculation has already been performed successfully.
        """

        cls._validate_source(
            source_type=source_type,
            source_id=source_id,
        )

        cls._validate_currency(currency)

        result = CommissionCalculator.calculate(
            plan=plan,
            calculation_basis=calculation_basis,
        )

        now = timezone.now()

        commission = Commission.objects.create(
            plan=plan,
            beneficiary=beneficiary,
            source_type=source_type,
            source_id=source_id,
            source_reference=source_reference,
            calculation_basis=result.calculation_basis,
            rate=result.rate,
            calculated_amount=result.calculated_amount,
            currency=currency,
            status=Commission.Status.CALCULATED,
            notes=notes,
            metadata=metadata or {},
            calculated_at=now,
        )

        return commission

    @classmethod
    @transaction.atomic
    def create_allocations(
        cls,
        *,
        commission: Commission,
        allocations: Iterable[dict],
    ) -> list[CommissionAllocation]:
        """
        Create allocations for a commission.

        Expected allocation structure:

            {
                "beneficiary": user,
                "amount": Decimal("7000.00"),
                "allocation_percentage": Decimal("70.00"),
                "notes": "",
                "metadata": {},
            }

        The allocations must collectively equal the commission
        amount before they are finalized.
        """

        if commission.status not in {
            Commission.Status.CALCULATED,
            Commission.Status.APPROVED,
        }:
            raise ValidationError(
                _(
                    "Allocations can only be created for a "
                    "calculated or approved commission."
                )
            )

        allocation_items = list(allocations)

        if not allocation_items:
            raise ValidationError(
                _("At least one commission allocation is required.")
            )

        created_allocations = []

        for item in allocation_items:
            allocation = CommissionAllocation(
                commission=commission,
                beneficiary=item["beneficiary"],
                amount=item["amount"],
                allocation_percentage=item.get(
                    "allocation_percentage"
                ),
                notes=item.get("notes", ""),
                metadata=item.get("metadata", {}),
            )

            allocation.full_clean()
            allocation.save()

            created_allocations.append(allocation)

        cls._validate_allocation_total(
            commission=commission,
            allocations=created_allocations,
        )

        return created_allocations

    @classmethod
    @transaction.atomic
    def approve(
        cls,
        *,
        commission: Commission,
    ) -> Commission:
        """
        Approve a calculated commission.
        """

        if commission.status != Commission.Status.CALCULATED:
            raise ValidationError(
                _(
                    "Only calculated commissions can be approved."
                )
            )

        commission.status = Commission.Status.APPROVED
        commission.approved_at = timezone.now()

        commission.full_clean(
            exclude=[
                "settled_at",
                "reversed_at",
            ]
        )

        commission.save(
            update_fields=[
                "status",
                "approved_at",
                "updated_at",
            ]
        )

        return commission

    @classmethod
    @transaction.atomic
    def mark_payable(
        cls,
        *,
        commission: Commission,
    ) -> Commission:
        """
        Mark an approved commission as payable.

        This does not perform settlement or payment.
        """

        if commission.status != Commission.Status.APPROVED:
            raise ValidationError(
                _(
                    "Only approved commissions can be marked payable."
                )
            )

        commission.status = Commission.Status.PAYABLE
        commission.payable_at = timezone.now()

        commission.full_clean(
            exclude=[
                "settled_at",
                "reversed_at",
            ]
        )

        commission.save(
            update_fields=[
                "status",
                "payable_at",
                "updated_at",
            ]
        )

        return commission

    @classmethod
    @transaction.atomic
    def cancel(
        cls,
        *,
        commission: Commission,
    ) -> Commission:
        """
        Cancel a commission that has not yet been settled.
        """

        if commission.status in {
            Commission.Status.SETTLED,
            Commission.Status.REVERSED,
        }:
            raise ValidationError(
                _(
                    "A settled or reversed commission cannot "
                    "be cancelled."
                )
            )

        commission.status = Commission.Status.CANCELLED

        commission.full_clean(
            exclude=[
                "settled_at",
                "reversed_at",
            ]
        )

        commission.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return commission

    @classmethod
    @transaction.atomic
    def reverse(
        cls,
        *,
        commission: Commission,
    ) -> Commission:
        """
        Reverse a commission.

        Reversal is distinct from cancellation because the commission
        may already have progressed through the payable/settlement
        lifecycle.
        """

        if commission.status == Commission.Status.REVERSED:
            raise ValidationError(
                _("Commission is already reversed.")
            )

        if commission.status == Commission.Status.CANCELLED:
            raise ValidationError(
                _(
                    "A cancelled commission cannot be reversed."
                )
            )

        commission.status = Commission.Status.REVERSED
        commission.reversed_at = timezone.now()

        commission.full_clean(
            exclude=[
                "settled_at",
            ]
        )

        commission.save(
            update_fields=[
                "status",
                "reversed_at",
                "updated_at",
            ]
        )

        return commission

    @staticmethod
    def _validate_source(
        *,
        source_type: str,
        source_id: str,
    ) -> None:
        if not source_type:
            raise ValidationError(
                {
                    "source_type": _(
                        "Commission source type is required."
                    )
                }
            )

        if not source_id:
            raise ValidationError(
                {
                    "source_id": _(
                        "Commission source ID is required."
                    )
                }
            )

    @staticmethod
    def _validate_currency(currency: str) -> None:
        if not currency:
            raise ValidationError(
                {
                    "currency": _(
                        "Commission currency is required."
                    )
                }
            )

        if len(currency) != 3:
            raise ValidationError(
                {
                    "currency": _(
                        "Commission currency must be a "
                        "three-letter currency code."
                    )
                }
            )

    @staticmethod
    def _validate_allocation_total(
        *,
        commission: Commission,
        allocations: list[CommissionAllocation],
    ) -> None:
        allocated_amount = sum(
            (
                allocation.amount
                for allocation in allocations
            ),
            Decimal("0.00"),
        )

        if allocated_amount != commission.calculated_amount:
            raise ValidationError(
                _(
                    "Commission allocations must equal the "
                    "commission calculated amount. "
                    "Expected %(expected)s, received %(actual)s."
                )
                % {
                    "expected": commission.calculated_amount,
                    "actual": allocated_amount,
                }
            )