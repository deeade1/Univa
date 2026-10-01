# recommendations.py
import math

import pandas as pd
from django.contrib.gis.geos import Point
from django.db.models import F, Q
# recommendations.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class PropertyRecommender:
    def __init__(self, client):  # Changed from buyer_profile to client
        self.client = client
    
    def get_recommendations(self, max_results=10):
        """Get personalized property recommendations"""
        # The rest of the implementation can remain the same
        # since it uses attributes that now exist on the Client model
        base_query = self._get_base_query()
        
        # Score properties based on multiple factors
        scored_properties = base_query.annotate(
            proximity_score=F('proximities__score'),
            price_score=self._get_price_score(),
            type_score=self._get_type_score(),
            total_score=(
                F('proximity_score') +
                F('price_score') +
                F('type_score')
            )
        ).order_by('-total_score')[:max_results]
        
        return scored_properties
    
    def _get_base_query(self):
        """Base query for properties within search radius"""
        from .models import Listing
        
        return Listing.objects.filter(
            address__location__distance_lte=(
                self.client.location_point,  # Now using client's location
                D(km=self.client.search_radius_km)  # Now using client's search radius
            ),
            is_published=True
        )
    
    def _get_price_score(self):
        """Calculate score based on price match to client's budget"""
        from django.db.models import Case, IntegerField, Value, When
        
        if not self.client.price_range_min or not self.client.price_range_max:
            return Value(0, output_field=IntegerField())
        
        min_price = self.client.price_range_min
        max_price = self.client.price_range_max
        
        return Case(
            When(
                price__gte=min_price,
                price__lte=max_price,
                then=Value(50)
            ),
            # ... rest of the implementation
        )
    
    def _get_type_score(self):
        """Calculate score based on property type preferences"""
        from django.db.models import Case, IntegerField, Value, When
        
        if not self.client.preferred_property_types:
            return Value(0, output_field=IntegerField())
        
        cases = []
        for i, prop_type in enumerate(self.client.preferred_property_types):
            score = 30 - (i * 5)
            cases.append(
                When(listing_type__property_type=prop_type, then=Value(score))
            )
        
        return Case(
            *cases,
            default=Value(0),
            output_field=IntegerField()
        )




class AIPropertyRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        
    def train(self, properties):
        """Train recommendation model on property features"""
        features = [
            f"{p.title} {p.description} {p.listing_type} {', '.join([t.name for t in p.tags.all()])}"
            for p in properties
        ]
        self.tfidf_matrix = self.vectorizer.fit_transform(features)
        self.property_ids = [p.id for p in properties]
        
    def recommend(self, property_id, num_recommendations=5):
        """Get similar properties based on content"""
        idx = self.property_ids.index(property_id)
        sim_scores = cosine_similarity(self.tfidf_matrix[idx], self.tfidf_matrix)
        sim_scores = sim_scores.flatten()
        rec_indices = sim_scores.argsort()[-num_recommendations-1:-1][::-1]
        return [self.property_ids[i] for i in rec_indices]