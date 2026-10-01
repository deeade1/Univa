# apps/backend/transport/middleware/rate_limiting.py
import time

from django.core.cache import cache
from django.http import JsonResponse


class RateLimitMiddleware:
    """Middleware for API rate limiting"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = {
            'default': (100, 3600),  # 100 requests per hour
            'auth': (10, 300),       # 10 requests per 5 minutes for auth
            'geocoding': (50, 3600), # 50 geocoding requests per hour
            'booking': (20, 300),    # 20 bookings per 5 minutes
        }
    
    def __call__(self, request):
        # Skip rate limiting for non-API routes
        if not request.path.startswith('/api/'):
            return self.get_response(request)
        
        # Get client identifier
        client_id = self.get_client_identifier(request)
        
        # Determine rate limit type
        limit_type = self.get_rate_limit_type(request)
        
        # Check rate limit
        if not self.check_rate_limit(client_id, limit_type):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }, status=429)
        
        response = self.get_response(request)
        
        # Add rate limit headers
        self.add_rate_limit_headers(response, client_id, limit_type)
        
        return response
    
    def get_client_identifier(self, request):
        """Get unique identifier for client"""
        if request.user.is_authenticated:
            return f"user_{request.user.id}"
        else:
            return f"ip_{self.get_client_ip(request)}"
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_rate_limit_type(self, request):
        """Determine rate limit type based on request path and method"""
        path = request.path
        
        if '/auth/' in path:
            return 'auth'
        elif '/geocode/' in path:
            return 'geocoding'
        elif '/book/' in path or request.method == 'POST' and '/rides/' in path:
            return 'booking'
        else:
            return 'default'
    
    def check_rate_limit(self, client_id, limit_type):
        """Check if client has exceeded rate limit"""
        limit, window = self.rate_limits[limit_type]
        cache_key = f"rate_limit:{client_id}:{limit_type}"
        
        # Get current count and timestamp
        current = cache.get(cache_key, {'count': 0, 'reset_time': time.time() + window})
        
        # Reset if window has passed
        if time.time() > current['reset_time']:
            current = {'count': 0, 'reset_time': time.time() + window}
        
        # Check if limit exceeded
        if current['count'] >= limit:
            return False
        
        # Increment count
        current['count'] += 1
        cache.set(cache_key, current, window)
        
        return True
    
    def add_rate_limit_headers(self, response, client_id, limit_type):
        """Add rate limit headers to response"""
        limit, window = self.rate_limits[limit_type]
        cache_key = f"rate_limit:{client_id}:{limit_type}"
        
        current = cache.get(cache_key, {'count': 0, 'reset_time': time.time() + window})
        
        response['X-RateLimit-Limit'] = str(limit)
        response['X-RateLimit-Remaining'] = str(limit - current['count'])
        response['X-RateLimit-Reset'] = str(int(current['reset_time']))
        
        return response

# apps/backend/transport/services/security_service.py
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

import jwt
from django.conf import settings


class SecurityService:
    """Service for security-related operations"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
    
    def generate_api_key(self, user, name="Default"):
        """Generate a new API key for user"""
        # Generate random key
        key = secrets.token_urlsafe(32)
        
        # Create hash for storage
        key_hash = self.hash_api_key(key)
        
        # Store in database (implementation depends on your APIKey model)
        api_key = APIKey.objects.create(
            user=user,
            name=name,
            key_hash=key_hash,
            expires_at=datetime.now() + timedelta(days=365)
        )
        
        return key, api_key
    
    def hash_api_key(self, key):
        """Hash API key for secure storage"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            key.encode('utf-8'),
            self.secret_key.encode('utf-8'),
            100000
        ).hex()
    
    def verify_api_key(self, provided_key, stored_hash):
        """Verify API key against stored hash"""
        computed_hash = self.hash_api_key(provided_key)
        return hmac.compare_digest(computed_hash, stored_hash)
    
    def validate_jwt_token(self, token):
        """Validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    def generate_signed_url(self, path, expires_in=3600):
        """Generate signed URL for secure access"""
        expiration = int(time.time()) + expires_in
        
        data = f"{path}:{expiration}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"{path}?expires={expiration}&signature={signature}"
    
    def verify_signed_url(self, request):
        """Verify signed URL"""
        expires = request.GET.get('expires')
        signature = request.GET.get('signature')
        path = request.path
        
        if not expires or not signature:
            return False
        
        # Check expiration
        if int(expires) < time.time():
            return False
        
        # Verify signature
        data = f"{path}:{expires}"
        expected_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)