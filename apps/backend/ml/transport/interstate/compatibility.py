# ml/transport/interstate/compatibility.py
"""
Interstate compatibility system - Simplified and refactored.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


@dataclass
class InterstateTrip:
    """Interstate trip request."""
    trip_id: str
    user_id: str
    departure_city: str
    destination_city: str
    departure_time: datetime
    passengers: int
    max_group_size: int = 4


@dataclass
class TravelerProfile:
    """Traveler profile for matching."""
    user_id: str
    route_preferences: Dict
    time_preferences: Dict
    social_preferences: Dict
    historical_trips: List[Dict]


class InterstateCompatibilityEngine:
    """
    ML-powered compatibility engine for interstate passenger matching.
    """
    
    def __init__(self, ml_enabled: bool = True):
        self.ml_enabled = ml_enabled
        self._scaler = StandardScaler()
        self._profiles = {}
        self._models = {}
    
    def find_compatible_groups(
        self,
        trips: List[InterstateTrip],
        max_group_size: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Find compatible groups of travelers for interstate trips.
        
        Args:
            trips: List of trip requests
            max_group_size: Maximum group size
        
        Returns:
            List of compatible groups with scores and details
        """
        if len(trips) < 2:
            return self._single_trip_groups(trips)
        
        # Group by route
        route_groups = self._group_by_route(trips)
        
        compatible_groups = []
        for route, route_trips in route_groups.items():
            if len(route_trips) < 2:
                compatible_groups.extend(self._single_trip_groups(route_trips))
                continue
            
            # Calculate compatibility matrix
            matrix = self._calculate_compatibility_matrix(route_trips)
            
            # Find optimal groups
            groups = self._cluster_into_groups(route_trips, matrix, max_group_size)
            compatible_groups.extend(groups)
        
        return compatible_groups
    
    def _calculate_compatibility_matrix(
        self,
        trips: List[InterstateTrip]
    ) -> np.ndarray:
        """Calculate pairwise compatibility matrix."""
        n = len(trips)
        matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                score = self._calculate_pairwise_score(trips[i], trips[j])
                matrix[i][j] = score
                matrix[j][i] = score
        
        return matrix
    
    def _calculate_pairwise_score(
        self,
        trip1: InterstateTrip,
        trip2: InterstateTrip
    ) -> float:
        """Calculate compatibility score between two trips."""
        scores = []
        
        # Time compatibility (0-1)
        time_diff = abs(
            (trip1.departure_time - trip2.departure_time).total_seconds()
        ) / 3600  # hours
        
        time_score = max(0, 1 - time_diff / 2)  # 2 hour window
        scores.append(time_score * 0.3)
        
        # Route compatibility (0-1)
        route_score = 1.0 if (
            trip1.departure_city == trip2.departure_city and
            trip1.destination_city == trip2.destination_city
        ) else 0.0
        scores.append(route_score * 0.3)
        
        # Size compatibility (0-1)
        total_passengers = trip1.passengers + trip2.passengers
        max_size = min(trip1.max_group_size, trip2.max_group_size)
        size_score = 1.0 if total_passengers <= max_size else 0.5
        scores.append(size_score * 0.2)
        
        # Profile compatibility (if available)
        profile_score = self._get_profile_compatibility(
            trip1.user_id, trip2.user_id
        )
        scores.append(profile_score * 0.2)
        
        return sum(scores)
    
    def _get_profile_compatibility(self, user1: str, user2: str) -> float:
        """Get compatibility score from user profiles."""
        profile1 = self._profiles.get(user1)
        profile2 = self._profiles.get(user2)
        
        if not profile1 or not profile2:
            return 0.5
        
        # Compare social preferences
        social1 = profile1.social_preferences
        social2 = profile2.social_preferences
        
        conv_diff = abs(
            social1.get('conversation_preference', 0.5) -
            social2.get('conversation_preference', 0.5)
        )
        
        return max(0, 1 - conv_diff)