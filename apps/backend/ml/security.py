# ml/security.py
"""
Security layer for ML system - Refactored and enhanced.
"""

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional, List

from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Security-related exceptions."""
    pass


class SafeModelSerializer:
    """Secure model serialization/deserialization with encryption."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        self._encryption_key = encryption_key
        self._cipher = Fernet(encryption_key.encode()) if encryption_key else None
    
    def serialize_model(self, model: Any, model_hash: Optional[str] = None) -> bytes:
        """
        Securely serialize model with integrity checking.
        
        Args:
            model: Model to serialize
            model_hash: Optional hash for verification
        
        Returns:
            bytes: Serialized model data
        
        Raises:
            SecurityError: If serialization fails
        """
        try:
            import joblib
            
            # Serialize using joblib
            serialized = joblib.dumps(model)
            
            # Compute hash
            actual_hash = self._compute_hash(serialized)
            if model_hash and not hmac.compare_digest(model_hash, actual_hash):
                raise SecurityError("Model hash mismatch")
            
            # Create secure package
            package = {
                'model_data': serialized.hex(),
                'hash': actual_hash,
                'timestamp': int(time.time()),
                'version': '2.0.0',
                'serializer': 'joblib',
            }
            
            # Encrypt if key provided
            if self._cipher:
                encrypted = self._cipher.encrypt(json.dumps(package).encode())
                return encrypted
            
            return json.dumps(package).encode()
            
        except Exception as e:
            logger.error(f"Model serialization failed: {e}")
            raise SecurityError(f"Model serialization failed: {e}")
    
    def deserialize_model(self, model_data: bytes, expected_hash: Optional[str] = None) -> Any:
        """
        Securely deserialize model with integrity verification.
        
        Args:
            model_data: Serialized model data
            expected_hash: Expected hash for verification
        
        Returns:
            Any: Deserialized model
        
        Raises:
            SecurityError: If deserialization fails
        """
        try:
            import joblib
            
            # Decrypt if encrypted
            if self._cipher:
                try:
                    decrypted = self._cipher.decrypt(model_data)
                    package = json.loads(decrypted.decode())
                except:
                    package = json.loads(model_data.decode())
            else:
                package = json.loads(model_data.decode())
            
            # Verify package structure
            required_fields = ['model_data', 'hash', 'timestamp']
            if not all(field in package for field in required_fields):
                raise SecurityError("Invalid model package structure")
            
            # Verify hash
            serialized = bytes.fromhex(package['model_data'])
            actual_hash = self._compute_hash(serialized)
            
            if not hmac.compare_digest(package['hash'], actual_hash):
                raise SecurityError("Model integrity check failed")
            
            if expected_hash and not hmac.compare_digest(package['hash'], expected_hash):
                raise SecurityError("Model hash mismatch")
            
            # Deserialize using joblib
            return joblib.loads(serialized)
            
        except Exception as e:
            logger.error(f"Model deserialization failed: {e}")
            raise SecurityError(f"Model deserialization failed: {e}")
    
    def _compute_hash(self, data: Any) -> str:
        """Compute SHA-256 hash of data."""
        if isinstance(data, bytes):
            return hashlib.sha256(data).hexdigest()
        elif isinstance(data, str):
            return hashlib.sha256(data.encode()).hexdigest()
        else:
            json_str = json.dumps(data, sort_keys=True)
            return hashlib.sha256(json_str.encode()).hexdigest()


class InputSanitizer:
    """Sanitize and validate ML model inputs."""
    
    @staticmethod
    def sanitize_features(features: Dict, schema: Dict) -> Dict:
        """
        Sanitize and validate feature inputs based on schema.
        
        Args:
            features: Input features
            schema: Feature schema with validation rules
        
        Returns:
            Dict: Sanitized features
        
        Raises:
            ValidationError: If validation fails
        """
        if not features:
            return {}
        
        sanitized = {}
        
        for feature_name, value in features.items():
            # Get schema for this feature
            feature_config = schema.get(feature_name, {})
            
            # Validate type
            if not InputSanitizer._validate_type(value, feature_config):
                raise ValidationError(
                    f"Feature '{feature_name}': expected {feature_config.get('type', 'any')}"
                )
            
            # Validate ranges
            if feature_config.get('type') in ['int', 'float']:
                value = InputSanitizer._validate_range(value, feature_config)
            
            # Sanitize string
            if feature_config.get('type') == 'str':
                value = InputSanitizer._sanitize_string(value, feature_config)
            
            # Validate categorical
            if feature_config.get('type') == 'categorical':
                allowed = feature_config.get('values', [])
                if allowed and value not in allowed:
                    raise ValidationError(
                        f"Feature '{feature_name}': value must be one of {allowed}"
                    )
            
            sanitized[feature_name] = value
        
        return sanitized
    
    @staticmethod
    def _validate_type(value: Any, config: Dict) -> bool:
        """Validate value type."""
        expected_type = config.get('type', 'any')
        
        type_map = {
            'int': int,
            'float': (int, float),
            'str': str,
            'bool': bool,
            'categorical': (str, int, float),
            'any': object,
        }
        
        return isinstance(value, type_map.get(expected_type, object))
    
    @staticmethod
    def _validate_range(value: Any, config: Dict) -> Any:
        """Validate numeric range."""
        min_val = config.get('min')
        max_val = config.get('max')
        
        if min_val is not None and value < min_val:
            raise ValidationError(f"Value {value} below minimum {min_val}")
        if max_val is not None and value > max_val:
            raise ValidationError(f"Value {value} above maximum {max_val}")
        
        return value
    
    @staticmethod
    def _sanitize_string(value: str, config: Dict) -> str:
        """Sanitize string value."""
        # Remove dangerous characters
        dangerous = ['<', '>', '&', "'", '"', ';', '--', '/*', '*/']
        for char in dangerous:
            value = value.replace(char, '')
        
        # Truncate if too long
        max_len = config.get('max_length', 1000)
        if len(value) > max_len:
            value = value[:max_len]
        
        return value.strip()