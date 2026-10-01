# ml/transport/pricing/optimizer.py
"""
ML pricing optimization - Simplified and consolidated.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from django.core.cache import cache
from django.core.validators import MinValueValidator, MaxValueValidator

logger = logging.getLogger(__name__)


@dataclass
class RideContext:
    """Ride pricing context."""
    service_type: str
    distance_km: float
    duration_min: float
    time_of_day: int
    day_of_week: int
    traffic_level: float
    vehicle_type: str
    customer_segment: str


class MLPricingOptimizer:
    """
    ML-powered pricing optimization for rides and deliveries.
    """
    
    def __init__(self):
        self._models = {}
        self._feature_importance = {}
        self._demand_cache = {}
    
    def calculate_optimal_price(
        self,
        context: RideContext,
        base_price: float,
        objective: str = 'revenue'
    ) -> Dict[str, Any]:
        """
        Calculate optimal price using ML.
        
        Args:
            context: Ride pricing context
            base_price: Base price from pricing profile
            objective: Optimization objective
        
        Returns:
            Dict with optimal price and explanation
        """
        cache_key = self._generate_cache_key(context, base_price)
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            # Get demand prediction
            demand = self._predict_demand(context)
            
            # Get price elasticity
            elasticity = self._predict_elasticity(context)
            
            # Calculate optimal price
            optimal_price = self._optimize_price(
                base_price, demand, elasticity, objective
            )
            
            # Calculate surge multiplier
            surge = self._calculate_surge(context, demand)
            
            result = {
                'optimal_price': round(optimal_price, 2),
                'base_price': round(base_price, 2),
                'surge_multiplier': round(surge, 2),
                'expected_demand': demand,
                'confidence': 0.85,
                'explanation': self._generate_explanation(
                    base_price, optimal_price, surge, demand
                ),
            }
            
            cache.set(cache_key, result, 300)  # Cache for 5 minutes
            return result
            
        except Exception as e:
            logger.error(f"Pricing optimization failed: {e}")
            return self._fallback_price(base_price, context)
    
    def _predict_demand(self, context: RideContext) -> float:
        """Predict demand for given context."""
        try:
            model = self._get_model('demand_predictor')
            if model:
                X = self._prepare_demand_features(context)
                return float(model.predict(X)[0])
        except Exception as e:
            logger.error(f"Demand prediction failed: {e}")
        
        return self._estimate_demand(context)
    
    def _predict_elasticity(self, context: RideContext) -> float:
        """Predict price elasticity."""
        # Default elasticities by service type
        elasticities = {
            'taxi': -0.4,
            'delivery': -0.6,
            'shared': -0.8,
            'cargo': -0.3,
        }
        return elasticities.get(context.service_type, -0.5)
    
    def _optimize_price(
        self,
        base_price: float,
        demand: float,
        elasticity: float,
        objective: str
    ) -> float:
        """Optimize price based on demand and elasticity."""
        # Price elasticity formula: Q = a * P^e
        # For revenue maximization: P* = (e/(e+1)) * MC
        
        if elasticity < -1:  # Elastic demand
            optimal_price = base_price * abs(elasticity) / (abs(elasticity) - 1)
        else:  # Inelastic demand
            optimal_price = base_price * (1 + (1 - abs(elasticity)))
        
        # Adjust for demand
        if demand > 1.5:  # High demand
            optimal_price *= 1.1
        elif demand < 0.5:  # Low demand
            optimal_price *= 0.9
        
        # Round to nearest 0.5
        return round(optimal_price * 2) / 2
    
    def _calculate_surge(self, context: RideContext, demand: float) -> float:
        """Calculate surge multiplier."""
        surge = 1.0
        
        # Time-based surge
        hour = context.time_of_day
        if 7 <= hour <= 9 or 16 <= hour <= 19:
            surge *= 1.3
        
        # Weekend surge
        if context.day_of_week >= 5:
            surge *= 1.2
        
        # Demand-based surge
        if demand > 1.5:
            surge *= 1.2
        
        return min(2.5, surge)
    
    def _estimate_demand(self, context: RideContext) -> float:
        """Estimate demand using simple rules."""
        hour = context.time_of_day
        
        if 7 <= hour <= 9 or 16 <= hour <= 19:
            return 1.5 + np.random.uniform(0, 0.5)
        elif 20 <= hour <= 24:
            return 1.2 + np.random.uniform(0, 0.3)
        else:
            return 0.8 + np.random.uniform(0, 0.3)
    
    def _generate_explanation(
        self,
        base_price: float,
        optimal_price: float,
        surge: float,
        demand: float
    ) -> List[str]:
        """Generate human-readable explanation."""
        explanations = []
        
        if surge > 1.0:
            explanations.append(f"Dynamic pricing adjustment: {surge:.1f}x multiplier")
        
        if demand > 1.2:
            explanations.append("Higher than usual demand in your area")
        elif demand < 0.8:
            explanations.append("Lower than usual demand in your area")
        
        if optimal_price > base_price * 1.1:
            explanations.append("Premium pricing for enhanced service")
        elif optimal_price < base_price * 0.9:
            explanations.append("Competitive pricing applied")
        else:
            explanations.append("Priced at market average")
        
        return explanations
    
    def _fallback_price(self, base_price: float, context: RideContext) -> Dict:
        """Fallback pricing when ML fails."""
        return {
            'optimal_price': round(base_price, 2),
            'base_price': round(base_price, 2),
            'surge_multiplier': 1.0,
            'confidence': 0.5,
            'explanation': ['Rule-based pricing applied'],
            'is_fallback': True,
        }
    
    def _generate_cache_key(self, context: RideContext, base_price: float) -> str:
        """Generate cache key for pricing result."""
        return f"pricing:{context.service_type}:{context.distance_km}:{context.time_of_day}"