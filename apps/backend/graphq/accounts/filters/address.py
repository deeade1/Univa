"""
GraphQL filters for account-owned addresses.

Architecture
------------
This module belongs to the Accounts GraphQL boundary.

Responsibilities:
    - expose safe address filtering to GraphQL
    - keep filtering logic separate from GraphQL types
    - scope filters to fields owned by accounts.Address

Non-responsibilities:
    - authorization
    - mutation logic
    - address creation/update
    - ecommerce filtering
    - transport filtering
    - real-estate filtering
    - notification filtering

Compatible with:
    - Django
    - django-filter
    - Graphene-Django 3.x
    - Graphene 3.2.3
    - Relay
"""

from django.db.models import Q
from django_filters import rest_framework as filters

from accounts.models.address import Address


class AddressFilter(filters.FilterSet):
    """
    FilterSet for the Accounts Address GraphQL node.

    The filter names intentionally map to the actual Address model
    fields rather than exposing arbitrary queryset filtering.

    GraphQL consumers can use these filters through the
    Graphene-Django connection generated for AddressNode.
    """

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------

    user = filters.NumberFilter(
        field_name="user_id",
        lookup_expr="exact",
    )

    user_id = filters.NumberFilter(
        field_name="user_id",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Address classification
    # ------------------------------------------------------------------

    address_type = filters.CharFilter(
        field_name="address_type",
        lookup_expr="exact",
    )

    address_type_contains = filters.CharFilter(
        field_name="address_type",
        lookup_expr="icontains",
    )

    is_default = filters.BooleanFilter(
        field_name="is_default",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Recipient
    # ------------------------------------------------------------------

    first_name = filters.CharFilter(
        field_name="first_name",
        lookup_expr="icontains",
    )

    last_name = filters.CharFilter(
        field_name="last_name",
        lookup_expr="icontains",
    )

    company_name = filters.CharFilter(
        field_name="company_name",
        lookup_expr="icontains",
    )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    street_address_1 = filters.CharFilter(
        field_name="street_address_1",
        lookup_expr="icontains",
    )

    street_address_2 = filters.CharFilter(
        field_name="street_address_2",
        lookup_expr="icontains",
    )

    city = filters.CharFilter(
        field_name="city",
        lookup_expr="icontains",
    )

    city_area = filters.CharFilter(
        field_name="city_area",
        lookup_expr="icontains",
    )

    postal_code = filters.CharFilter(
        field_name="postal_code",
        lookup_expr="exact",
    )

    state = filters.CharFilter(
        field_name="state",
        lookup_expr="exact",
    )

    country = filters.CharFilter(
        field_name="country",
        lookup_expr="exact",
    )

    country_area = filters.CharFilter(
        field_name="country_area",
        lookup_expr="icontains",
    )

    # ------------------------------------------------------------------
    # Contact
    # ------------------------------------------------------------------

    phone = filters.CharFilter(
        field_name="phone",
        lookup_expr="icontains",
    )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    validation_skipped = filters.BooleanFilter(
        field_name="validation_skipped",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="exact",
    )

    created_at_gte = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
    )

    created_at_lte = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
    )

    updated_at = filters.DateTimeFilter(
        field_name="updated_at",
        lookup_expr="exact",
    )

    updated_at_gte = filters.DateTimeFilter(
        field_name="updated_at",
        lookup_expr="gte",
    )

    updated_at_lte = filters.DateTimeFilter(
        field_name="updated_at",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    search = filters.CharFilter(
        method="filter_search",
    )

    # ------------------------------------------------------------------
    # Default address helpers
    # ------------------------------------------------------------------

    default_for_type = filters.CharFilter(
        method="filter_default_for_type",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        model = Address

        fields = [
            "user",
            "user_id",
            "address_type",
            "address_type_contains",
            "is_default",
            "first_name",
            "last_name",
            "company_name",
            "street_address_1",
            "street_address_2",
            "city",
            "city_area",
            "postal_code",
            "state",
            "country",
            "country_area",
            "phone",
            "validation_skipped",
            "created_at",
            "created_at_gte",
            "created_at_lte",
            "updated_at",
            "updated_at_gte",
            "updated_at_lte",
            "search",
            "default_for_type",
        ]

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def filter_search(self, queryset, name, value):
        """
        Perform a broad address search.

        Searches the fields that are useful to users when locating
        an address without exposing arbitrary database lookups.
        """

        if not value:
            return queryset

        value = value.strip()

        if not value:
            return queryset

        return queryset.filter(
            Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
            | Q(company_name__icontains=value)
            | Q(street_address_1__icontains=value)
            | Q(street_address_2__icontains=value)
            | Q(city__icontains=value)
            | Q(city_area__icontains=value)
            | Q(postal_code__icontains=value)
            | Q(state__icontains=value)
            | Q(country_area__icontains=value)
            | Q(phone__icontains=value)
        )

    # ------------------------------------------------------------------
    # Default address filtering
    # ------------------------------------------------------------------

    def filter_default_for_type(self, queryset, name, value):
        """
        Return default addresses for a particular address type.

        Example:

            default_for_type = "shipping"

        produces:

            address_type = "shipping"
            is_default = True
        """

        if not value:
            return queryset

        value = value.strip().lower()

        return queryset.filter(
            address_type=value,
            is_default=True,
        )