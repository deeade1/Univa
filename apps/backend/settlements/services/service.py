"""
Canonical Settlement service for Univa.

SettlementService is responsible for creating Settlement records.

Responsibilities
----------------
- Validate settlement creation input.
- Normalize monetary values and currency.
- Enforce positive settlement amounts.
- Enforce required source information.
- Enforce idempotency.
- Validate the Settlement model before persistence.

This service intentionally does NOT:

- perform status transitions
- execute payments
- interact with banking
- interact with external providers
- create settlement attempts
- record audit events

Those concerns belong to their respective layers.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from settlements.models import Settlement


class SettlementService:
    """
    Application service for creating canonical Settlement records.
    """

    @staticmethod
    def _validate_amount(amount):
        """
        Normalize and validate the settlement amount.
        """

        if amount is None:
            raise ValidationError(
                "Settlement amount is required."
            )

        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError, InvalidOperation):
            raise ValidationError(
                "Settlement amount is invalid."
            )

        if amount <= Decimal("0.00"):
            raise ValidationError(
                "Settlement amount must be greater than zero."
            )

        return amount

    @staticmethod
    def _validate_required(
        *,
        reference,
        beneficiary,
        source_type,
        source_id,
        idempotency_key,
    ):
        """
        Validate required settlement creation fields.
        """

        errors = {}

        if not reference:
            errors["reference"] = (
                "Settlement reference is required."
            )

        if beneficiary is None:
            errors["beneficiary"] = (
                "Settlement beneficiary is required."
            )

        if not source_type:
            errors["source_type"] = (
                "Settlement source type is required."
            )

        if not source_id:
            errors["source_id"] = (
                "Settlement source ID is required."
            )

        if not idempotency_key:
            errors["idempotency_key"] = (
                "Settlement idempotency key is required."
            )

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def _validate_idempotent_match(
        settlement,
        *,
        beneficiary,
        source_type,
        source_id,
        source_reference,
        amount,
        currency,
        reference,
    ):
        """
        Ensure an existing idempotency record represents the same
        settlement request.

        Reusing an idempotency key with different financial or source
        information is rejected.
        """

        conflicts = {}

        expected_values = {
            "reference": reference,
            "beneficiary_id": beneficiary.pk,
            "source_type": source_type,
            "source_id": source_id,
            "source_reference": source_reference or "",
            "amount": amount,
            "currency": currency.upper(),
        }

        actual_values = {
            "reference": settlement.reference,
            "beneficiary_id": settlement.beneficiary_id,
            "source_type": settlement.source_type,
            "source_id": settlement.source_id,
            "source_reference": settlement.source_reference,
            "amount": settlement.amount,
            "currency": settlement.currency,
        }

        for field_name, expected in expected_values.items():
            if actual_values[field_name] != expected:
                conflicts[field_name] = (
                    "The idempotency key is already associated "
                    "with a different settlement request."
                )

        if conflicts:
            raise ValidationError(conflicts)

    @classmethod
    @transaction.atomic
    def create_settlement(
        cls,
        *,
        reference,
        beneficiary,
        source_type,
        source_id,
        amount,
        idempotency_key,
        currency="NGN",
        source_reference="",
        notes="",
        metadata=None,
    ):
        """
        Create a Settlement.

        If the idempotency key already exists and represents the exact
        same request, the existing Settlement is returned.

        If the idempotency key exists with different settlement data,
        ValidationError is raised.

        New settlements always begin in PENDING status.
        """

        cls._validate_required(
            reference=reference,
            beneficiary=beneficiary,
            source_type=source_type,
            source_id=source_id,
            idempotency_key=idempotency_key,
        )

        amount = cls._validate_amount(amount)

        if not currency:
            raise ValidationError(
                {"currency": "Settlement currency is required."}
            )

        currency = str(currency).upper()

        if len(currency) != 3:
            raise ValidationError(
                {
                    "currency": (
                        "Currency must be a three-letter code."
                    )
                }
            )

        if metadata is None:
            metadata = {}

        existing = (
            Settlement.objects
            .filter(idempotency_key=idempotency_key)
            .first()
        )

        if existing is not None:
            cls._validate_idempotent_match(
                existing,
                beneficiary=beneficiary,
                source_type=source_type,
                source_id=source_id,
                source_reference=source_reference,
                amount=amount,
                currency=currency,
                reference=reference,
            )

            return existing

        settlement = Settlement(
            reference=reference,
            beneficiary=beneficiary,
            source_type=source_type,
            source_id=source_id,
            source_reference=source_reference or "",
            amount=amount,
            currency=currency,
            status=Settlement.Status.PENDING,
            idempotency_key=idempotency_key,
            notes=notes or "",
            metadata=metadata,
        )

        settlement.full_clean()
        
        try:
            settlement.save()
        except IntegrityError:
            # Another concurrent request may have created the same
            # idempotency key between the lookup and save.
            existing = (
                Settlement.objects
                .filter(idempotency_key=idempotency_key)
                .first()
            )

            if existing is None:
                raise

            cls._validate_idempotent_match(
                existing,
                beneficiary=beneficiary,
                source_type=source_type,
                source_id=source_id,
                source_reference=source_reference,
                amount=amount,
                currency=currency,
                reference=reference,
            )

            return existing

        return settlement