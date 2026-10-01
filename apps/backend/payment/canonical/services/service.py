from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from payment.canonical.models import Payment


class PaymentService:
    """
    Canonical service boundary for creating Payment records.

    This service owns Payment creation and idempotency.

    It does not:
        - execute payments
        - select providers
        - interact with Banking
        - perform reconciliation
        - manage PaymentExecution
        - manage Settlement lifecycle
    """

    @classmethod
    def _validate_amount(cls, amount):
        if amount is None:
            raise ValidationError({"amount": "Amount is required."})

        amount = Decimal(str(amount))

        if amount <= 0:
            raise ValidationError(
                {"amount": "Amount must be greater than zero."}
            )

        return amount

    @classmethod
    def _validate_required(cls, **values):
        errors = {}

        for field, value in values.items():
            if value is None or (
                isinstance(value, str) and not value.strip()
            ):
                errors[field] = f"{field} is required."

        if errors:
            raise ValidationError(errors)

    @classmethod
    def _normalize_currency(cls, currency):
        if currency is None:
            raise ValidationError(
                {"currency": "Currency is required."}
            )

        currency = str(currency).strip().upper()

        if len(currency) != 3:
            raise ValidationError(
                {"currency": "Currency must be exactly 3 characters."}
            )

        return currency

    @classmethod
    def _validate_direction_requirements(
        cls,
        *,
        direction,
        payer,
        beneficiary,
    ):
        errors = {}

        if direction == Payment.Direction.DISBURSE:
            if beneficiary is None:
                errors["beneficiary"] = (
                    "Beneficiary is required for disbursement payments."
                )

        if errors:
            raise ValidationError(errors)

    @classmethod
    def _idempotency_matches(
        cls,
        payment,
        *,
        direction,
        purpose,
        source_type,
        source_id,
        source_reference,
        payer,
        beneficiary,
        amount,
        currency,
    ):
        return (
            payment.direction == direction
            and payment.purpose == purpose
            and payment.source_type == source_type
            and payment.source_id == source_id
            and payment.source_reference == (source_reference or "")
            and payment.payer_id == getattr(payer, "pk", None)
            and payment.beneficiary_id
            == getattr(beneficiary, "pk", None)
            and payment.amount == amount
            and payment.currency == currency
        )

    @classmethod
    def _validate_idempotent_match(
        cls,
        payment,
        *,
        direction,
        purpose,
        source_type,
        source_id,
        source_reference,
        payer,
        beneficiary,
        amount,
        currency,
    ):
        if cls._idempotency_matches(
            payment,
            direction=direction,
            purpose=purpose,
            source_type=source_type,
            source_id=source_id,
            source_reference=source_reference,
            payer=payer,
            beneficiary=beneficiary,
            amount=amount,
            currency=currency,
        ):
            return payment

        raise ValidationError(
            {
                "idempotency_key": (
                    "A payment already exists with this idempotency "
                    "key but different payment parameters."
                )
            }
        )

    @classmethod
    @transaction.atomic
    def create_payment(
        cls,
        *,
        direction,
        purpose,
        source_type,
        source_id,
        amount,
        currency,
        idempotency_key,
        payer=None,
        beneficiary=None,
        source_reference="",
        metadata=None,
    ):
        cls._validate_required(
            direction=direction,
            purpose=purpose,
            source_type=source_type,
            source_id=source_id,
            idempotency_key=idempotency_key,
        )

        amount = cls._validate_amount(amount)
        currency = cls._normalize_currency(currency)

        cls._validate_direction_requirements(
            direction=direction,
            payer=payer,
            beneficiary=beneficiary,
        )

        if metadata is None:
            metadata = {}

        try:
            payment = Payment.objects.get(
                idempotency_key=idempotency_key,
            )
        except Payment.DoesNotExist:
            payment = None

        if payment is not None:
            return cls._validate_idempotent_match(
                payment,
                direction=direction,
                purpose=purpose,
                source_type=source_type,
                source_id=source_id,
                source_reference=source_reference,
                payer=payer,
                beneficiary=beneficiary,
                amount=amount,
                currency=currency,
            )

        payment = Payment(
            reference=cls._generate_reference(),
            direction=direction,
            purpose=purpose,
            source_type=source_type,
            source_id=source_id,
            source_reference=source_reference or "",
            payer=payer,
            beneficiary=beneficiary,
            amount=amount,
            currency=currency,
            status=Payment.Status.PENDING,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )

        payment.full_clean()

        try:
            payment.save()
        except IntegrityError:
            existing = Payment.objects.get(
                idempotency_key=idempotency_key,
            )

            return cls._validate_idempotent_match(
                existing,
                direction=direction,
                purpose=purpose,
                source_type=source_type,
                source_id=source_id,
                source_reference=source_reference,
                payer=payer,
                beneficiary=beneficiary,
                amount=amount,
                currency=currency,
            )

        return payment

    @classmethod
    def _generate_reference(cls):
        """
        Generate a unique Payment business reference.

        Provider references and Banking transaction references
        remain separate from this Payment reference.
        """
        import uuid

        return f"PAY-{uuid.uuid4().hex[:12].upper()}"