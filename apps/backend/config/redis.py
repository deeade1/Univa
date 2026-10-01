import json
import pickle

import redis
from django.conf import settings


class RedisCache:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    
    def cache_geo_data(self, key, location_data, expire=300):
        """Cache geographical data"""
        self.redis_client.setex(
            f"geo:{key}", 
            expire, 
            json.dumps(location_data)
        )
    
    def get_cached_geo_data(self, key):
        """Get cached geographical data"""
        data = self.redis_client.get(f"geo:{key}")
        return json.loads(data) if data else None
    
    def cache_dispatch_result(self, request_id, provider_id, score, expire=60):
        """Cache dispatch matching results"""
        key = f"dispatch:{request_id}"
        data = {
            'provider_id': provider_id,
            'score': score,
            'timestamp': timezone.now().isoformat()
        }
        self.redis_client.setex(key, expire, json.dumps(data))
    
    def get_cached_dispatch(self, request_id):
        """Get cached dispatch result"""
        data = self.redis_client.get(f"dispatch:{request_id}")
        return json.loads(data) if data else None
    
    def increment_request_counter(self, area_key):
        """Increment request counter for surge pricing"""
        key = f"requests:{area_key}"
        self.redis_client.incr(key)
        self.redis_client.expire(key, 600)  # 10 minutes
    
    def get_request_count(self, area_key):
        """Get request count for area"""
        count = self.redis_client.get(f"requests:{area_key}")
        return int(count) if count else 0
    
    def add_to_geo_index(self, provider_id, lat, lng):
        """Add provider to geographical index"""
        self.redis_client.geoadd(
            'providers:location',
            (lng, lat, provider_id)
        )
    
    def find_nearby_providers(self, lat, lng, radius_km=5):
        """Find providers within radius using Redis GEO"""
        providers = self.redis_client.georadius(
            'providers:location',
            lng,
            lat,
            radius_km,
            unit='km',
            withdist=True
        )
        return providers