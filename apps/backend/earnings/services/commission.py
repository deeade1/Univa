"""
Commission → Earning integration.

This module is an integration boundary.

The canonical Earning model remains completely independent of
the commissions application.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from commissions.models import Commission, CommissionAllocation

from ..models import Earning, EarningType
from .earning import EarningService


class CommissionEarningService:

    @staticmethod
    @transaction.atomic
    def create_from_allocation(
        *,
        allocation: CommissionAllocation,
        earning_type: EarningType,
    ) -> Earning:

        commission = allocation.commission

        if commission.status not in {
            Commission.Status.APPROVED,
            Commission.Status.PAYABLE,
            Commission.Status.SETTLED,
        }:
            raise ValidationError(
                _(
                    "A commission allocation cannot become an "
                    "earning until its commission has been approved."
                )
            )

        return EarningService.create_earning(
            beneficiary=allocation.beneficiary,
            earning_type=earning_type,
            source_type="commission_allocation",
            source_id=str(allocation.id),
            source_reference=str(
                commission.source_reference
                or commission.source_id
            ),
            amount=allocation.amount,
            currency=commission.currency,
            calculation_basis=commission.calculation_basis,
            calculation_rate=commission.rate,
            calculation_metadata={
                "commission_id": str(commission.id),
                "commission_plan_id": str(
                    commission.plan_id
                ),
                "commission_allocation_id": str(
                    allocation.id
                ),
            },
        )