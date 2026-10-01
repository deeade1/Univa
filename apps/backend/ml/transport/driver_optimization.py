# ml/transport/driver/optimizer.py
"""
Driver optimization using ML - Core optimizer.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


@dataclass
class DriverPerformance:
    """Driver performance metrics."""
    rating: float
    acceptance_rate: float
    completion_rate: float
    earnings_per_hour: float
    total_rides: int
    online_hours: float
    cancellation_rate: float
    customer_satisfaction: float


class DriverEarningOptimizer:
    """
    ML-powered driver earning optimization.
    Focused on commission optimization and earning prediction.
    """
    
    def __init__(self):
        self._models = {}
        self._scaler = StandardScaler()
        self._feature_importance = {}
        self._last_trained = None
    
    def optimize_commission(
        self,
        driver_id: str,
        performance: DriverPerformance,
        market_conditions: Dict
    ) -> Dict[str, Any]:
        """
        Optimize commission rate for a driver.
        
        Args:
            driver_id: Driver identifier
            performance: Driver performance metrics
            market_conditions: Current market conditions
        
        Returns:
            Dict with optimized commission and recommendations
        """
        try:
            model = self._get_model('commission_optimizer')
            
            if model:
                # Prepare features
                features = self._prepare_commission_features(performance, market_conditions)
                X = self._scaler.transform([features])
                
                # Predict optimal commission
                prediction = model.predict(X)
                
                base_commission = 20.0
                optimal_rate = max(10.0, min(30.0, float(prediction[0])))
                
                # Calculate driver value score
                value_score = self._calculate_driver_value(performance)
                
                return {
                    'commission_rate': round(optimal_rate, 2),
                    'driver_value_score': round(value_score, 2),
                    'driver_tier': self._determine_tier(value_score),
                    'confidence': 0.85,
                    'recommendations': self._generate_recommendations(
                        performance, optimal_rate
                    ),
                }
        except Exception as e:
            logger.error(f"Commission optimization failed for {driver_id}: {e}")
        
        return self._fallback_commission(performance)
    
    def predict_earnings(
        self,
        driver_id: str,
        period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Predict driver earnings for upcoming period.
        
        Args:
            driver_id: Driver identifier
            period_days: Number of days to forecast
        
        Returns:
            Dict with earnings prediction and insights
        """
        try:
            model = self._get_model('earnings_predictor')
            
            if model:
                # Get historical data
                historical = self._get_driver_history(driver_id)
                
                if historical:
                    prediction = self._forecast_earnings(model, historical, period_days)
                    
                    return {
                        'predicted_earnings': prediction['predicted'],
                        'confidence_interval': prediction['confidence_interval'],
                        'peak_times': self._find_peak_times(prediction),
                        'optimization_tips': self._generate_earning_tips(prediction),
                    }
        except Exception as e:
            logger.error(f"Earnings prediction failed for {driver_id}: {e}")
        
        return self._fallback_earnings_prediction()
    
    def _prepare_commission_features(
        self,
        performance: DriverPerformance,
        market_conditions: Dict
    ) -> List[float]:
        """Prepare features for commission optimization."""
        return [
            performance.rating,
            performance.acceptance_rate,
            performance.completion_rate,
            performance.earnings_per_hour,
            performance.total_rides,
            performance.online_hours,
            performance.cancellation_rate,
            market_conditions.get('demand_supply_ratio', 1.0),
            market_conditions.get('competitor_commission', 20.0),
        ]
    
    def _calculate_driver_value(self, performance: DriverPerformance) -> float:
        """Calculate driver value score (0-100)."""
        weights = {
            'rating': 0.25,
            'acceptance_rate': 0.20,
            'completion_rate': 0.15,
            'earnings_per_hour': 0.20,
            'customer_satisfaction': 0.10,
            'total_rides': 0.10,
        }
        
        score = 0.0
        score += (performance.rating / 5.0) * 100 * weights['rating']
        score += performance.acceptance_rate * 100 * weights['acceptance_rate']
        score += performance.completion_rate * 100 * weights['completion_rate']
        score += min(1.0, performance.earnings_per_hour / 50) * 100 * weights['earnings_per_hour']
        score += performance.customer_satisfaction * 100 * weights['customer_satisfaction']
        score += min(1.0, performance.total_rides / 200) * 100 * weights['total_rides']
        
        return score
    
    def _determine_tier(self, value_score: float) -> str:
        """Determine driver tier based on value score."""
        if value_score >= 80:
            return 'platinum'
        elif value_score >= 65:
            return 'gold'
        elif value_score >= 50:
            return 'silver'
        else:
            return 'bronze'
    
    def _generate_recommendations(
        self,
        performance: DriverPerformance,
        commission_rate: float
    ) -> List[Dict]:
        """Generate recommendations for driver."""
        recommendations = []
        
        if performance.rating < 4.5:
            recommendations.append({
                'type': 'improvement',
                'priority': 'high',
                'message': 'Focus on improving customer ratings',
                'action': 'improve_service_quality',
            })
        
        if performance.acceptance_rate < 0.7:
            recommendations.append({
                'type': 'improvement',
                'priority': 'medium',
                'message': 'Increase acceptance rate for better opportunities',
                'action': 'adjust_availability',
            })
        
        if commission_rate > 25:
            recommendations.append({
                'type': 'optimization',
                'priority': 'medium',
                'message': 'High commission rate - focus on performance',
                'action': 'improve_metrics',
            })
        
        return recommendations