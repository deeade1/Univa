# apps/backend/realestate/models/managers.py

"""
Custom managers for real estate models.
"""

from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db import models
from django.db.models import Avg, Count, Q

from realestate.constants import PROPERTY_TYPES


class ListingQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)
    
    def for_sale(self):
        return self.filter(property_for__in=['B', 'S'])
    
    def for_rent(self):
        return self.filter(property_for__in=['R', 'L'])
    
    def active(self):
        return self.filter(property_status__in=['published', 'approved'])
    
    def nearby(self, point, radius_km=10):
        if not point:
            return self.none()
        return self.filter(
            location_point__distance_lte=(point, D(km=radius_km))
        ).annotate(
            distance=gis_models.Distance('location_point', point)
        ).order_by('distance')
    
    def with_price_range(self, min_price=None, max_price=None):
        queryset = self
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        return queryset
    
    def by_property_type(self, property_types):
        if not property_types:
            return self
        return self.filter(listing_type__property_type__in=property_types)
    
    def by_state(self, state):
        return self.filter(state=state)
    
    def by_lga(self, lga):
        return self.filter(lga__iexact=lga)
    
    def land_properties(self):
        land_types = ['land', 'commercial_land', 'residential_land', 'agricultural_land', 'industrial_land']
        return self.filter(listing_type__property_type__in=land_types)
    
    def with_legal_documents(self):
        return self.filter(Q(has_c_of_o=True) | Q(has_governors_consent=True))
    
    def by_land_size_range(self, min_size=None, max_size=None, unit=None):
        queryset = self
        if min_size is not None:
            queryset = queryset.filter(land_size__gte=min_size)
        if max_size is not None:
            queryset = queryset.filter(land_size__lte=max_size)
        if unit is not None:
            queryset = queryset.filter(land_unit=unit)
        return queryset


class ListingManager(models.Manager):
    def get_queryset(self):
        return ListingQuerySet(self.model, using=self._db)
    
    def published(self):
        return self.get_queryset().published()
    
    def for_sale(self):
        return self.get_queryset().for_sale()
    
    def for_rent(self):
        return self.get_queryset().for_rent()
    
    def active(self):
        return self.get_queryset().active()
    
    def nearby(self, point, radius_km=10):
        return self.get_queryset().nearby(point, radius_km)
    
    def search(self, query_params):
        queryset = self.get_queryset().published()
        
        if 'location_point' in query_params and 'radius_km' in query_params:
            queryset = queryset.nearby(query_params['location_point'], query_params['radius_km'])
        
        queryset = queryset.with_price_range(
            query_params.get('min_price'),
            query_params.get('max_price')
        )
        
        if 'property_types' in query_params:
            queryset = queryset.by_property_type(query_params['property_types'])
        
        if 'min_bedrooms' in query_params:
            queryset = queryset.filter(bedrooms__gte=query_params['min_bedrooms'])
        
        if 'min_bathrooms' in query_params:
            queryset = queryset.filter(bathrooms__gte=query_params['min_bathrooms'])
        
        return queryset
    
    def search_nigerian_properties(self, search_params):
        queryset = self.get_queryset().published()
        
        if 'state' in search_params:
            queryset = queryset.by_state(search_params['state'])
        if 'lga' in search_params:
            queryset = queryset.by_lga(search_params['lga'])
        
        if 'property_type' in search_params:
            if search_params['property_type'] == 'land':
                queryset = queryset.land_properties()
            else:
                queryset = queryset.filter(listing_type__property_type=search_params['property_type'])
        
        if 'min_land_size' in search_params or 'max_land_size' in search_params:
            queryset = queryset.by_land_size_range(
                search_params.get('min_land_size'),
                search_params.get('max_land_size'),
                search_params.get('land_unit')
            )
        
        if search_params.get('has_legal_docs'):
            queryset = queryset.with_legal_documents()
        
        return queryset


class AgentQuerySet(models.QuerySet):
    def verified(self):
        return self.filter(is_verified=True)
    
    def by_specialization(self, specialization):
        return self.filter(specialization__contains=[specialization])
    
    def by_language(self, language):
        return self.filter(languages__contains=[language])
    
    def with_listings_count(self):
        return self.annotate(listings_count=Count('listings_agent'))
    
    def with_rating(self):
        return self.annotate(avg_rating=Avg('ratings__rating'))
    
    def top_performing(self, limit=10):
        return self.verified().annotate(
            listings_count=Count('listings_agent'),
            avg_rating=Avg('ratings__rating')
        ).order_by('-listings_count', '-avg_rating')[:limit]
    
    def nearby(self, point, radius_km=10):
        if not point:
            return self.none()
        return self.filter(location_point__distance_lte=(point, D(km=radius_km)))


class AgentManager(models.Manager):
    def get_queryset(self):
        return AgentQuerySet(self.model, using=self._db)
    
    def verified(self):
        return self.get_queryset().verified()
    
    def by_specialization(self, specialization):
        return self.get_queryset().by_specialization(specialization)
    
    def by_language(self, language):
        return self.get_queryset().by_language(language)
    
    def with_listings_count(self):
        return self.get_queryset().with_listings_count()
    
    def with_rating(self):
        return self.get_queryset().with_rating()
    
    def top_performing(self, limit=10):
        return self.get_queryset().top_performing(limit)
    
    def nearby(self, point, radius_km=10):
        return self.get_queryset().nearby(point, radius_km)