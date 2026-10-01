import numpy as np
from django.db import models
from django.db.models import Q, Count
from django.utils import timezone
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class RiderCompatibility:
    """
    Calculate rider compatibility for shared trips based on multiple factors
    including interstate travel preferences and locations
    """
    
    def __init__(self, weights=None):
        # Default weights for different compatibility factors
        self.weights = weights or {
            'preferences': 0.25,
            'ratings': 0.2,
            'behavior': 0.15,
            'demographics': 0.1,
            'trip_details': 0.1,
            'interstate_routes': 0.2  # New weight for interstate compatibility
        }
    
    def find_compatible_groups(self, trip):
        """
        Find compatible rider groups for a shared trip with interstate support
        """
        try:
            # Get all bookings for this trip
            from .models import Booking
            bookings = Booking.objects.filter(
                service_request=trip,
                status__in=['confirmed', 'active']
            ).select_related('user')
            
            if not bookings:
                return self._create_empty_clusters(trip)
            
            riders = [booking.user for booking in bookings]
            
            # Calculate compatibility matrix with interstate support
            compatibility_matrix = self._calculate_compatibility_matrix(riders, trip)
            
            # Cluster riders based on compatibility
            clusters = self._cluster_riders(riders, compatibility_matrix)
            
            # Generate seating suggestions
            clusters_with_seating = self._suggest_seating(clusters, trip)
            
            return clusters_with_seating
            
        except Exception as e:
            logger.error(f"Error finding compatible groups for trip {trip.id}: {str(e)}")
            return self._create_empty_clusters(trip)
    
    def _calculate_compatibility_matrix(self, riders, trip):
        """Calculate pairwise compatibility scores between riders with trip context"""
        n = len(riders)
        matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                score = self._calculate_pairwise_compatibility(riders[i], riders[j], trip)
                matrix[i][j] = score
                matrix[j][i] = score
        
        return matrix
    
    def _calculate_pairwise_compatibility(self, rider1, rider2, trip):
        """Calculate compatibility score between two riders with trip context"""
        scores = {}
        
        # 1. Preference compatibility
        scores['preferences'] = self._calculate_preference_compatibility(rider1, rider2)
        
        # 2. Rating compatibility
        scores['ratings'] = self._calculate_rating_compatibility(rider1, rider2)
        
        # 3. Behavior compatibility
        scores['behavior'] = self._calculate_behavior_compatibility(rider1, rider2)
        
        # 4. Demographic compatibility
        scores['demographics'] = self._calculate_demographic_compatibility(rider1, rider2)
        
        # 5. Trip detail compatibility
        scores['trip_details'] = self._calculate_trip_detail_compatibility(rider1, rider2)
        
        # 6. Interstate route compatibility (NEW)
        scores['interstate_routes'] = self._calculate_interstate_compatibility(rider1, rider2, trip)
        
        # Weighted sum
        total_score = sum(scores[factor] * self.weights[factor] 
                         for factor in scores)
        
        return total_score
    
    def _calculate_interstate_compatibility(self, rider1, rider2, trip):
        """
        Calculate compatibility based on interstate travel routes and preferences
        """
        try:
            from .models import Booking, ServiceRequest
            
            # Get recent interstate trips for both riders
            rider1_trips = ServiceRequest.objects.filter(
                Q(bookings__user=rider1) &
                Q(service_type='interstate') &
                Q(status__in=['completed', 'in_progress'])
            ).select_related('pickup_address', 'dropoff_address')
            
            rider2_trips = ServiceRequest.objects.filter(
                Q(bookings__user=rider2) &
                Q(service_type='interstate') &
                Q(status__in=['completed', 'in_progress'])
            ).select_related('pickup_address', 'dropoff_address')
            
            compatibility_score = 0.0
            factors_considered = 0
            
            # 1. Current trip route compatibility
            current_trip_compatibility = self._calculate_current_trip_compatibility(rider1, rider2, trip)
            if current_trip_compatibility is not None:
                compatibility_score += current_trip_compatibility
                factors_considered += 1
            
            # 2. Historical route preference compatibility
            route_pref_compatibility = self._calculate_route_preference_compatibility(rider1_trips, rider2_trips)
            if route_pref_compatibility is not None:
                compatibility_score += route_pref_compatibility
                factors_considered += 1
            
            # 3. Terminal preference compatibility
            terminal_compatibility = self._calculate_terminal_compatibility(rider1_trips, rider2_trips)
            if terminal_compatibility is not None:
                compatibility_score += terminal_compatibility
                factors_considered += 1
            
            return compatibility_score / factors_considered if factors_considered > 0 else 0.7
            
        except Exception as e:
            logger.error(f"Error calculating interstate compatibility: {str(e)}")
            return 0.7
    
    def _calculate_current_trip_compatibility(self, rider1, rider2, trip):
        """
        Calculate compatibility based on current trip's interstate route
        """
        try:
            # Check if this is an interstate trip
            if not hasattr(trip, 'departure_state') or not trip.departure_state:
                return 0.5  # Default for non-interstate trips
            
            score = 0.0
            factors = 0
            
            # Departure state compatibility
            if trip.departure_state:
                # Riders from same departure state get higher compatibility
                rider1_departure_match = self._rider_has_state_history(rider1, trip.departure_state, is_departure=True)
                rider2_departure_match = self._rider_has_state_history(rider2, trip.departure_state, is_departure=True)
                
                if rider1_departure_match and rider2_departure_match:
                    score += 1.0
                elif rider1_departure_match or rider2_departure_match:
                    score += 0.7
                else:
                    score += 0.3
                factors += 1
            
            # Destination state compatibility
            if trip.destination_state:
                # Riders with same destination state get higher compatibility
                rider1_destination_match = self._rider_has_state_history(rider1, trip.destination_state, is_departure=False)
                rider2_destination_match = self._rider_has_state_history(rider2, trip.destination_state, is_departure=False)
                
                if rider1_destination_match and rider2_destination_match:
                    score += 1.0
                elif rider1_destination_match or rider2_destination_match:
                    score += 0.7
                else:
                    score += 0.3
                factors += 1
            
            # City-level compatibility
            if trip.departure_city and trip.destination_city:
                city_compatibility = self._calculate_city_level_compatibility(rider1, rider2, trip)
                score += city_compatibility
                factors += 1
            
            # Terminal compatibility
            if trip.departure_terminal or trip.destination_terminal:
                terminal_compatibility = self._calculate_terminal_preference_compatibility(rider1, rider2, trip)
                score += terminal_compatibility
                factors += 1
            
            return score / factors if factors > 0 else 0.7
            
        except Exception as e:
            logger.error(f"Error calculating current trip compatibility: {str(e)}")
            return 0.7
    
    def _rider_has_state_history(self, rider, state, is_departure=True):
        """
        Check if rider has historical trips from/to this state
        """
        try:
            from .models import ServiceRequest, Booking
            
            field_to_check = 'departure_state' if is_departure else 'destination_state'
            
            has_history = ServiceRequest.objects.filter(
                Q(bookings__user=rider) &
                Q(**{f'{field_to_check}__iexact': state}) &
                Q(service_type='interstate') &
                Q(status='completed')
            ).exists()
            
            return has_history
            
        except Exception as e:
            logger.error(f"Error checking rider state history: {str(e)}")
            return False
    
    def _calculate_city_level_compatibility(self, rider1, rider2, trip):
        """
        Calculate compatibility at city level for interstate travel
        """
        try:
            from .models import ServiceRequest, Booking
            
            score = 0.0
            factors = 0
            
            # Departure city compatibility
            if trip.departure_city:
                rider1_dep_city = ServiceRequest.objects.filter(
                    Q(bookings__user=rider1) &
                    Q(departure_city__iexact=trip.departure_city) &
                    Q(service_type='interstate')
                ).exists()
                
                rider2_dep_city = ServiceRequest.objects.filter(
                    Q(bookings__user=rider2) &
                    Q(departure_city__iexact=trip.departure_city) &
                    Q(service_type='interstate')
                ).exists()
                
                if rider1_dep_city and rider2_dep_city:
                    score += 1.0
                elif rider1_dep_city or rider2_dep_city:
                    score += 0.6
                else:
                    score += 0.3
                factors += 1
            
            # Destination city compatibility
            if trip.destination_city:
                rider1_dest_city = ServiceRequest.objects.filter(
                    Q(bookings__user=rider1) &
                    Q(destination_city__iexact=trip.destination_city) &
                    Q(service_type='interstate')
                ).exists()
                
                rider2_dest_city = ServiceRequest.objects.filter(
                    Q(bookings__user=rider2) &
                    Q(destination_city__iexact=trip.destination_city) &
                    Q(service_type='interstate')
                ).exists()
                
                if rider1_dest_city and rider2_dest_city:
                    score += 1.0
                elif rider1_dest_city or rider2_dest_city:
                    score += 0.6
                else:
                    score += 0.3
                factors += 1
            
            return score / factors if factors > 0 else 0.5
            
        except Exception as e:
            logger.error(f"Error calculating city level compatibility: {str(e)}")
            return 0.5
    
    def _calculate_terminal_preference_compatibility(self, rider1, rider2, trip):
        """
        Calculate compatibility based on terminal preferences
        """
        try:
            from .models import ServiceRequest, Booking
            
            score = 0.0
            factors = 0
            
            # Departure terminal compatibility
            if trip.departure_terminal:
                rider1_dep_terminal = ServiceRequest.objects.filter(
                    Q(bookings__user=rider1) &
                    Q(departure_terminal__iexact=trip.departure_terminal) &
                    Q(service_type='interstate')
                ).exists()
                
                rider2_dep_terminal = ServiceRequest.objects.filter(
                    Q(bookings__user=rider2) &
                    Q(departure_terminal__iexact=trip.departure_terminal) &
                    Q(service_type='interstate')
                ).exists()
                
                if rider1_dep_terminal and rider2_dep_terminal:
                    score += 1.0
                elif rider1_dep_terminal or rider2_dep_terminal:
                    score += 0.7
                else:
                    score += 0.4
                factors += 1
            
            # Destination terminal compatibility
            if trip.destination_terminal:
                rider1_dest_terminal = ServiceRequest.objects.filter(
                    Q(bookings__user=rider1) &
                    Q(destination_terminal__iexact=trip.destination_terminal) &
                    Q(service_type='interstate')
                ).exists()
                
                rider2_dest_terminal = ServiceRequest.objects.filter(
                    Q(bookings__user=rider2) &
                    Q(destination_terminal__iexact=trip.destination_terminal) &
                    Q(service_type='interstate')
                ).exists()
                
                if rider1_dest_terminal and rider2_dest_terminal:
                    score += 1.0
                elif rider1_dest_terminal or rider2_dest_terminal:
                    score += 0.7
                else:
                    score += 0.4
                factors += 1
            
            return score / factors if factors > 0 else 0.5
            
        except Exception as e:
            logger.error(f"Error calculating terminal compatibility: {str(e)}")
            return 0.5
    
    def _calculate_route_preference_compatibility(self, rider1_trips, rider2_trips):
        """
        Calculate compatibility based on historical route preferences
        """
        try:
            if not rider1_trips or not rider2_trips:
                return 0.5
            
            # Extract common routes
            rider1_routes = set()
            for trip in rider1_trips:
                if trip.departure_state and trip.destination_state:
                    route = f"{trip.departure_state}_{trip.destination_state}"
                    rider1_routes.add(route)
            
            rider2_routes = set()
            for trip in rider2_trips:
                if trip.departure_state and trip.destination_state:
                    route = f"{trip.departure_state}_{trip.destination_state}"
                    rider2_routes.add(route)
            
            if not rider1_routes or not rider2_routes:
                return 0.5
            
            # Calculate Jaccard similarity for routes
            intersection = rider1_routes.intersection(rider2_routes)
            union = rider1_routes.union(rider2_routes)
            
            if not union:
                return 0.5
            
            similarity = len(intersection) / len(union)
            return similarity
            
        except Exception as e:
            logger.error(f"Error calculating route preference compatibility: {str(e)}")
            return 0.5
    
    def _calculate_terminal_compatibility(self, rider1_trips, rider2_trips):
        """
        Calculate compatibility based on terminal usage patterns
        """
        try:
            if not rider1_trips or not rider2_trips:
                return 0.5
            
            rider1_terminals = set()
            rider2_terminals = set()
            
            for trip in rider1_trips:
                if trip.departure_terminal:
                    rider1_terminals.add(trip.departure_terminal.lower())
                if trip.destination_terminal:
                    rider1_terminals.add(trip.destination_terminal.lower())
            
            for trip in rider2_trips:
                if trip.departure_terminal:
                    rider2_terminals.add(trip.departure_terminal.lower())
                if trip.destination_terminal:
                    rider2_terminals.add(trip.destination_terminal.lower())
            
            if not rider1_terminals or not rider2_terminals:
                return 0.5
            
            # Calculate terminal preference similarity
            intersection = rider1_terminals.intersection(rider2_terminals)
            union = rider1_terminals.union(rider2_terminals)
            
            similarity = len(intersection) / len(union) if union else 0.5
            return similarity
            
        except Exception as e:
            logger.error(f"Error calculating terminal compatibility: {str(e)}")
            return 0.5

    # ... (keep all the existing methods from the original class unchanged)
    # _calculate_preference_compatibility, _calculate_rating_compatibility, 
    # _calculate_behavior_compatibility, _calculate_demographic_compatibility,
    # _calculate_trip_detail_compatibility, _cluster_riders, _find_shared_interests,
    # _suggest_seating, _create_empty_clusters

    def get_interstate_compatibility_breakdown(self, rider1, rider2, trip):
        """
        Get detailed breakdown of interstate compatibility factors
        """
        breakdown = {
            'current_trip_compatibility': self._calculate_current_trip_compatibility(rider1, rider2, trip),
            'route_preference_compatibility': self._calculate_route_preference_compatibility(
                self._get_rider_trips(rider1), self._get_rider_trips(rider2)
            ),
            'terminal_compatibility': self._calculate_terminal_compatibility(
                self._get_rider_trips(rider1), self._get_rider_trips(rider2)
            ),
            'city_level_compatibility': self._calculate_city_level_compatibility(rider1, rider2, trip)
        }
        
        breakdown['overall_interstate_score'] = sum(breakdown.values()) / len(breakdown)
        return breakdown
    
    def _get_rider_trips(self, rider):
        """Helper method to get rider's interstate trips"""
        from .models import ServiceRequest, Booking
        
        return ServiceRequest.objects.filter(
            Q(bookings__user=rider) &
            Q(service_type='interstate') &
            Q(status__in=['completed', 'in_progress'])
        ).select_related('pickup_address', 'dropoff_address')