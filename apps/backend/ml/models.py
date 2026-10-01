# ml/models.py
"""
ML models - Consolidated and cleaned up.
"""

import logging
import hashlib
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import uuid4

from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache

from .security import SafeModelSerializer, InputSanitizer, SecurityError

logger = logging.getLogger(__name__)


class MLModelVersion(models.Model):
    """Track different versions of ML models."""
    
    class ModelType(models.TextChoices):
        PRICING_DYNAMIC = 'pricing_dynamic', 'Dynamic Pricing'
        PRICING_ELASTICITY = 'pricing_elasticity', 'Price Elasticity'
        DEMAND_FORECASTING = 'demand_forecasting', 'Demand Forecasting'
        CUSTOMER_SEGMENTATION = 'customer_segmentation', 'Customer Segmentation'
        CHURN_PREDICTION = 'churn_prediction', 'Churn Prediction'
        LIFETIME_VALUE = 'lifetime_value', 'Lifetime Value Prediction'
        RECOMMENDATION = 'recommendation', 'Recommendation Engine'
    
    class Framework(models.TextChoices):
        XGBOOST = 'xgboost', 'XGBoost'
        LIGHTGBM = 'lightgbm', 'LightGBM'
        TENSORFLOW = 'tensorflow', 'TensorFlow'
        PYTORCH = 'pytorch', 'PyTorch'
        SKLEARN = 'sklearn', 'Scikit-Learn'
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    model_type = models.CharField(max_length=50, choices=ModelType.choices, db_index=True)
    framework = models.CharField(max_length=20, choices=Framework.choices)
    version = models.CharField(max_length=50, db_index=True)
    
    # Model storage
    model_file = models.BinaryField(null=True, blank=True)
    model_path = models.CharField(max_length=500, blank=True)
    model_hash = models.CharField(max_length=64, blank=True)
    model_size_mb = models.FloatField(default=0.0) 
    # Feature schema
    feature_schema = models.JSONField(default=dict)
    features_used = ArrayField(models.CharField(max_length=100), default=list)
    # Performance
    performance_metrics = models.JSONField(default=dict)
    monitoring_metrics = models.JSONField(default=dict)
    
    # Training metadata
    training_samples = models.BigIntegerField(default=0)
    training_duration_seconds = models.FloatField(default=0.0)
    training_data_start = models.DateTimeField(null=True)
    training_data_end = models.DateTimeField(null=True)
    
    # Status
    is_production = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_experimental = models.BooleanField(default=False)
    
    # Security
    encryption_key_id = models.CharField(max_length=100, blank=True)
    security_score = models.FloatField(null=True)
    
    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='created_models'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deployed_at = models.DateTimeField(null=True)
    deprecated_at = models.DateTimeField(null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_type', 'is_production', 'is_active']),
            models.Index(fields=['version', 'framework']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['model_type', 'version'],
                name='unique_model_version',
                condition=models.Q(is_active=True)
            )
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._serializer = SafeModelSerializer(
            encryption_key=getattr(settings, 'MODEL_ENCRYPTION_KEY', None)
        )
    
    def save_model(self, model: Any) -> bool:
        """Securely save model with integrity checking."""
        try:
            serialized = self._serializer.serialize_model(model)
            self.model_hash = hashlib.sha256(serialized).hexdigest()
            self.model_file = serialized
            self.model_size_mb = len(serialized) / (1024 * 1024)
            self.save()
            return True
        except Exception as e:
            logger.error(f"Model save failed: {e}")
            return False
    
    def load_model(self) -> Optional[Any]:
        """Securely load model with integrity verification."""
        try:
            if not self.model_file:
                raise ValueError("No model file available")
            
            return self._serializer.deserialize_model(
                self.model_file,
                expected_hash=self.model_hash
            )
        except SecurityError as e:
            logger.error(f"Security violation loading model: {e}")
            raise
        except Exception as e:
            logger.error(f"Model load failed: {e}")
            return None
    
    def predict(self, features: Dict) -> Dict:
        """Make prediction with input validation."""
        try:
            # Validate inputs
            sanitized = InputSanitizer.sanitize_features(features, self.feature_schema)
            
            # Load model
            model = self.load_model()
            if model is None:
                raise ValueError("Model could not be loaded")
            
            # Make prediction
            result = model.predict(sanitized)
            
            return {
                'prediction': result,
                'model_version': self.version,
                'model_id': str(self.id),
                'timestamp': datetime.utcnow().isoformat(),
            }
        except SecurityError as e:
            logger.error(f"Security error in prediction: {e}")
            raise
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise
    
    def get_performance_report(self) -> Dict:
        """Generate performance report."""
        return {
            'model_id': str(self.id),
            'version': self.version,
            'type': self.model_type,
            'metrics': self.performance_metrics,
            'samples': self.training_samples,
            'is_production': self.is_production,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'security_score': self.security_score,
        }