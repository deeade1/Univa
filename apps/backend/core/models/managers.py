# core/models/managers.py

"""
Location manager for LocationModel with GIS helpers.
"""

from django.contrib.gis.db.models import Manager
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Q


class LocationManager(Manager):
    """
    Custom manager for LocationModel with GIS helpers.
    Used by all apps that inherit from LocationModel.
    """

    def nearby(self, point, radius_km=10):
        """
        Get objects within radius of a point.
        
        Args:
            point: Point object or (latitude, longitude) tuple
            radius_km: Radius in kilometers
        
        Returns:
            QuerySet: Objects within radius
        """
        if isinstance(point, (tuple, list)) and len(point) == 2:
            lat, lng = point
            point = Point(float(lng), float(lat), srid=4326)
        elif not isinstance(point, Point):
            raise ValueError("point must be a Point or (latitude, longitude) tuple")

        return self.filter(
            location_point__distance_lte=(point, D(km=radius_km))
        ).annotate(
            distance=Distance("location_point", point)
        ).order_by("distance")

    def with_coordinates(self):
        """Filter objects with valid coordinates."""
        return self.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            location_point__isnull=False,
        )

    def without_coordinates(self):
        """Filter objects without coordinates."""
        return self.filter(
            latitude__isnull=True,
            longitude__isnull=True,
            location_point__isnull=True,
        )

    def with_address(self):
        """Filter objects with resolved address."""
        return self.exclude(
            Q(location__isnull=True) | Q(location__exact="")
        )

    def without_address(self):
        """Filter objects without resolved address."""
        return self.filter(
            Q(location__isnull=True) | Q(location__exact="")
        )

    def within_bounds(self, min_lat, max_lat, min_lng, max_lng):
        """
        Filter objects within bounding box.
        
        Args:
            min_lat: Minimum latitude
            max_lat: Maximum latitude
            min_lng: Minimum longitude
            max_lng: Maximum longitude
        
        Returns:
            QuerySet: Objects within bounding box
        """
        return self.filter(
            latitude__gte=min_lat,
            latitude__lte=max_lat,
            longitude__gte=min_lng,
            longitude__lte=max_lng,
        )

    def with_location_source(self, source):
        """Filter by location source."""
        return self.filter(location_source=source)

    def recently_updated(self, hours=24):
        """Filter objects recently updated."""
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(hours=hours)
        return self.filter(location_timestamp__gte=cutoff)

    def with_location(self):
        """Filter objects with any location data."""
        return self.filter(
            location_point__isnull=False
        )

    def without_location(self):
        """Filter objects without any location data."""
        return self.filter(
            location_point__isnull=True
        )

    def nearest_to(self, point, limit=10):
        """
        Get nearest objects to a point.
        
        Args:
            point: Point or (latitude, longitude) tuple
            limit: Maximum number of results
        
        Returns:
            QuerySet: Nearest objects
        """
        if isinstance(point, (tuple, list)) and len(point) == 2:
            lat, lng = point
            point = Point(float(lng), float(lat), srid=4326)
        elif not isinstance(point, Point):
            raise ValueError("point must be a Point or (latitude, longitude) tuple")

        return self.filter(
            location_point__isnull=False
        ).annotate(
            distance=Distance("location_point", point)
        ).order_by("distance")[:limit]

    # ============================================================
    # Bulk Operations
    # ============================================================

    def bulk_update_location(self, objects_data):
        """
        Bulk update locations for multiple objects.
        
        Args:
            objects_data: List of dicts with 'id', 'latitude', 'longitude'
        
        Returns:
            int: Number of objects updated
        """
        updates = []
        for data in objects_data:
            obj = self.get(id=data['id'])
            obj.update_location(
                data['latitude'],
                data['longitude'],
                source=data.get('source', 'bulk'),
                save=False,
                queue_tasks=False,
            )
            updates.append(obj)

        return self.bulk_update(
            updates,
            fields=[
                'latitude',
                'longitude',
                'location_point',
                'location_accuracy',
                'location_source',
                'location_timestamp',
            ]
        )