from django.db.models import Q

import django_filters
from django_filters import OrderingFilter

from transport.models import (
    Booking,
    Delivery,
    ServiceProviderProfile,
    Tracking,
)


class ServiceProviderProfileFilterSet(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")

    order_by = OrderingFilter(
        fields=(
            ("rating", "rating"),
            ("last_active", "last_active"),
            ("provider_type", "provider_type"),
        )
    )

    class Meta:
        model = ServiceProviderProfile
        fields = [
            "id",
            "user",
            "provider_type",
            "license_type",
            "license_number",
            "union_id",
            "verified_union_member",
            "is_available",
            "is_online",
            "current_service",
            "rating",
            "last_active",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(user__user__first_name__icontains=value)
            | Q(user__user__last_name__icontains=value)
            | Q(user__user__email__icontains=value)
            | Q(user__company_name__icontains=value)
            | Q(license_number__icontains=value)
            | Q(union_id__icontains=value)
        )


class DeliveryFilterSet(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")

    order_by = OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("started_at", "started_at"),
            ("completed_at", "completed_at"),
            ("status", "status"),
            ("service_type", "service_type"),
        )
    )

    class Meta:
        model = Delivery
        fields = [
            "id",
            "service_type",
            "status",
            "customer",
            "provider",
            "vehicle",
            "insurance_required",
            "created_at",
            "started_at",
            "completed_at",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(pickup_address__icontains=value)
            | Q(dropoff_address__icontains=value)
            | Q(customer__user__first_name__icontains=value)
            | Q(customer__user__last_name__icontains=value)
            | Q(customer__user__email__icontains=value)
            | Q(provider__user__user__first_name__icontains=value)
            | Q(provider__user__user__last_name__icontains=value)
        )


class BookingFilterSet(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")

    order_by = OrderingFilter(
        fields=(
            ("booked_at", "booked_at"),
            ("confirmed_at", "confirmed_at"),
            ("cancelled_at", "cancelled_at"),
            ("completed_at", "completed_at"),
            ("status", "status"),
        )
    )

    class Meta:
        model = Booking
        fields = [
            "id",
            "service_request",
            "user",
            "status",
            "booked_at",
            "confirmed_at",
            "cancelled_at",
            "completed_at",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(user__user__first_name__icontains=value)
            | Q(user__user__last_name__icontains=value)
            | Q(user__user__email__icontains=value)
            | Q(service_request__pickup_address__icontains=value)
            | Q(service_request__dropoff_address__icontains=value)
        )


class TrackingFilterSet(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")

    tracking_number = django_filters.CharFilter(
        lookup_expr="icontains",
    )

    order_by = OrderingFilter(
        fields=(
            ("last_updated", "last_updated"),
            ("estimated_delivery", "estimated_delivery"),
            ("tracking_number", "tracking_number"),
        )
    )

    class Meta:
        model = Tracking
        fields = [
            "id",
            "tracking_number",
            "service_request",
            "current_status",
            "estimated_delivery",
            "last_updated",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(tracking_number__icontains=value)
            | Q(service_request__pickup_address__icontains=value)
            | Q(service_request__dropoff_address__icontains=value)
            | Q(service_request__customer__user__first_name__icontains=value)
            | Q(service_request__customer__user__last_name__icontains=value)
            | Q(service_request__customer__user__email__icontains=value)
        )