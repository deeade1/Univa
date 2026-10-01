# utils/session_interest.py
import json
from collections import Counter

import redis
from django.conf import settings

r = redis.Redis.from_url(settings.REDIS_URL)

def add_session_tag(user_id_or_session, tag, ttl_seconds=3600):
    key = f"user:{user_id_or_session}:recent_tags"
    r.zincrby(key, 1, tag)
    r.expire(key, ttl_seconds)

def get_session_top_tags(user_id_or_session, top_n=10):
    key = f"user:{user_id_or_session}:recent_tags"
    # return list of tags sorted descending
    items = r.zrevrange(key, 0, top_n - 1, withscores=False)
    return [it.decode() for it in items]
