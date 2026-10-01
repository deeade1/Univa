# ml/monitoring.py
"""
ML Model Monitoring System - Refactored with PerformanceMonitor.
"""

import json
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Deque

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class ModelMonitor:
    """Monitor ML model performance and data drift."""
    
    def __init__(self, window_size: int = 10000):
        self._window_size = window_size
        self._predictions: Dict[str, Deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._errors: Dict[str, Deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self._feature_stats: Dict[str, Dict[str, Deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=window_size))
        )
        self._drift_thresholds = {
            'psi': 0.1,
            'ks_pvalue': 0.05,
            'mean_shift': 2.0,
        }
    
    def track_prediction(
        self,
        model_id: str,
        features: Dict,
        prediction: Any,
        prediction_time_ms: float,
        request_id: Optional[str] = None,
        actual: Optional[Any] = None
    ):
        """Track a prediction for monitoring."""
        timestamp = datetime.utcnow()
        
        self._predictions[model_id].append({
            'timestamp': timestamp,
            'features': features,
            'prediction': prediction,
            'prediction_time_ms': prediction_time_ms,
            'request_id': request_id,
            'actual': actual,
        })
        
        # Update feature stats for drift detection
        for feature_name, value in features.items():
            if isinstance(value, (int, float)):
                self._feature_stats[model_id][feature_name].append(value)
        
        # Check drift periodically
        if len(self._predictions[model_id]) % 100 == 0:
            self._check_drift(model_id)
    
    def track_error(self, model_id: str, error: str):
        """Track model error."""
        self._errors[model_id].append({
            'timestamp': datetime.utcnow(),
            'error': error,
        })
    
    def get_stats(self, model_id: str) -> Dict[str, Any]:
        """Get monitoring statistics for a model."""
        predictions = list(self._predictions.get(model_id, []))
        errors = list(self._errors.get(model_id, []))
        
        if not predictions:
            return {'total_predictions': 0, 'total_errors': 0}
        
        prediction_times = [p['prediction_time_ms'] for p in predictions]
        
        return {
            'total_predictions': len(predictions),
            'total_errors': len(errors),
            'error_rate': len(errors) / max(len(predictions), 1),
            'avg_prediction_time_ms': np.mean(prediction_times),
            'p95_prediction_time_ms': np.percentile(prediction_times, 95),
            'recent_activity': {
                'last_hour': self._count_recent(predictions, hours=1),
                'last_day': self._count_recent(predictions, hours=24),
            },
            'drift_status': self._get_drift_status(model_id),
        }
    
    def _check_drift(self, model_id: str) -> Dict[str, Any]:
        """Check for data drift."""
        if len(self._predictions[model_id]) < 100:
            return {'has_drift': False, 'reason': 'Insufficient data'}
        
        # Get recent and baseline data
        predictions = list(self._predictions[model_id])
        recent = predictions[-500:]  # Last 500 predictions
        baseline = predictions[:500]  # First 500 predictions
        
        drift_results = {}
        has_drift = False
        
        for feature_name in self._feature_stats[model_id].keys():
            recent_vals = [p['features'].get(feature_name) for p in recent]
            baseline_vals = [p['features'].get(feature_name) for p in baseline]
            
            # Filter None values
            recent_vals = [v for v in recent_vals if v is not None and isinstance(v, (int, float))]
            baseline_vals = [v for v in baseline_vals if v is not None and isinstance(v, (int, float))]
            
            if len(recent_vals) < 50 or len(baseline_vals) < 50:
                continue
            
            # Calculate drift metrics
            psi = self._calculate_psi(baseline_vals, recent_vals)
            ks_stat, ks_pvalue = stats.ks_2samp(baseline_vals, recent_vals)
            
            drift_results[feature_name] = {
                'psi': psi,
                'ks_pvalue': ks_pvalue,
                'mean_shift': self._calculate_shift(baseline_vals, recent_vals),
            }
            
            # Check if drift occurred
            if (psi > self._drift_thresholds['psi'] or
                ks_pvalue < self._drift_thresholds['ks_pvalue']):
                has_drift = True
        
        if has_drift:
            logger.warning(f"Data drift detected for model {model_id}")
            self._trigger_alert(model_id, drift_results)
        
        return {'has_drift': has_drift, 'drift_results': drift_results}
    
    def _calculate_psi(self, baseline: List[float], current: List[float], bins: int = 10) -> float:
        """Calculate Population Stability Index."""
        if len(baseline) < 10 or len(current) < 10:
            return 0.0
        
        try:
            # Create bins based on combined distribution
            all_vals = baseline + current
            bin_edges = np.percentile(all_vals, np.linspace(0, 100, bins + 1))
            bin_edges = np.unique(bin_edges)
            
            baseline_hist, _ = np.histogram(baseline, bins=bin_edges)
            current_hist, _ = np.histogram(current, bins=bin_edges)
            
            # Add small epsilon to avoid division by zero
            baseline_hist = baseline_hist.astype(float) + 1e-10
            current_hist = current_hist.astype(float) + 1e-10
            
            baseline_probs = baseline_hist / np.sum(baseline_hist)
            current_probs = current_hist / np.sum(current_hist)
            
            psi = np.sum((current_probs - baseline_probs) * 
                        np.log(current_probs / baseline_probs))
            
            return float(psi)
        except Exception as e:
            logger.warning(f"PSI calculation failed: {e}")
            return 0.0
    
    def _calculate_shift(self, baseline: List[float], current: List[float]) -> float:
        """Calculate mean shift in standard deviations."""
        baseline_mean = np.mean(baseline)
        baseline_std = np.std(baseline)
        current_mean = np.mean(current)
        
        if baseline_std == 0:
            return 0.0
        
        return float((current_mean - baseline_mean) / baseline_std)
    
    def _count_recent(self, predictions: List[Dict], hours: int) -> int:
        """Count predictions within time window."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return sum(1 for p in predictions if p['timestamp'] > cutoff)
    
    def _get_drift_status(self, model_id: str) -> Dict:
        """Get current drift status."""
        try:
            drift_results = self._check_drift(model_id)
            return {
                'has_drift': drift_results.get('has_drift', False),
                'last_checked': datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning(f"Drift check failed: {e}")
            return {'has_drift': False, 'error': str(e)}
    
    def _trigger_alert(self, model_id: str, drift_results: Dict):
        """Trigger drift alert."""
        alert = {
            'alert_type': 'data_drift',
            'model_id': model_id,
            'severity': 'warning',
            'message': f"Data drift detected for model {model_id}",
            'details': drift_results,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        # Log alert
        logger.warning(f"DRIFT ALERT: {json.dumps(alert, indent=2)}")
        
        # TODO: Send to external alerting system


class PerformanceMonitor:
    """
    Monitor system performance metrics like latency and throughput.
    """
    
    def __init__(self, window_size: int = 1440):  # 24 hours at 1-minute intervals
        self._latency_history: Dict[str, Deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self._throughput_history: Dict[str, Deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._error_history: Dict[str, Deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._alert_thresholds = {
            'latency_ms': 5000,  # 5 seconds
            'error_rate': 0.05,   # 5%
        }
    
    def track_latency(self, endpoint: str, latency_ms: float) -> None:
        """
        Track endpoint latency.
        
        Args:
            endpoint: Endpoint identifier
            latency_ms: Latency in milliseconds
        """
        self._latency_history[endpoint].append({
            'timestamp': datetime.utcnow(),
            'latency_ms': latency_ms
        })
        
        # Check for latency threshold breach
        if latency_ms > self._alert_thresholds['latency_ms']:
            logger.warning(f"High latency detected for {endpoint}: {latency_ms}ms")
            self._trigger_alert(
                'high_latency',
                endpoint=endpoint,
                latency_ms=latency_ms,
                threshold=self._alert_thresholds['latency_ms']
            )
    
    def track_throughput(self, endpoint: str, requests_per_minute: int) -> None:
        """
        Track endpoint throughput.
        
        Args:
            endpoint: Endpoint identifier
            requests_per_minute: Requests per minute
        """
        self._throughput_history[endpoint].append({
            'timestamp': datetime.utcnow(),
            'rpm': requests_per_minute
        })
    
    def track_error(self, endpoint: str, error: str) -> None:
        """
        Track endpoint error.
        
        Args:
            endpoint: Endpoint identifier
            error: Error message
        """
        self._error_history[endpoint].append({
            'timestamp': datetime.utcnow(),
            'error': error
        })
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Returns:
            Dict: Performance report with all metrics
        """
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'endpoints': {}
        }
        
        all_endpoints = set(
            list(self._latency_history.keys()) +
            list(self._throughput_history.keys()) +
            list(self._error_history.keys())
        )
        
        for endpoint in all_endpoints:
            latencies = [l['latency_ms'] for l in self._latency_history.get(endpoint, [])]
            throughputs = [t['rpm'] for t in self._throughput_history.get(endpoint, [])]
            errors = self._error_history.get(endpoint, [])
            
            endpoint_report = {
                'latency_ms': {},
                'throughput_rpm': {},
                'error_count': len(errors),
            }
            
            if latencies:
                endpoint_report['latency_ms'] = {
                    'avg': round(np.mean(latencies), 2),
                    'p50': round(np.percentile(latencies, 50), 2),
                    'p95': round(np.percentile(latencies, 95), 2),
                    'p99': round(np.percentile(latencies, 99), 2),
                    'max': round(np.max(latencies), 2),
                    'min': round(np.min(latencies), 2),
                    'sample_count': len(latencies),
                }
                
                # Check for degradation
                endpoint_report['degraded'] = (
                    np.percentile(latencies, 95) > self._alert_thresholds['latency_ms']
                )
            
            if throughputs:
                endpoint_report['throughput_rpm'] = {
                    'current': throughputs[-1] if throughputs else 0,
                    'avg': round(np.mean(throughputs), 2),
                    'max': round(np.max(throughputs), 2),
                    'min': round(np.min(throughputs), 2),
                    'trend': self._calculate_trend(throughputs),
                    'sample_count': len(throughputs),
                }
            
            report['endpoints'][endpoint] = endpoint_report
        
        return report
    
    def get_endpoint_stats(self, endpoint: str) -> Dict[str, Any]:
        """
        Get statistics for a specific endpoint.
        
        Args:
            endpoint: Endpoint identifier
        
        Returns:
            Dict: Endpoint statistics
        """
        latencies = [l['latency_ms'] for l in self._latency_history.get(endpoint, [])]
        throughputs = [t['rpm'] for t in self._throughput_history.get(endpoint, [])]
        errors = self._error_history.get(endpoint, [])
        
        if not latencies:
            return {'error': 'No data available for endpoint'}
        
        return {
            'endpoint': endpoint,
            'last_minute': {
                'avg_latency': round(np.mean(latencies[-60:]) if len(latencies) >= 60 else np.mean(latencies), 2),
                'throughput': throughputs[-1] if throughputs else 0,
                'error_count': len([e for e in errors if e['timestamp'] > datetime.utcnow() - timedelta(minutes=1)]),
            },
            'last_hour': {
                'avg_latency': round(np.mean(latencies[-3600:]) if len(latencies) >= 3600 else np.mean(latencies), 2),
                'throughput': np.mean(throughputs[-60:]) if len(throughputs) >= 60 else np.mean(throughputs) if throughputs else 0,
                'error_count': len([e for e in errors if e['timestamp'] > datetime.utcnow() - timedelta(hours=1)]),
            },
            'last_day': {
                'avg_latency': round(np.mean(latencies), 2),
                'throughput': np.mean(throughputs) if throughputs else 0,
                'error_count': len(errors),
                'p95_latency': round(np.percentile(latencies, 95), 2),
            },
            'health_status': self._get_health_status(endpoint, latencies, errors),
        }
    
    def clear_history(self, endpoint: Optional[str] = None) -> None:
        """
        Clear performance history.
        
        Args:
            endpoint: Optional specific endpoint to clear
        """
        if endpoint:
            self._latency_history[endpoint].clear()
            self._throughput_history[endpoint].clear()
            self._error_history[endpoint].clear()
        else:
            self._latency_history.clear()
            self._throughput_history.clear()
            self._error_history.clear()
        
        logger.info(f"Performance history cleared: {endpoint or 'all'}")
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend (increasing, decreasing, stable)."""
        if len(values) < 2:
            return 'insufficient_data'
        
        recent = values[-10:] if len(values) >= 10 else values
        older = values[-20:-10] if len(values) >= 20 else values[:len(values)//2]
        
        if not older:
            return 'insufficient_data'
        
        recent_avg = np.mean(recent)
        older_avg = np.mean(older)
        
        if recent_avg > older_avg * 1.1:
            return 'increasing'
        elif recent_avg < older_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'
    
    def _get_health_status(self, endpoint: str, latencies: List[float], errors: List) -> str:
        """Get health status for an endpoint."""
        if not latencies:
            return 'unknown'
        
        # Check error rate
        recent_errors = len([e for e in errors if e['timestamp'] > datetime.utcnow() - timedelta(minutes=5)])
        total_requests = len(latencies)
        error_rate = recent_errors / max(total_requests, 1)
        
        if error_rate > self._alert_thresholds['error_rate']:
            return 'critical'
        
        # Check latency
        p95_latency = np.percentile(latencies, 95)
        if p95_latency > self._alert_thresholds['latency_ms']:
            return 'degraded'
        
        # Check for increasing latency trend
        if len(latencies) > 20:
            recent_avg = np.mean(latencies[-10:])
            older_avg = np.mean(latencies[-20:-10])
            if recent_avg > older_avg * 1.2:
                return 'degraded'
        
        return 'healthy'
    
    def _trigger_alert(self, alert_type: str, **kwargs) -> None:
        """
        Trigger performance alert.
        
        Args:
            alert_type: Type of alert
            **kwargs: Alert details
        """
        alert = {
            'alert_type': alert_type,
            'timestamp': datetime.utcnow().isoformat(),
            **kwargs
        }
        
        logger.warning(f"PERFORMANCE ALERT: {json.dumps(alert)}")
        
        # TODO: Send to external alerting system (Slack, PagerDuty, etc.)