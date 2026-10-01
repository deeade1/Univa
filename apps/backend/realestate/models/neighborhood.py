# apps/backend/realestate/models/neighborhood.py

"""
Neighborhood model for real estate.
"""

from django.contrib.gis.db import models as gis_models
from django.db import models


class Neighborhood(models.Model):
    name = models.CharField(max_length=200)
    boundary = gis_models.PolygonField()
    center_point = gis_models.PointField()
    avg_price = models.DecimalField(max_digits=12, decimal_places=2)
    avg_price_per_sqft = models.DecimalField(max_digits=8, decimal_places=2)
    school_rating = models.DecimalField(max_digits=3, decimal_places=1)
    crime_rate = models.DecimalField(max_digits=5, decimal_places=2)
    amenities_score = models.PositiveIntegerField()

    class Meta:
        ordering = ['name']
        indexes = [
            gis_models.Index(fields=['boundary'], name='neighborhood_boundary_idx'),
            gis_models.Index(fields=['center_point'], name='neighborhood_center_idx'),
            models.Index(fields=['name'], name='neighborhood_name_idx'),
            models.Index(fields=['avg_price'], name='neighborhood_avg_price_idx'),
            models.Index(fields=['school_rating'], name='neighborhood_school_idx'),
        ]

    def contains(self, point):
        return self.boundary.contains(point)

    def __str__(self):
        return self.name