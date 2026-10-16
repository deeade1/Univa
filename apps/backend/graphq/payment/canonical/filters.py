"""
FilterSets for canonical Payment GraphQL types.

Filters shape queries only. They do not enforce business rules.
Access control is enforced by each node's get_queryset().
"""

import django_filters as filters
from django.db.models import Q

from payment.canonical.models import (
    Payment,
    PaymentExecution,
    PaymentExecutionEvent,
    PaymentInstrument,
)


# ---------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------

class PaymentFilter(filters.FilterSet):
    """
    Filters for the canonical Payment type.
    """

    reference = filters.CharFilter(lookup_expr="icontains")
    reference_exact = filters.CharFilter(
        field_name="reference", lookup_expr="exact"
    )

    source_type = filters.CharFilter(lookup_expr="exact")
    source_id = filters.CharFilter(lookup_expr="exact")
    source_reference = filters.CharFilter(lookup_expr="icontains")

    direction = filters.CharFilter(lookup_expr="exact")
    purpose = filters.CharFilter(lookup_expr="exact")
    status = filters.CharFilter(lookup_expr="exact")
    currency = filters.CharFilter(lookup_expr="iexact")

    payer = filters.UUIDFilter(field_name="payer__id")
    beneficiary = filters.UUIDFilter(field_name="beneficiary__id")

    amount_min = filters.NumberFilter(
        field_name="amount", lookup_expr="gte"
    )
    amount_max = filters.NumberFilter(
        field_name="amount", lookup_expr="lte"
    )

    created_after = filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )
    completed_after = filters.IsoDateTimeFilter(
        field_name="completed_at", lookup_expr="gte"
    )
    completed_before = filters.IsoDateTimeFilter(
        field_name="completed_at", lookup_expr="lte"
    )

    involved = filters.BooleanFilter(
        method="filter_involved",
        label="Only payments where the current user is a party.",
    )

    class Meta:
        model = Payment
        fields = [
            "reference",
            "direction",
            "purpose",
            "source_type",
            "source_id",
            "payer",
            "beneficiary",
            "currency",
            "status",
        ]

    def filter_involved(self, queryset, name, value):
        if not value:
            return queryset

        user = getattr(self.request, "user", None)
        if user is None or not user.is_authenticated:
            return queryset.none()

        return queryset.filter(
            Q(payer=user) | Q(beneficiary=user)
        )


# ---------------------------------------------------------------------
# PaymentExecution
# ---------------------------------------------------------------------

class PaymentExecutionFilter(filters.FilterSet):
    """
    Filters for the canonical PaymentExecution type.
    """

    reference = filters.CharFilter(lookup_expr="icontains")
    reference_exact = filters.CharFilter(
        field_name="reference", lookup_expr="exact"
    )

    provider = filters.CharFilter(lookup_expr="icontains")
    provider_reference = filters.CharFilter(lookup_expr="icontains")
    failure_code = filters.CharFilter(lookup_expr="icontains")
    banking_transaction_reference = filters.CharFilter(
        lookup_expr="icontains"
    )

    route_type = filters.CharFilter(lookup_expr="exact")
    status = filters.CharFilter(lookup_expr="exact")
    reconciliation_state = filters.CharFilter(lookup_expr="exact")

    payment = filters.UUIDFilter(field_name="payment__id")
    instrument = filters.UUIDFilter(field_name="instrument__id")

    attempt_number = filters.NumberFilter(lookup_expr="exact")
    attempt_number_min = filters.NumberFilter(
        field_name="attempt_number", lookup_expr="gte"
    )
    attempt_number_max = filters.NumberFilter(
        field_name="attempt_number", lookup_expr="lte"
    )

    created_after = filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )
    completed_after = filters.IsoDateTimeFilter(
        field_name="completed_at", lookup_expr="gte"
    )
    completed_before = filters.IsoDateTimeFilter(
        field_name="completed_at", lookup_expr="lte"
    )

    requires_reconciliation = filters.BooleanFilter(
        method="filter_requires_reconciliation",
    )

    class Meta:
        model = PaymentExecution
        fields = [
            "reference",
            "payment",
            "attempt_number",
            "idempotency_key",
            "route_type",
            "provider",
            "provider_reference",
            "instrument",
            "status",
            "reconciliation_state",
            "failure_code",
            "banking_transaction_reference",
        ]

    def filter_requires_reconciliation(self, queryset, name, value):
        if value is None:
            return queryset

        required = PaymentExecution.ReconciliationState.REQUIRED
        if value:
            return queryset.filter(reconciliation_state=required)
        return queryset.exclude(reconciliation_state=required)


# ---------------------------------------------------------------------
# PaymentExecutionEvent
# ---------------------------------------------------------------------

class PaymentExecutionEventFilter(filters.FilterSet):
    """
    Filters for the canonical PaymentExecutionEvent type.
    """

    execution = filters.UUIDFilter(field_name="execution__id")
    event_type = filters.CharFilter(lookup_expr="exact")
    source = filters.CharFilter(lookup_expr="exact")
    provider_event_id = filters.CharFilter(lookup_expr="exact")
    provider_reference = filters.CharFilter(lookup_expr="icontains")

    occurred_after = filters.IsoDateTimeFilter(
        field_name="occurred_at", lookup_expr="gte"
    )
    occurred_before = filters.IsoDateTimeFilter(
        field_name="occurred_at", lookup_expr="lte"
    )
    received_after = filters.IsoDateTimeFilter(
        field_name="received_at", lookup_expr="gte"
    )
    received_before = filters.IsoDateTimeFilter(
        field_name="received_at", lookup_expr="lte"
    )

    class Meta:
        model = PaymentExecutionEvent
        fields = [
            "execution",
            "event_type",
            "source",
            "provider_event_id",
            "provider_reference",
        ]


# ---------------------------------------------------------------------
# PaymentInstrument
# ---------------------------------------------------------------------

class PaymentInstrumentFilter(filters.FilterSet):
    """
    Filters for the canonical PaymentInstrument type.
    """

    reference = filters.CharFilter(lookup_expr="icontains")
    reference_exact = filters.CharFilter(
        field_name="reference", lookup_expr="exact"
    )

    owner = filters.UUIDFilter(field_name="owner__id")
    instrument_type = filters.CharFilter(lookup_expr="exact")
    institution = filters.CharFilter(lookup_expr="icontains")
    status = filters.CharFilter(lookup_expr="exact")
    verification_status = filters.CharFilter(lookup_expr="exact")

    can_fund = filters.BooleanFilter()
    can_receive = filters.BooleanFilter()

    created_after = filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )

    class Meta:
        model = PaymentInstrument
        fields = [
            "reference",
            "owner",
            "instrument_type",
            "institution",
            "can_fund",
            "can_receive",
            "status",
            "verification_status",
        ]