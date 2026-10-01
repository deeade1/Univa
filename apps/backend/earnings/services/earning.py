# apps/backend/earnings/services/earning.py

"""
Canonical earning service.

This service creates and manages Earning records.

It does not:

    - initiate payments
    - create settlements
    - write AuditLog directly
    - know Transport/Real Estate/E-commerce models
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ..models import Earning, EarningAdjustment, EarningType


class EarningService:

    @staticmethod
    @transaction.atomic
    def create_earning(
        *,
        beneficiary,
        earning_type: EarningType,
        source_type: str,
        source_id: str,
        amount,
        currency: str = "NGN",
        earned_at=None,
        calculation_basis=None,
        calculation_rate=None,
        calculation_metadata=None,
        source_reference: str = "",
        notes: str = "",
        metadata=None,
    ) -> Earning:
        if amount is None:
            raise ValidationError(
                _("Earning amount is required.")
            )

        if not source_type:
            raise ValidationError(
                _("Earning source_type is required.")
            )

        if not source_id:
            raise ValidationError(
                _("Earning source_id is required.")
            )

        if not currency:
            raise ValidationError(
                _("Earning currency is required.")
            )

        earning = Earning(
            beneficiary=beneficiary,
            earning_type=earning_type,
            source_type=source_type,
            source_id=str(source_id),
            source_reference=source_reference,
            amount=amount,
            currency=currency.upper(),
            calculation_basis=calculation_basis,
            calculation_rate=calculation_rate,
            calculation_metadata=calculation_metadata or {},
            status=Earning.Status.CALCULATED,
            earned_at=earned_at or timezone.now(),
            calculated_at=timezone.now(),
            notes=notes,
            metadata=metadata or {},
        )

        earning.full_clean()
        earning.save()

        return earning

    @staticmethod
    @transaction.atomic
    def create_adjustment(
        *,
        earning: Earning,
        adjustment_type: str,
        amount,
        reason: str,
        created_by=None,
        source_type: str = "",
        source_id: str = "",
        source_reference: str = "",
        metadata=None,
    ) -> EarningAdjustment:
        if earning.status in {
            Earning.Status.CANCELLED,
        }:
            raise ValidationError(
                _(
                    "Cancelled earnings cannot receive "
                    "adjustments."
                )
            )

        adjustment = EarningAdjustment(
            earning=earning,
            adjustment_type=adjustment_type,
            amount=amount,
            reason=reason,
            created_by=created_by,
            source_type=source_type,
            source_id=str(source_id) if source_id else "",
            source_reference=source_reference,
            metadata=metadata or {},
        )

        adjustment.full_clean()
        adjustment.save()

        return adjustment