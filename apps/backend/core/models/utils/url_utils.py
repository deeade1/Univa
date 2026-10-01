# core/url_utils.py
"""
URL utilities for building absolute URLs across Univa.
"""

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site


def build_absolute_uri(location, request=None):
    """
    Build an absolute URI from a relative path.
    
    Args:
        location: The relative URL path
        request: Optional request object
    
    Returns:
        str: Absolute URL
    """
    if not location:
        return None
    
    if request:
        return request.build_absolute_uri(location)
    
    try:
        site = get_current_site(None)
        protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
        return f"{protocol}://{site.domain}{location}"
    except Exception:
        return location


def get_frontend_url(path='', request=None):
    """
    Build absolute URL for frontend routes.
    
    Args:
        path: Frontend path (e.g., '/invoice/123')
        request: Optional request object
    
    Returns:
        str: Full frontend URL
    """
    frontend_domain = getattr(settings, 'FRONTEND_DOMAIN', None)
    if frontend_domain:
        return f"{frontend_domain}{path}"
    return build_absolute_uri(path, request)