# core/services/routing.py

"""
CANONICAL Routing Service

Used by:
    • Transport (Ride, Logistics, Delivery)
    • Real Estate
    • Banking
    • Marketplace
    • All other apps requiring routing functionality

Responsibilities:
    ✓ Route calculation
    ✓ Distance calculation (Haversine)
    ✓ ETA estimation
    ✓ Route optimization (TSP with Google Maps)
    ✓ Route summaries
    ✓ Provider abstraction

Current Providers:
    • Haversine (always available - fallback)
    • Google Maps (optional - requires API key)

Future Providers:
    • OSRM
    • HERE
    • GraphHopper
    • Mapbox
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any, Union

from django.conf import settings

# =============================================================================
# Constants
# =============================================================================

EARTH_RADIUS_KM = 6371.0088
DEFAULT_AVG_SPEED_KMH = 40  # Urban average speed

# =============================================================================
# Distance Calculations (Haversine)
# =============================================================================

def haversine_distance(
    lat1: Union[float, str, Decimal],
    lon1: Union[float, str, Decimal],
    lat2: Union[float, str, Decimal],
    lon2: Union[float, str, Decimal],
) -> float:
    """
    Calculate straight-line (great-circle) distance using Haversine formula.
    
    Args:
        lat1: Start latitude
        lon1: Start longitude
        lat2: End latitude
        lon2: End longitude
    
    Returns:
        float: Distance in kilometers
    
    Example:
        >>> haversine_distance(40.7128, -74.0060, 40.7580, -73.9855)
        5.29
    """
    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return EARTH_RADIUS_KM * c


def trip_distance(
    origin: Tuple[float, float],
    destination: Tuple[float, float],
) -> float:
    """
    Calculate distance between two points.
    
    Args:
        origin: (lat, lon)
        destination: (lat, lon)
    
    Returns:
        float: Distance in kilometers
    """
    return haversine_distance(
        origin[0], origin[1],
        destination[0], destination[1],
    )


def within_radius(
    origin: Tuple[float, float],
    destination: Tuple[float, float],
    radius_km: float = 5,
) -> bool:
    """
    Check if destination is within radius of origin.
    
    Args:
        origin: (lat, lon)
        destination: (lat, lon)
        radius_km: Radius in kilometers
    
    Returns:
        bool: True if within radius
    """
    distance = trip_distance(origin, destination)
    return distance <= radius_km


# =============================================================================
# ETA Calculations
# =============================================================================

def estimate_eta(
    distance_km: float,
    average_speed_kmh: float = DEFAULT_AVG_SPEED_KMH,
) -> Optional[int]:
    """
    Estimate travel time in minutes.
    
    Args:
        distance_km: Distance in kilometers
        average_speed_kmh: Average speed in km/h (default: 40)
    
    Returns:
        int: Estimated minutes, or None if speed is invalid
    """
    if average_speed_kmh <= 0:
        return None

    hours = distance_km / average_speed_kmh
    return round(hours * 60)


def estimate_eta_with_traffic(
    distance_km: float,
    base_speed_kmh: float = DEFAULT_AVG_SPEED_KMH,
    traffic_factor: float = 1.0,
) -> Optional[int]:
    """
    Estimate travel time with traffic consideration.
    
    Args:
        distance_km: Distance in kilometers
        base_speed_kmh: Base average speed in km/h
        traffic_factor: Traffic multiplier (1.0 = normal, >1.0 = more traffic)
    
    Returns:
        int: Estimated minutes, or None if speed is invalid
    """
    adjusted_speed = base_speed_kmh / traffic_factor
    return estimate_eta(distance_km, adjusted_speed)


# =============================================================================
# Route Information
# =============================================================================

def get_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    average_speed_kmh: float = DEFAULT_AVG_SPEED_KMH,
) -> Dict[str, Any]:
    """
    Get basic route information using Haversine calculation.
    
    This is the fallback method when no external provider is available.
    
    Args:
        start_lat: Start latitude
        start_lon: Start longitude
        end_lat: End latitude
        end_lon: End longitude
        average_speed_kmh: Average speed for ETA calculation
    
    Returns:
        dict: Route information with distance, ETA, etc.
    
    Example:
        >>> get_route(40.7128, -74.0060, 40.7580, -73.9855)
        {
            "provider": "haversine",
            "distance_km": 5.29,
            "estimated_minutes": 8,
            "polyline": None,
            "steps": [],
            "source": "haversine"
        }
    """
    distance = haversine_distance(start_lat, start_lon, end_lat, end_lon)
    eta = estimate_eta(distance, average_speed_kmh)

    return {
        "provider": "haversine",
        "source": "haversine",
        "distance_km": round(distance, 2),
        "estimated_minutes": eta,
        "polyline": None,
        "steps": [],
        "start": (start_lat, start_lon),
        "end": (end_lat, end_lon),
    }


def get_route_with_provider(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    provider: str = "haversine",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get route information using specified provider.
    
    Args:
        start_lat: Start latitude
        start_lon: Start longitude
        end_lat: End latitude
        end_lon: End longitude
        provider: Provider to use ('haversine', 'google')
        api_key: API key for external providers
    
    Returns:
        dict: Route information
    
    Raises:
        ValueError: If provider is unknown
        ImportError: If required provider dependencies are missing
    """
    if provider == "haversine":
        return get_route(start_lat, start_lon, end_lat, end_lon)
    
    elif provider == "google":
        if not api_key:
            api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        if not api_key:
            raise ValueError("Google Maps API key is required")
        
        optimizer = RouteOptimizer(api_key)
        return optimizer.get_route_details(
            (start_lat, start_lon),
            (end_lat, end_lon)
        )
    
    else:
        raise ValueError(f"Unknown provider: {provider}")


# =============================================================================
# Route Optimization (TSP with Google Maps)
# =============================================================================

class RouteOptimizer:
    """
    Optimize routes with multiple stops using Traveling Salesman Problem solution.
    
    Uses Google Maps Distance Matrix API for distances between stops.
    Falls back to Haversine if Google Maps is unavailable.
    
    Example:
        >>> optimizer = RouteOptimizer(api_key="your_api_key")
        >>> stops = [(40.7128, -74.0060), (40.7580, -73.9855), (40.7614, -73.9776)]
        >>> result = optimizer.optimize_route(stops)
        >>> print(result['distance'], result['duration'])
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize RouteOptimizer.
        
        Args:
            api_key: Google Maps API key (optional - will use settings if not provided)
        """
        self.api_key = api_key or getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        self._gmaps = None
        
        if self.api_key:
            try:
                import googlemaps
                self._gmaps = googlemaps.Client(key=self.api_key)
            except ImportError:
                self._gmaps = None
    
    @property
    def google_available(self) -> bool:
        """Check if Google Maps API is available."""
        return self._gmaps is not None
    
    def optimize_route(
        self,
        stops: List[Tuple[float, float]],
        vehicle_type: str = 'car',
        use_google: bool = True,
    ) -> Dict[str, Any]:
        """
        Optimize delivery route with multiple stops.
        
        Args:
            stops: List of (latitude, longitude) points
            vehicle_type: Type of vehicle ('car', 'truck', 'bicycle', etc.)
            use_google: Use Google Maps API if available
        
        Returns:
            dict: Optimized route with order, distance, duration
        
        Example:
            >>> stops = [(40.7128, -74.0060), (40.7580, -73.9855), (40.7614, -73.9776)]
            >>> result = optimizer.optimize_route(stops)
            >>> result['route']  # List of optimized stop indices
            [0, 2, 1]  # Optimized order
        """
        if len(stops) < 2:
            return {
                'route': list(range(len(stops))),
                'distance': 0,
                'duration': 0,
                'vehicle_type': vehicle_type,
                'provider': 'haversine'
            }
        
        # Try Google Maps if available
        if use_google and self.google_available:
            try:
                return self._optimize_with_google(stops, vehicle_type)
            except Exception as e:
                # Fall back to Haversine
                print(f"Google Maps optimization failed: {e}. Falling back to Haversine.")
                return self._optimize_with_haversine(stops, vehicle_type)
        
        # Use Haversine fallback
        return self._optimize_with_haversine(stops, vehicle_type)
    
    def _optimize_with_google(self, stops: List[Tuple[float, float]], vehicle_type: str) -> Dict[str, Any]:
        """Optimize using Google Maps Distance Matrix API."""
        # Convert stops to strings for API
        origins = [f"{lat},{lng}" for lat, lng in stops]
        
        # Get distance matrix
        distance_matrix = self._gmaps.distance_matrix(
            origins=origins,
            destinations=origins,
            mode='driving',
            departure_time=datetime.now(),
            traffic_model='best_guess'
        )
        
        # Parse distance matrix
        n = len(stops)
        dist_matrix = []
        for i in range(n):
            row = []
            for j in range(n):
                try:
                    element = distance_matrix['rows'][i]['elements'][j]
                    if element['status'] == 'OK':
                        row.append({
                            'distance_meters': element['distance']['value'],
                            'duration_seconds': element['duration']['value'],
                        })
                    else:
                        # Fallback to Haversine for failed elements
                        dist = haversine_distance(
                            stops[i][0], stops[i][1],
                            stops[j][0], stops[j][1]
                        )
                        row.append({
                            'distance_meters': dist * 1000,
                            'duration_seconds': (dist / DEFAULT_AVG_SPEED_KMH) * 3600,
                        })
                except (KeyError, IndexError):
                    # Fallback to Haversine
                    dist = haversine_distance(
                        stops[i][0], stops[i][1],
                        stops[j][0], stops[j][1]
                    )
                    row.append({
                        'distance_meters': dist * 1000,
                        'duration_seconds': (dist / DEFAULT_AVG_SPEED_KMH) * 3600,
                    })
            dist_matrix.append(row)
        
        # Solve TSP
        route_indices = self._solve_tsp(dist_matrix)
        
        # Calculate totals
        total_distance_m = 0
        total_duration_s = 0
        
        for i in range(len(route_indices) - 1):
            origin_idx = route_indices[i]
            dest_idx = route_indices[i + 1]
            total_distance_m += dist_matrix[origin_idx][dest_idx]['distance_meters']
            total_duration_s += dist_matrix[origin_idx][dest_idx]['duration_seconds']
        
        return {
            'route': route_indices,
            'distance': total_distance_m,  # meters
            'distance_km': round(total_distance_m / 1000, 2),  # kilometers
            'duration': total_duration_s,  # seconds
            'duration_minutes': round(total_duration_s / 60, 1),  # minutes
            'vehicle_type': vehicle_type,
            'provider': 'google_maps',
            'stops': stops,
        }
    
    def _optimize_with_haversine(self, stops: List[Tuple[float, float]], vehicle_type: str) -> Dict[str, Any]:
        """Optimize using Haversine distance (fallback)."""
        n = len(stops)
        
        # Build distance matrix using Haversine
        dist_matrix = []
        for i in range(n):
            row = []
            for j in range(n):
                if i == j:
                    row.append(0)
                else:
                    dist = haversine_distance(
                        stops[i][0], stops[i][1],
                        stops[j][0], stops[j][1]
                    )
                    row.append(dist)
            dist_matrix.append(row)
        
        # Solve TSP
        route_indices = self._solve_tsp_simple(dist_matrix)
        
        # Calculate totals
        total_distance_km = 0
        for i in range(len(route_indices) - 1):
            origin_idx = route_indices[i]
            dest_idx = route_indices[i + 1]
            total_distance_km += dist_matrix[origin_idx][dest_idx]
        
        avg_speed = 40 if vehicle_type == 'car' else 25  # km/h
        total_duration_minutes = estimate_eta(total_distance_km, avg_speed)
        
        return {
            'route': route_indices,
            'distance': total_distance_km * 1000,  # meters
            'distance_km': round(total_distance_km, 2),  # kilometers
            'duration': total_duration_minutes * 60 if total_duration_minutes else 0,  # seconds
            'duration_minutes': total_duration_minutes or 0,  # minutes
            'vehicle_type': vehicle_type,
            'provider': 'haversine',
            'stops': stops,
        }
    
    def _solve_tsp(self, distance_matrix: List[List[Dict[str, float]]]) -> List[int]:
        """
        Solve TSP using nearest neighbor algorithm.
        
        Args:
            distance_matrix: Matrix of distance/duration dictionaries
        
        Returns:
            list: Optimized route indices
        """
        n = len(distance_matrix)
        unvisited = set(range(n))
        route = [0]
        unvisited.remove(0)
        
        while unvisited:
            last = route[-1]
            nearest = min(
                unvisited,
                key=lambda x: distance_matrix[last][x]['distance_meters']
            )
            route.append(nearest)
            unvisited.remove(nearest)
        
        return route
    
    def _solve_tsp_simple(self, distance_matrix: List[List[float]]) -> List[int]:
        """
        Solve TSP using nearest neighbor with simple distance matrix.
        
        Args:
            distance_matrix: Matrix of distances (float)
        
        Returns:
            list: Optimized route indices
        """
        n = len(distance_matrix)
        unvisited = set(range(n))
        route = [0]
        unvisited.remove(0)
        
        while unvisited:
            last = route[-1]
            nearest = min(
                unvisited,
                key=lambda x: distance_matrix[last][x]
            )
            route.append(nearest)
            unvisited.remove(nearest)
        
        return route
    
    def get_route_details(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        waypoints: Optional[List[Tuple[float, float]]] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed route information using Google Maps.
        
        Args:
            origin: (lat, lon)
            destination: (lat, lon)
            waypoints: Optional list of intermediate waypoints
        
        Returns:
            dict: Detailed route information
        """
        if not self.google_available:
            # Fallback to Haversine
            return get_route(
                origin[0], origin[1],
                destination[0], destination[1]
            )
        
        try:
            # Get directions from Google
            directions = self._gmaps.directions(
                origin=f"{origin[0]},{origin[1]}",
                destination=f"{destination[0]},{destination[1]}",
                waypoints=[f"{lat},{lng}" for lat, lng in (waypoints or [])],
                mode='driving',
                departure_time=datetime.now(),
                traffic_model='best_guess'
            )
            
            if not directions:
                # Fallback to Haversine
                return get_route(
                    origin[0], origin[1],
                    destination[0], destination[1]
                )
            
            route = directions[0]
            leg = route['legs'][0]
            
            # Extract route geometry
            polyline = route.get('overview_polyline', {}).get('points', None)
            
            # Extract steps
            steps = []
            for step in leg['steps']:
                steps.append({
                    'instruction': step.get('html_instructions', ''),
                    'distance_km': step['distance']['value'] / 1000,
                    'duration_minutes': step['duration']['value'] / 60,
                    'polyline': step.get('polyline', {}).get('points', None),
                })
            
            return {
                'provider': 'google_maps',
                'source': 'google',
                'distance_km': round(leg['distance']['value'] / 1000, 2),
                'estimated_minutes': round(leg['duration']['value'] / 60, 1),
                'estimated_seconds': leg['duration']['value'],
                'polyline': polyline,
                'steps': steps,
                'start': origin,
                'end': destination,
                'waypoints': waypoints,
                'start_address': leg.get('start_address'),
                'end_address': leg.get('end_address'),
            }
            
        except Exception as e:
            # Fallback to Haversine
            return get_route(
                origin[0], origin[1],
                destination[0], destination[1]
            )


# =============================================================================
# Provider Information
# =============================================================================

def routing_provider() -> str:
    """
    Get the current routing provider.
    
    Returns:
        str: Provider name
    """
    return "Haversine (fallback) / Google Maps (optional)"


def available_providers() -> List[str]:
    """
    Get list of available routing providers.
    
    Returns:
        list: List of available provider names
    """
    providers = ['haversine']
    
    try:
        from googlemaps import Client
        providers.append('google')
    except ImportError:
        pass
    
    return providers


# =============================================================================
# Convenience Functions (Backward Compatible)
# =============================================================================

# Alias for backward compatibility
def get_distance(*args, **kwargs):
    """Backward compatible alias for haversine_distance."""
    return haversine_distance(*args, **kwargs)


def calculate_route(*args, **kwargs):
    """Backward compatible alias for get_route."""
    return get_route(*args, **kwargs)