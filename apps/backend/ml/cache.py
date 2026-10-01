# ml/cache.py
"""
Caching layer for ML system - Refactored and simplified.
"""

import hashlib
import json
import pickle
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

from django.core.cache import cache
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)


class ModelCache:
    """Cache for ML models with TTL and LRU eviction."""
    
    def __init__(self, maxsize: int = 10, ttl: int = 3600):
        self._ttl = ttl
        self._maxsize = maxsize
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0,
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get model from cache."""
        try:
            cached = cache.get(self._make_key(key))
            if cached is not None:
                self._stats['hits'] += 1
                return cached
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
        
        self._stats['misses'] += 1
        return None
    
    def set(self, key: str, model: Any, ttl: Optional[int] = None) -> bool:
        """Store model in cache."""
        try:
            ttl = ttl or self._ttl
            cache.set(self._make_key(key), model, timeout=ttl)
            self._stats['size'] += 1
            return True
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
            return False
    
    def invalidate(self, key: str) -> bool:
        """Invalidate cache entry."""
        try:
            cache.delete(self._make_key(key))
            self._stats['size'] -= 1
            return True
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear entire cache."""
        try:
            cache.clear()
            self._stats['size'] = 0
            self._stats['evictions'] += 1
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = self._stats['hits'] / max(
            self._stats['hits'] + self._stats['misses'], 1
        )
        
        return {
            **self._stats,
            'hit_rate': round(hit_rate, 4),
            'max_size': self._maxsize,
            'ttl': self._ttl,
        }
    
    def _make_key(self, key: str) -> str:
        """Make cache key with prefix."""
        return f"ml:model:{key}"


class FeatureCache:
    """Redis-based cache for features."""
    
    def __init__(self, redis_client_name: str = "default"):
        self._redis = get_redis_connection(redis_client_name)
        self._prefix = "ml:features"
    
    def get(self, entity_id: str, feature_name: str) -> Optional[Any]:
        """Get a single feature from cache."""
        try:
            key = self._make_key(entity_id, feature_name)
            value = self._redis.get(key)
            
            if value:
                return self._deserialize(value)
        except Exception as e:
            logger.warning(f"Feature cache get failed: {e}")
        
        return None
    
    def get_batch(
        self,
        entity_ids: List[str],
        feature_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get multiple features for multiple entities."""
        if not entity_ids or not feature_names:
            return {}
        
        results = {}
        try:
            pipeline = self._redis.pipeline()
            for entity_id in entity_ids:
                for feature_name in feature_names:
                    key = self._make_key(entity_id, feature_name)
                    pipeline.get(key)
            
            values = pipeline.execute()
            
            idx = 0
            for entity_id in entity_ids:
                results[entity_id] = {}
                for feature_name in feature_names:
                    value = values[idx]
                    if value:
                        results[entity_id][feature_name] = self._deserialize(value)
                    idx += 1
            
            return results
        except Exception as e:
            logger.warning(f"Batch cache get failed: {e}")
            return {}
    
    def set_batch(
        self,
        features: Dict[str, Dict[str, Any]],
        ttl: int = 3600
    ) -> bool:
        """Set multiple features in cache."""
        try:
            pipeline = self._redis.pipeline()
            
            for entity_id, entity_features in features.items():
                for feature_name, value in entity_features.items():
                    key = self._make_key(entity_id, feature_name)
                    serialized = self._serialize(value)
                    pipeline.setex(key, ttl, serialized)
            
            pipeline.execute()
            return True
        except Exception as e:
            logger.warning(f"Batch cache set failed: {e}")
            return False
    
    def invalidate_entity(self, entity_id: str) -> bool:
        """Invalidate all features for an entity."""
        try:
            pattern = f"{self._prefix}:{entity_id}:*"
            keys = self._redis.keys(pattern)
            
            if keys:
                self._redis.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Entity invalidation failed: {e}")
            return False
    
    def _make_key(self, entity_id: str, feature_name: str) -> str:
        """Make cache key."""
        return f"{self._prefix}:{entity_id}:{feature_name}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for Redis."""
        try:
            return json.dumps(value).encode()
        except (TypeError, ValueError):
            return pickle.dumps(value)
    
    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from Redis."""
        try:
            return json.loads(value.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return pickle.loads(value)


class PredictionCache:
    """Cache for ML predictions."""
    
    def __init__(self, redis_client_name: str = "predictions"):
        self._redis = get_redis_connection(redis_client_name)
        self._prefix = "ml:predictions"
        self._default_ttl = 300  # 5 minutes
    
    def get(self, model_id: str, features_hash: str) -> Optional[Dict]:
        """
        Get cached prediction.
        
        Args:
            model_id: Model identifier
            features_hash: Hash of features
        
        Returns:
            Cached prediction or None
        """
        try:
            key = self._make_key(model_id, features_hash)
            value = self._redis.get(key)
            
            if value:
                return json.loads(value.decode())
        except Exception as e:
            logger.warning(f"Prediction cache get failed: {e}")
        
        return None
    
    def set(
        self,
        model_id: str,
        features_hash: str,
        prediction: Dict,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache prediction.
        
        Args:
            model_id: Model identifier
            features_hash: Hash of features
            prediction: Prediction result
            ttl: Time to live in seconds
        
        Returns:
            bool: Success status
        """
        try:
            ttl = ttl or self._default_ttl
            key = self._make_key(model_id, features_hash)
            self._redis.setex(key, ttl, json.dumps(prediction))
            return True
        except Exception as e:
            logger.warning(f"Prediction cache set failed: {e}")
            return False
    
    def invalidate(self, model_id: str, features_hash: Optional[str] = None) -> bool:
        """
        Invalidate cached predictions.
        
        Args:
            model_id: Model identifier
            features_hash: Optional specific features hash to invalidate
        
        Returns:
            bool: Success status
        """
        try:
            if features_hash:
                key = self._make_key(model_id, features_hash)
                self._redis.delete(key)
            else:
                # Invalidate all predictions for this model
                pattern = f"{self._prefix}:{model_id}:*"
                keys = self._redis.keys(pattern)
                if keys:
                    self._redis.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Prediction cache invalidation failed: {e}")
            return False
    
    def compute_features_hash(self, features: Dict) -> str:
        """
        Compute hash of features for cache key.
        
        Args:
            features: Feature dictionary
        
        Returns:
            str: SHA-256 hash of features
        """
        # Sort features for consistent hashing
        sorted_features = json.dumps(features, sort_keys=True)
        return hashlib.sha256(sorted_features.encode()).hexdigest()
    
    def _make_key(self, model_id: str, features_hash: str) -> str:
        """Make cache key."""
        return f"{self._prefix}:{model_id}:{features_hash}"