# graphq/realestate/filters.py

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.utils import timezone
from datetime import timedelta

import django_filters as filters


# =============================================================================
# PROPERTY PROXIMITY FILTER (for nearby_properties)
# =============================================================================

class PropertyProximityFilter(filters.FilterSet):
    """
    Filters for nearby-property searches.

    The frontend passes latitude/longitude/radius_km/max_results
    as filter arguments instead of custom resolver args.
    """

    latitude = filters.NumberFilter(method="filter_nearby")
    longitude = filters.NumberFilter(method="filter_nearby")
    radius_km = filters.NumberFilter(method="filter_nearby")
    max_results = filters.NumberFilter(method="filter_nearby")

    def filter_nearby(self, queryset, name, value):
        # Only trigger the distance query once, on the first of
        # the four params that Django calls filter_* on.
        # Use self.data to grab all four together.
        data = self.data or {}

        lat = data.get("latitude")
        lng = data.get("longitude")
        radius = data.get("radiusKm") or data.get("radius_km") or 10
        max_results = data.get("maxResults") or data.get("max_results") or 20

        if not lat or not lng:
            return queryset

        try:
            lat = float(lat)
            lng = float(lng)
            radius = float(radius)
            max_results = int(max_results)
        except (TypeError, ValueError):
            return queryset.none()

        point = Point(lng, lat, srid=4326)

        return (
            queryset
            .filter(location_point__distance_lte=(point, D(km=radius)))
            .distance(point)
            .order_by("distance")[:max_results]
        )


# =============================================================================
# LISTING FILTER (for properties_in_neighborhood + general listing queries)
# =============================================================================

class ListingFilter(filters.FilterSet):
    """
    Filters for ListingNode connections, including neighborhood
    filtering used by the properties_in_neighborhood query.
    """

    neighborhood_id = filters.NumberFilter(
        field_name="neighborhood_id",
        lookup_expr="exact",
    )

    status = filters.CharFilter(
        field_name="property_status",
        lookup_expr="iexact",
    )

    property_type = filters.CharFilter(
        method="filter_property_type",
    )

    def filter_property_type(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(
            listing_type__property_type__iexact=value,
        ).distinct()


# =============================================================================
# LIVE TOUR SCHEDULE FILTER (for upcoming_live_tours)
# =============================================================================

class LiveTourScheduleFilter(filters.FilterSet):
    """
    Filters for live tour schedules.

    The frontend passes days_ahead to constrain the schedule window.
    """

    days_ahead = filters.NumberFilter(method="filter_upcoming")

    def filter_upcoming(self, queryset, name, value):
        if not value:
            return queryset

        try:
            days = int(value)
        except (TypeError, ValueError):
            return queryset

        now = timezone.now()
        cutoff = now + timedelta(days=days)

        return queryset.filter(
            scheduled_time__gte=now,
            scheduled_time__lte=cutoff,
        ).order_by("scheduled_time")


# =============================================================================
# MARKET TREND FILTER (for all_market_trends)
# =============================================================================

class MarketTrendFilter(filters.FilterSet):
    """
    Filters for market trends.
    """

    neighborhood_id = filters.NumberFilter(
        field_name="neighborhood_id",
        lookup_expr="exact",
    )